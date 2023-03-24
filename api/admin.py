from apifairy.decorators import other_responses
from flask import Blueprint, abort
from apifairy import authenticate, body, response

from api import db
from api.models import User, Account, ChangeLog
from api.schemas import AccountSchema, UserSchema, \
    UpdateUserSchema, EmptySchema, \
    UpdateUserRoleSchema
from api.auth import token_auth
from api.enums import Role, Action
from api.decorators import paginated_response

admin = Blueprint('admin', __name__)
user_schema = UserSchema()
users_schema = UserSchema(many=True)
account_schema = AccountSchema()
accounts_schema = AccountSchema(many=True)
update_user_schema = UpdateUserSchema(partial=True)
update_user_role = UpdateUserRoleSchema()


@admin.route('/users', methods=['GET'])
@authenticate(token_auth, role=[Role.ADMIN.value])
@paginated_response(users_schema)
def all_user():
    """Retrieve all users"""
    return User.select()


@admin.route('/accounts', methods=['GET'])
@authenticate(token_auth, role=[Role.ADMIN.value])
@paginated_response(accounts_schema)
def all_account():
    """Retrieve all accounts"""
    return Account.select()


@admin.route('/accounts/<int:id>/activate', methods=['POST'])
@authenticate(token_auth, role=[Role.ADMIN.value])
@response(EmptySchema, status_code=204,
          description='User activated successfully.')
@other_responses({404: 'Account not found', 409: 'Account already activated'})
def activate_account(id):
    """Activate the account"""

    # Issuer
    requester = token_auth.current_user()

    # Setup
    account = db.session.get(Account, id) or abort(404)
    prev = account.activated

    # Gatekeeper
    if account.is_activated():
        abort(409)

    # Modification
    account.activate()

    # Track changes
    change = ChangeLog(
        object_type=type(account).__name__,
        object_id=account.id,
        operation=Action.UPDATE.value,
        requester_id=requester.id,
        attribute_name='activated',
        old_value=prev,
        new_value=account.activated
    )

    # Save data
    db.session.add(change)
    db.session.commit()


@admin.route('/accounts/<int:id>/deactivate', methods=['POST'])
@authenticate(token_auth, role=[Role.ADMIN.value])
@response(EmptySchema, status_code=204,
          description='Account deactivated successfully.')
@other_responses({404: 'Account not found',
                  409: 'Account already deactivated'})
def deactivate_account(id):
    """Deactivate the account"""

    # Issuer
    requester = token_auth.current_user()

    # Setup
    account = db.session.get(Account, id) or abort(404)
    prev = account.activated

    # Gatekeeper
    if not account.is_activated():
        abort(409)

    # Modification
    account.deactivate()

    # Track changes
    change = ChangeLog(
        object_type=type(account).__name__,
        object_id=account.id,
        operation=Action.UPDATE.value,
        requester_id=requester.id,
        attribute_name='activated',
        old_value=prev,
        new_value=account.activated
    )

    # Save data
    db.session.add(change)
    db.session.commit()


@admin.route('/users/<int:id>/setrole', methods=['PUT'])
@authenticate(token_auth, role=[Role.ADMIN.value])
@body(update_user_role)
@response(EmptySchema, status_code=204,
          description='User role set successfully.')
@other_responses({400: 'Role does not exist',
                  404: 'User not found',
                  409: "User already set to the role specified"})
def setRole(data, id):
    """Set a specific role for the user"""

    # Issuer
    requester = token_auth.current_user()

    # Setup
    user = db.session.get(User, id) or abort(404)
    prev = user.role

    # Gatekeeper
    if not Role.isValid(data['role']):
        abort(400)
    if user.role == data['role']:
        abort(409)

    # Modification
    user.role = data['role']

    # Track changes
    change = ChangeLog(
        object_type=type(user).__name__,
        object_id=user.id,
        operation=Action.UPDATE.value,
        requester_id=requester.id,
        attribute_name='activated',
        old_value=prev,
        new_value=user.role
    )

    # Save data
    db.session.add(change)
    db.session.commit()


@admin.route('/users/<int:id>', methods=['PUT'])
@authenticate(token_auth, role=[Role.ADMIN.value])
@body(update_user_schema)
@response(user_schema)
@other_responses({404: 'User not found'})
def modifyUserInfo(data, id):
    """Modify information for the user
    Allow admin to modify user table of the database.
    **Use this power wisely**.

    Please use seperate API to set role, activate or deactivate user.
    """

    # Issuer
    requester = token_auth.current_user()

    # Setup
    user = db.session.get(User, id) or abort(404)
    prev = {key: getattr(user, key) for key in dict(data).keys()}

    # Modification
    user.update(data)

    # Track changes
    for key in dict(data).keys():
        if getattr(user, key) is not None:
            change = ChangeLog(
                object_type=type(user).__name__,
                object_id=user.id,
                operation=Action.UPDATE.value,
                requester_id=requester.id,
                attribute_name=key,
                old_value=prev[key],
                new_value=getattr(user, key)
            )
            db.session.add(change)

    # Save data
    db.session.commit()
    return user


@admin.route('/accounts/<int:id>', methods=['PUT'])
@authenticate(token_auth, role=[Role.ADMIN.value])
@body(update_user_schema)
@response(user_schema)
@other_responses({404: 'User not found'})
def modifyAccountInfo(data, id):
    """Modify information for the user
    Allow admin to modify user table of the database.
    **Use this power wisely**.

    Please use seperate API to set role, activate or deactivate user.
    """

    # Issuer
    requester = token_auth.current_user()

    # Setup
    account = db.session.get(Account, id) or abort(404)
    prev = {key: getattr(Account, key) for key in dict(data).keys()}

    # Modification
    account.update(data)

    # Track changes
    for key in dict(data).keys():
        if getattr(account, key) is not None:
            change = ChangeLog(
                object_type=type(account).__name__,
                object_id=account.id,
                operation=Action.UPDATE.value,
                requester_id=requester.id,
                attribute_name=key,
                old_value=prev[key],
                new_value=getattr(account, key)
            )
            db.session.add(change)

    # Save data
    db.session.commit()
    return account

@admin.route('/accounts/<int:id>', methods=['GET'])
@authenticate(token_auth, role=[Role.ADMIN.value])
@response(account_schema)
@other_responses({404: 'Account not found'})
def get(id):
    """Retrieve a account by id
    Admin access is not limited by ownership.
    """

    return db.session.get(Account, id) or abort(404)


@admin.route('/accounts/<account_name>', methods=['GET'])
@authenticate(token_auth, role=[Role.ADMIN.value])
@response(account_schema)
@other_responses({404: 'User not found'})
def get_by_username(account_name):
    """Retrieve a account by name
    Admin access is not limited by ownership.
    """

    user = token_auth.current_user()
    account = db.session.scalar(
        Account.select().filter_by(name=account_name)) or \
        abort(404)

    if account.owner_id != user.id:
        abort(401)

    return account
