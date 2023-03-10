from apifairy.decorators import other_responses
from flask import Blueprint, abort
from apifairy import authenticate, body, response

from api import db
from api.models import User, ChangeLog
from api.schemas import UserSchema, UpdateUserSchema, EmptySchema, UpdateUserRoleSchema
from api.auth import token_auth
from api.enums import Role, Action
from api.decorators import paginated_response

admin = Blueprint('admin', __name__)
user_schema = UserSchema()
users_schema = UserSchema(many=True)
update_user_schema = UpdateUserSchema(partial=True)
update_user_role = UpdateUserRoleSchema()


@admin.route('/users', methods=['GET'])
@authenticate(token_auth, role=[Role.ADMIN.value])
@paginated_response(users_schema)
def all():
    """Retrieve all users"""
    return User.select()

@admin.route('/activate/user/<int:id>', methods=['POST'])
@authenticate(token_auth, role=[Role.ADMIN.value])
@response(EmptySchema, status_code=204,
          description='User activated successfully.')
@other_responses({404: 'User not found', 409: 'User already activated'})
def activate(id):
    """Activate the user"""

    # Issuer
    requester = token_auth.current_user()

    # Setup
    user = db.session.get(User, id) or abort(404)
    prev = user.activated

    # Gatekeeper
    if user.is_activated():
        abort(409)

    # Modification
    user.activate()

    # Track changes
    change = ChangeLog(
        object_type=type(user).__name__,
        object_id = user.id,
        operation=Action.UPDATE.value,
        requester_id=requester.id,
        attribute_name='activated',
        old_value=prev,
        new_value=user.activated
    )

    # Save data
    db.session.add(change)
    db.session.commit()

@admin.route('/deactivate/user/<int:id>', methods=['POST'])
@authenticate(token_auth, role=[Role.ADMIN.value])
@response(EmptySchema, status_code=204, description='User activated successfully.')
@other_responses({404: 'User not found', 409: 'User already deactivated'})
def deactivate(id):
    """Deactivate the user"""

    # Issuer
    requester = token_auth.current_user()

    # Setup
    user = db.session.get(User, id) or abort(404)
    prev = user.activated

    # Gatekeeper
    if not user.is_activated():
        abort(409)

    # Modification
    user.deactivate()

    # Track changes
    change = ChangeLog(
        object_type=type(user).__name__,
        object_id = user.id,
        operation=Action.UPDATE.value,
        requester_id=requester.id,
        attribute_name='activated',
        old_value=prev,
        new_value=user.activated
    )

    # Save data
    db.session.add(change)
    db.session.commit()

@admin.route('/setrole/<int:id>', methods=['PUT'])
@authenticate(token_auth, role=[Role.ADMIN.value])
@body(update_user_role)
@response(EmptySchema, status_code=204, description='User role set successfully.')
@other_responses({400: 'Role does not exist', 404: 'User not found', 409: "User already set to the role specified"})
def setRole(id, to_role):
    """Set a specific role for the user"""
    
    # Issuer
    requester = token_auth.current_user()

    # Setup
    user = db.session.get(User, id) or abort(404)
    prev = user.role

    # Gatekeeper
    if not Role.isValid(to_role):
        abort(400)
    if user.role == to_role:
        abort(409)

    # Modification
    user.role = to_role

    # Track changes
    change = ChangeLog(
        object_type=type(user).__name__,
        object_id = user.id,
        operation=Action.UPDATE.value,
        requester_id=requester.id,
        attribute_name='activated',
        old_value=prev,
        new_value=user.role
    )

    # Save data
    db.session.add(change)
    db.session.commit()

@admin.route('/modify/<int:id>', methods=['PUT'])
@authenticate(token_auth, role=[Role.ADMIN.value])
@body(update_user_schema)
@response(user_schema)
@other_responses({404: 'User not found'})
def modifyUserInfo(data, id):
    """Modify information for the user
    Allow admin to modify user table of the database. **Use this power wisely**.

    Please use seperate API to set role, activate or deactivate user.
    """

    # Issuer
    requester = token_auth.current_user()

    # Setup
    user = db.session.get(User, id) or abort(404)
    prev = { key: getattr(user, key) for key in dict(data).keys() }

    # Modification
    user.update(data)

    # Track changes
    for key in dict(data).keys():
        if getattr(user, key) is not None:
            change = ChangeLog(
                object_type=type(user).__name__,
                object_id = user.id,
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
