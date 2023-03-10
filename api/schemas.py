from marshmallow import validate, validates, validates_schema, \
    ValidationError, post_dump
from api import ma, db
from api.auth import token_auth
from api.models import User, Account, Mission
from api.enums import Role

paginated_schema_cache = {}


class EmptySchema(ma.Schema):
    pass

class DateTimePaginationSchema(ma.Schema):
    class Meta:
        ordered = True

    limit = ma.Integer()
    offset = ma.Integer()
    after = ma.DateTime(load_only=True)
    count = ma.Integer(dump_only=True)
    total = ma.Integer(dump_only=True)

    @validates_schema
    def validate_schema(self, data, **kwargs):
        if data.get('offset') is not None and data.get('after') is not None:
            raise ValidationError('Cannot specify both offset and after')


class StringPaginationSchema(ma.Schema):
    class Meta:
        ordered = True

    limit = ma.Integer()
    offset = ma.Integer()
    after = ma.String(load_only=True)
    count = ma.Integer(dump_only=True)
    total = ma.Integer(dump_only=True)

    @validates_schema
    def validate_schema(self, data, **kwargs):
        if data.get('offset') is not None and data.get('after') is not None:
            raise ValidationError('Cannot specify both offset and after')


def PaginatedCollection(schema, pagination_schema=StringPaginationSchema):
    if schema in paginated_schema_cache:
        return paginated_schema_cache[schema]

    class PaginatedSchema(ma.Schema):
        class Meta:
            ordered = True

        pagination = ma.Nested(pagination_schema)
        data = ma.Nested(schema, many=True)

    PaginatedSchema.__name__ = 'Paginated{}'.format(schema.__class__.__name__)
    paginated_schema_cache[schema] = PaginatedSchema
    return PaginatedSchema


class UserSchema(ma.SQLAlchemySchema):
    class Meta:
        model = User
        ordered = True
        description = "This is the primrary schema that represent an user. \nSince most of the player \
            are multiboxing, the user represent the responsible individuals for all the accounts \
            recorded in the system under his name. The user is also accepts mission on mission-runner's \
            behalf as well as tracking the bounty that he deserves."

    id = ma.auto_field(dump_only=True, description = "User ID number")
    url = ma.String(dump_only=True)
    username = ma.auto_field(required=True, validate=validate.Length(min=3, max=64))
    email = ma.auto_field(required=True, validate=[validate.Length(max=120), validate.Email()])
    im_number = ma.auto_field(required=True, validate=[validate.Length(max=120)], description = "Typically QQ number by Tencent")
    password = ma.String(required=True, load_only=True, validate=validate.Length(min=3))
    role = ma.String(dump_only=True, validate=[validate.Length(max=120)], description = "Typically QQ number by Tencent")
    avatar_url = ma.String(dump_only=True)
    # about_me = ma.auto_field()
    birthday = ma.auto_field(dump_only=True)
    last_seen = ma.auto_field(dump_only=True)
    activated = ma.auto_field(dump_only=True)
    # account_url = ma.URLFor('account.user_all', values={'id': '<id>'}, dump_only=True)

    @validates('username')
    def validate_username(self, value):
        if not value[0].isalpha():
            raise ValidationError('Username must start with a letter')
        user = token_auth.current_user()
        old_username = user.username if user else None
        if value != old_username and \
                db.session.scalar(User.select().filter_by(username=value)):
            raise ValidationError('Use a different username.')

    @validates('email')
    def validate_email(self, value):
        user = token_auth.current_user()
        old_email = user.email if user else None
        if value != old_email and \
                db.session.scalar(User.select().filter_by(email=value)):
            raise ValidationError('Use a different email.')
        
    @validates('role')
    def validate_role(self, value):
        allowed_roles = [r.value for r in Role]
        user = token_auth.current_user()
        if value not in allowed_roles:
            raise ValueError(f"Invalid role: {value}. Allowed roles are {', '.join(allowed_roles)}.")
        if user is not None:
            if not user.is_admin():
                raise PermissionError("Only administrator can update user role")
        else:
            raise PermissionError("Only administrator can update user role")

    @post_dump
    def fix_datetimes(self, data, **kwargs):
        data['birthday'] += 'Z'
        data['last_seen'] += 'Z'
        return data


class UpdateUserSchema(UserSchema):
    old_password = ma.String(load_only=True, validate=validate.Length(min=3))
    role = ma.String(dump_only=True, validate=[validate.Length(max=120)])

    @validates('old_password')
    def validate_old_password(self, value):
        if not token_auth.current_user().verify_password(value):
            raise ValidationError('Password is incorrect')

    @validates('role')
    def validate_role(self, value):
        allowed_roles = [r.value for r in Role]
        user = token_auth.current_user()
        if value not in allowed_roles:
            raise ValueError(f"Invalid role: {value}. Allowed roles are {', '.join(allowed_roles)}.")
        if user is not None:
            if not user.is_admin():
                raise PermissionError("Only administrator can update user role")
        else:
            raise PermissionError("Only administrator can update user role")
        
class UpdateUserRoleSchema(UserSchema):
    role = ma.String(validate=[validate.Length(max=120)])

    @validates('role')
    def validate_role(self, value):
        allowed_roles = [r.value for r in Role]
        user = token_auth.current_user()
        if value not in allowed_roles:
            raise ValueError(f"Invalid role: {value}. Allowed roles are {', '.join(allowed_roles)}.")
        if user is not None:
            if not user.is_admin():
                raise PermissionError("Only administrator can update user role")
        else:
            raise PermissionError("Only administrator can update user role")

class AccountSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Account
        ordered = True

    id = ma.auto_field(dump_only=True)
    url = ma.String(dump_only=True)
    name = ma.auto_field(required=True, validate=validate.Length(min=3, max=64))
    # email = ma.auto_field(required=True, validate=[validate.Length(max=120), validate.Email()])
    # im_number = ma.auto_field(required=True, validate=[validate.Length(max=120)])
    # password = ma.String(required=True, load_only=True, validate=validate.Length(min=3))
    # role = ma.String(dump_only=True, validate=[validate.Length(max=120)])
    # avatar_url = ma.String(dump_only=True)
    # # about_me = ma.auto_field()
    created = ma.auto_field(dump_only=True)
    # last_seen = ma.auto_field(dump_only=True)
    activated = ma.auto_field(dump_only=True)
    lp_point = ma.auto_field()
    owner = ma.Nested(UserSchema, dump_only=True)
    # missions_published
    

# class PostSchema(ma.SQLAlchemySchema):
#     class Meta:
#         model = Post
#         include_fk = True
#         ordered = True

#     id = ma.auto_field(dump_only=True)
#     url = ma.String(dump_only=True)
#     text = ma.auto_field(required=True, validate=validate.Length(
#         min=1, max=280))
#     timestamp = ma.auto_field(dump_only=True)
#     author = ma.Nested(UserSchema, dump_only=True)

#     @post_dump
#     def fix_datetimes(self, data, **kwargs):
#         data['timestamp'] += 'Z'
#         return data


class TokenSchema(ma.Schema):
    class Meta:
        ordered = True

    access_token = ma.String(required=True)
    refresh_token = ma.String()


class PasswordResetRequestSchema(ma.Schema):
    class Meta:
        ordered = True

    email = ma.String(required=True, validate=[validate.Length(max=120),
                                               validate.Email()])


class PasswordResetSchema(ma.Schema):
    class Meta:
        ordered = True

    token = ma.String(required=True)
    new_password = ma.String(required=True, validate=validate.Length(min=3))
        

