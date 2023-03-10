from apifairy.decorators import other_responses
from flask import Blueprint, abort
from apifairy import authenticate, body, response

from api import db
from api.models import User, Account, ChangeLog
from api.enums import Action
from api.schemas import UserSchema, UpdateUserSchema, EmptySchema, AccountSchema
from api.auth import token_auth
from api.decorators import paginated_response

accounts = Blueprint('accounts', __name__)
user_schema = UserSchema()
users_schema = UserSchema(many=True)
update_user_schema = UpdateUserSchema(partial=True)
account_schema = AccountSchema()
accounts_schema = AccountSchema(many=True)

@accounts.route('/accounts', methods=['POST'])
@authenticate(token_auth)
@body(account_schema)
@response(account_schema, 201)
def new(args):
    """Register a new account
    Account is registered under the logined user. Only admin is allowed to add account for other user.
    """
    # Issuer
    user = token_auth.current_user()

    # Setup
    account = Account(owner=user, **args)
    db.session.add(account)
    db.session.commit()

    # Track changes
    change = ChangeLog(
        object_type=type(user).__name__,
        object_id = user.id,
        operation=Action.INSERT.value,
        requester_id=user.id,
        attribute_name='',
        old_value="",
        new_value=f"Add Account ID: {account.id}"
    )

    # Save data
    db.session.add(change)
    db.session.commit()
    return account

@accounts.route('/accounts/<int:id>', methods=['GET'])
@authenticate(token_auth)
@response(account_schema)
@other_responses({404: 'Account not found'})
def get(id):
    """Retrieve a account by id"""
    return db.session.get(Account, id) or abort(404)


@accounts.route('/accounts/<account_name>', methods=['GET'])
@authenticate(token_auth)
@response(account_schema)
@other_responses({404: 'User not found'})
def get_by_username(account_name):
    """Retrieve a account by name"""
    return db.session.scalar(Account.select().filter_by(name=account_name)) or \
        abort(404)


# @users.route('/me', methods=['GET'])
# @authenticate(token_auth)
# @response(user_schema)
# def me():
#     """Retrieve the authenticated user"""
#     return token_auth.current_user()


# @users.route('/me', methods=['PUT'])
# @authenticate(token_auth)
# @body(update_user_schema)
# @response(user_schema)
# def put(data):
#     """Edit user information"""
#     user = token_auth.current_user()
#     if 'password' in data and ('old_password' not in data or not user.verify_password(data['old_password'])):
#         abort(400)
#     user.update(data)
#     db.session.commit()
#     return user


# @users.route('/me/following', methods=['GET'])
# @authenticate(token_auth)
# @paginated_response(users_schema, order_by=User.username)
# def my_following():
#     """Retrieve the users the logged in user is following"""
#     user = token_auth.current_user()
#     return user.following.select()


# @users.route('/me/followers', methods=['GET'])
# @authenticate(token_auth)
# @paginated_response(users_schema, order_by=User.username)
# def my_followers():
#     """Retrieve the followers of the logged in user"""
#     user = token_auth.current_user()
#     return user.followers.select()


# @users.route('/me/following/<int:id>', methods=['GET'])
# @authenticate(token_auth)
# @response(EmptySchema, status_code=204,
#           description='User is followed.')
# @other_responses({404: 'User is not followed'})
# def is_followed(id):
#     """Check if a user is followed"""
#     user = token_auth.current_user()
#     followed_user = db.session.get(User, id) or abort(404)
#     if not user.is_following(followed_user):
#         abort(404)
#     return {}


# @users.route('/me/following/<int:id>', methods=['POST'])
# @authenticate(token_auth)
# @response(EmptySchema, status_code=204,
#           description='User followed successfully.')
# @other_responses({404: 'User not found', 409: 'User already followed.'})
# def follow(id):
#     """Follow a user"""
#     user = token_auth.current_user()
#     followed_user = db.session.get(User, id) or abort(404)
#     if user.is_following(followed_user):
#         abort(409)
#     user.follow(followed_user)
#     db.session.commit()
#     return {}


# @users.route('/me/following/<int:id>', methods=['DELETE'])
# @authenticate(token_auth)
# @response(EmptySchema, status_code=204,
#           description='User unfollowed successfully.')
# @other_responses({404: 'User not found', 409: 'User is not followed.'})
# def unfollow(id):
#     """Unfollow a user"""
#     user = token_auth.current_user()
#     unfollowed_user = db.session.get(User, id) or abort(404)
#     if not user.is_following(unfollowed_user):
#         abort(409)
#     user.unfollow(unfollowed_user)
#     db.session.commit()
#     return {}


# @users.route('/users/<int:id>/following', methods=['GET'])
# @authenticate(token_auth)
# @paginated_response(users_schema, order_by=User.username)
# @other_responses({404: 'User not found'})
# def following(id):
#     """Retrieve the users this user is following"""
#     user = db.session.get(User, id) or abort(404)
#     return user.following.select()


# @users.route('/users/<int:id>/followers', methods=['GET'])
# @authenticate(token_auth)
# @paginated_response(users_schema, order_by=User.username)
# @other_responses({404: 'User not found'})
# def followers(id):
#     """Retrieve the followers of the user"""
#     user = db.session.get(User, id) or abort(404)
#     return user.followers.select()
