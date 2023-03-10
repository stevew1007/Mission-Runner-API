from datetime import datetime, timedelta
from enum import Enum
from hashlib import md5
import secrets
from time import time
from typing import Optional
from flask import current_app, url_for, has_request_context
import jwt
import sqlalchemy as sa
from sqlalchemy import orm as so
from sqlalchemy import event
from werkzeug.security import generate_password_hash, check_password_hash
from api.enums import Role
from api.app import db


class Updateable:
    def update(self, data):
        for attr, value in data.items():
            setattr(self, attr, value)
            
# followers = sa.Table(
#     'followers',
#     db.Model.metadata,
#     sa.Column('follower_id', sa.ForeignKey('users.id'), primary_key=True),
#     sa.Column('followed_id', sa.ForeignKey('users.id'), primary_key=True)
# )

# class Activity(db.Model):
#     __tablename__ = 'activity'

#     id: so.Mapped[int] = so.mapped_column(primary_key=True)
#     requester_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('users.id'), index=True)
#     table_name: so.Mapped[str] = so.mapped_column(sa.String(64), index=True)
#     changed_id: so.Mapped[int] = so.mapped_column(index=True)
#     attribute: so.Mapped[str] = so.mapped_column(sa.String(64))
#     prevous_value: so.Mapped[str] = so.mapped_column(sa.String(128))
#     new_value: so.Mapped[str] = so.mapped_column(sa.String(128))

#     object_type: so.Mapped[str] = so.mapped_column(sa.String(64))
#     object_id: so.Mapped[int] = so.mapped_column(index=True)
#     operation: so.Mapped[str] = so.mapped_column(sa.String(10))
#     timestamp: so.Mapped[datetime] = so.mapped_column(default=datetime.utcnow)

class ChangeLog(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    object_type: so.Mapped[str] = so.mapped_column(sa.String(64))
    object_id: so.Mapped[int] = so.mapped_column(index=True)
    operation: so.Mapped[str] = so.mapped_column(sa.String(10))
    requester_id: so.Mapped[int] = so.mapped_column(index=True)
    timestamp: so.Mapped[datetime] = so.mapped_column(default=datetime.utcnow)
    attribute_name: so.Mapped[str] = so.mapped_column(sa.String(64))
    old_value: so.Mapped[str] = so.mapped_column(sa.String(255))
    new_value: so.Mapped[str] = so.mapped_column(sa.String(255))
    
class Token(db.Model):
    __tablename__ = 'tokens'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    access_token: so.Mapped[str] = so.mapped_column(sa.String(64), index=True)
    access_expiration: so.Mapped[datetime]
    refresh_token: so.Mapped[str] = so.mapped_column(sa.String(64), index=True)
    refresh_expiration: so.Mapped[datetime]
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('users.id'), index=True)

    user: so.Mapped['User'] = so.relationship(back_populates='tokens')

    def generate(self):
        self.access_token = secrets.token_urlsafe()
        self.access_expiration = datetime.utcnow() + \
            timedelta(minutes=current_app.config['ACCESS_TOKEN_MINUTES'])
        self.refresh_token = secrets.token_urlsafe()
        self.refresh_expiration = datetime.utcnow() + \
            timedelta(days=current_app.config['REFRESH_TOKEN_DAYS'])

    def expire(self, delay=None):
        if delay is None:  # pragma: no branch
            # 5 second delay to allow simultaneous requests
            delay = 5 if not current_app.testing else 0
        self.access_expiration = datetime.utcnow() + timedelta(seconds=delay)
        self.refresh_expiration = datetime.utcnow() + timedelta(seconds=delay)

    @staticmethod
    def clean():
        """Remove any tokens that have been expired for more than a day."""
        yesterday = datetime.utcnow() - timedelta(days=1)
        db.session.execute(Token.delete().where(
            Token.refresh_expiration < yesterday))


