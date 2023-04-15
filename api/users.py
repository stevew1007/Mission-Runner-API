from apifairy.decorators import other_responses
from flask import Blueprint, abort, jsonify
from apifairy import authenticate, body, response

from api import db
from api.models import User, ChangeLog
from api.schemas import UserSchema, UpdateUserSchema, AccountSchema
from api.auth import token_auth
from api.enums import Action
# from api.decorators import paginated_response

users = Blueprint('users', __name__)
user_schema = UserSchema()
account_schema = AccountSchema()
users_schema = UserSchema(many=True)
update_user_schema = UpdateUserSchema(partial=True)


@users.route('/users', methods=['POST'])
@body(user_schema)
@response(user_schema, 201)
def new(args):
    """Register a new user"""
    # Setup
    user = User(**args)
    db.session.add(user)
    db.session.commit()

    # Track changes
    change = ChangeLog(
        object_type=type(user).__name__,
        object_id=user.id,
        operation=Action.INSERT.value,
        requester_id=user.id,
        attribute_name="",
        old_value="",
        new_value=f"Add User ID:{user.id}"
    )

    # Save data
    db.session.add(change)
    db.session.commit()
    return user


@users.route('/users/<int:id>', methods=['GET'])
@authenticate(token_auth)
@response(user_schema)
@other_responses({404: 'User not found'})
def get(id):
    """Retrieve a user by id"""
    return db.session.get(User, id) or abort(404)


@users.route('/users/<username>', methods=['GET'])
@authenticate(token_auth)
@response(user_schema)
@other_responses({404: 'User not found'})
def get_by_username(username):
    """Retrieve a user by username"""
    return db.session.scalar(User.select().filter_by(username=username)) or \
        abort(404)


@users.route('/users/<int:id>/default_account', methods=['GET'])
@authenticate(token_auth)
@other_responses({
    403: 'Default account not set for user',
    404: 'User not found'})
def get_default_account(id):
    """Retrieve a user default account by id
    You will only beable to get the id & name of account by this endpoint.
    """
    user = db.session.get(User, id) or abort(404)
    account = user.default_account or abort(403)
    return jsonify(id=account.id, name=account.name)


@users.route('/users/<username>/default_account', methods=['GET'])
@authenticate(token_auth)
@other_responses({
    403: 'Default account not set for user',
    404: 'User not found'})
def get_default_account_by_username(username):
    """Retrieve a user by username"""
    user = db.session.scalar(User.select().filter_by(username=username)) or \
        abort(404)
    account = user.default_account or abort(403)
    return jsonify(id=account.id, name=account.name)


@users.route('/me', methods=['GET'])
@authenticate(token_auth)
@response(user_schema)
def me():
    """Retrieve the authenticated user"""
    return token_auth.current_user()


@users.route('/me', methods=['PUT'])
@authenticate(token_auth)
@body(update_user_schema)
@response(user_schema)
def put(data):
    """Edit user information"""

    # Issuer
    user = token_auth.current_user()

    # Setup
    prev = {key: getattr(user, key)
            for key in dict(data).keys()
            if key not in ['password', 'old_password']}
    if 'password' in data and 'old_password' in data:
        prev['password_hash'] = user.password_hash

    # Gatekeeper
    if 'password' in data and ('old_password' not in data or
                               not user.verify_password(data['old_password'])):
        abort(400)

    # Modification
    user.update(data)

    # Track changes
    for key in prev.keys():
        # if key == 'password_hash' and 'password' not in data:
        #     continue
        if getattr(user, key) == prev[key]:
            # No need to log if the change is same as the origional value.
            continue
        # if getattr(user, key) is not None:
        change = ChangeLog(
            object_type=type(user).__name__,
            object_id=user.id,
            operation=Action.UPDATE.value,
            requester_id=user.id,
            attribute_name=key,
            old_value=prev[key],
            new_value=getattr(user, key)
        )
        db.session.add(change)
        # db.session.commit()

    # Save data
    db.session.commit()
    return user
