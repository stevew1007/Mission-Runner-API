from apifairy.decorators import other_responses
from apifairy import authenticate, body, response

from flask import Blueprint, abort

from api import db
from api.models import User, Account, ChangeLog
from api.enums import Action
from api.schemas import UserSchema, UpdateUserSchema, AccountSchema, StringPaginationSchema, MissionSchema
from api.auth import token_auth
from api.decorators import paginated_response

accounts = Blueprint('accounts', __name__)
user_schema = UserSchema()
users_schema = UserSchema(many=True)
update_user_schema = UpdateUserSchema(partial=True)
account_schema = AccountSchema()
accounts_schema = AccountSchema(many=True)
mission_schema = MissionSchema()
update_account_schema = AccountSchema(partial=True)