class User(Updateable, db.Model):
    __tablename__ = 'users'

    # Basic Info
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    im_number: so.Mapped[str] = so.mapped_column(sa.String(20), index=True, unique=True)
    password_hash: so.Mapped[str] = so.mapped_column(sa.String(128))
    role: so.Mapped[str] = so.mapped_column(sa.String(20), nullable=False, default=Role.MISSION_PUBLISHER.value)
    birthday: so.Mapped[datetime] = so.mapped_column(default=datetime.utcnow)
    last_seen: so.Mapped[datetime] = so.mapped_column(default=datetime.utcnow)
    activated: so.Mapped[bool] = so.mapped_column(default=False)
    
    # Links
    tokens: so.WriteOnlyMapped['Token'] = so.relationship(back_populates='user')
    accounts: so.WriteOnlyMapped['Account'] = so.relationship(back_populates='owner')
    missions_run: so.WriteOnlyMapped['Mission'] = so.relationship(back_populates='runner')


    def __repr__(self):  # pragma: no cover
        return '<User {}>'.format(self.username)

    @property
    def url(self):
        return url_for('users.get', id=self.id)

    @property
    def avatar_url(self):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon'

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def ping(self):
        self.last_seen = datetime.utcnow()

    def generate_auth_token(self):
        token = Token(user=self)
        token.generate()
        return token
    
    def activate(self):
        self.activated = True

    def deactivate(self):
        self.activated = False

    def is_activated(self):
        return bool(self.activated)
    
    def is_admin(self):
        return self.role == Role.ADMIN.value

    @staticmethod
    def verify_access_token(access_token, refresh_token=None):
        token = db.session.scalar(Token.select().filter_by(
            access_token=access_token))
        if token:
            if token.access_expiration > datetime.utcnow():
                token.user.ping()
                db.session.commit()
                return token.user

    @staticmethod
    def verify_refresh_token(refresh_token, access_token):
        token = db.session.scalar(Token.select().filter_by(
            refresh_token=refresh_token, access_token=access_token))
        if token:
            if token.refresh_expiration > datetime.utcnow():
                return token

            # someone tried to refresh with an expired token
            # revoke all tokens from this user as a precaution
            token.user.revoke_all()
            db.session.commit()

    def revoke_all(self):
        db.session.execute(Token.delete().where(Token.user == self))

    def generate_reset_token(self):
        return jwt.encode(
            {
                'exp': time() + current_app.config['RESET_TOKEN_MINUTES'] * 60,
                'reset_email': self.email,
            },
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )

    @staticmethod
    def verify_reset_token(reset_token):
        try:
            data = jwt.decode(reset_token, current_app.config['SECRET_KEY'],
                              algorithms=['HS256'])
        except jwt.PyJWTError:
            return
        return db.session.scalar(User.select().filter_by(
            email=data['reset_email']))

class Account(Updateable, db.Model):
    __tablename__ = 'accounts'

    #Basic Info
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=False, unique=True)
    created: so.Mapped[datetime] = so.mapped_column(default=datetime.utcnow)
    activated: so.Mapped[bool] = so.mapped_column(default=False)
    lp_point: so.Mapped[int] = so.mapped_column(nullable=False)

    # Links
    # Back_populates link for account owner
    owner_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)
    owner: so.Mapped['User'] = so.relationship(back_populates='accounts')
    missions_published: so.Mapped['Mission'] = so.relationship(back_populates='publisher')


    def __repr__(self):  # pragma: no cover
        return '<Post {}>'.format(self.text)
    
    @property
    def url(self):
        return url_for('accounts.get', id=self.id)
    
    # def publish_mission(self):

    def activate(self):
        self.activated = True

    def deactivate(self):
        self.activated = False

    def is_activated(self):
        return bool(self.activated)

class Mission(Updateable, db.Model):
    __tablename__ = 'mission'

    # Basic Info
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    
    published: so.Mapped[datetime] = so.mapped_column(default=datetime.utcnow)

    # Mission Related
    title: so.Mapped[str] = so.mapped_column(sa.String(), nullable=False)
    galaxy: so.Mapped[str] = so.mapped_column(sa.String(), nullable=False)
    created: so.Mapped[datetime] = so.mapped_column(default=datetime.utcnow)
    expired: so.Mapped[datetime]
    bounty: so.Mapped[int] = so.mapped_column(nullable=False)
     
    # Status Related
    status: so.Mapped[str] = so.mapped_column(sa.String(20), nullable=False, default='published')

    publisher_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Account.id), index=True)
    publisher: so.Mapped['Account'] = so.relationship(back_populates='missions_published')
    
    runner_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)
    runner: so.Mapped['User'] = so.relationship(back_populates='missions_run')

    @so.validates('status')
    def validate_status(self, key, value):
        allowed_status = ['published', 'accepted', 'completed', "archived"]
        if value not in allowed_status:
            raise ValueError(f"Invalid status: {value}. Allowed roles are {', '.join(allowed_status)}.")
        return value