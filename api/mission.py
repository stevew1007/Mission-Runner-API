from apifairy.decorators import other_responses
from apifairy import authenticate, body, response

from flask import Blueprint, abort

from api import db
from api.models import User, Account, ChangeLog, Mission
from api.enums import Action, Status, Role
from api.schemas import UserSchema, UpdateUserSchema, AccountSchema, DateTimePaginationSchema, MissionSchema, EmptySchema
from api.auth import token_auth
from api.decorators import paginated_response

missions = Blueprint('missions', __name__)
user_schema = UserSchema()
users_schema = UserSchema(many=True)
update_user_schema = UpdateUserSchema(partial=True)
account_schema = AccountSchema()
accounts_schema = AccountSchema(many=True)
mission_schema = MissionSchema()
missions_schema = MissionSchema(many=True)
update_account_schema = AccountSchema(partial=True)

@missions.route('/accounts/<int:id>/publish_mission', methods=['POST'])
@authenticate(token_auth)
@body(mission_schema)
@response(mission_schema, 201)
@other_responses({401: 'User cannot edit account info for others', 403: 'Account is not activated', 404: 'Account not found'})
def publish(args, id):
    """Publish a mission from a account
    **Note**: User can only publish mission from an activated account that belong to him
    """

    # Issuer
    user = token_auth.current_user()

    # Setup
    account = db.session.get(Account, id) or abort(404)

    # Gatekeeper
    if account.owner_id != user.id:
        abort(401)
    if not account.is_activated():
        abort(403)

    # Modification
    # account.update(data)
    mission = Mission(publisher=account, **args)
    db.session.add(mission)
    db.session.commit()

    # Track changes
    change = ChangeLog(
        object_type=type(user).__name__,
        object_id = user.id,
        operation=Action.INSERT.value,
        requester_id=user.id,
        attribute_name='',
        old_value="",
        new_value=f"Add Mission ID: {mission.id}"
    )

    # Save data
    db.session.add(change)
    db.session.commit()
    return account

@missions.route('/missions/<int:id>', methods=['GET'])
@authenticate(token_auth)
@response(mission_schema)
@other_responses({404: 'Mission not found'})
def get(id):
    """Retrieve a mission by id
    """
    return db.session.get(Mission, id) or abort(404)

@missions.route('/mission/<galaxy>', method=['GET'])
@authenticate(token_auth)
@paginated_response(missions_schema, order_by=Mission.created, 
                    order_direction='desc',
                    pagination_schema=DateTimePaginationSchema)
@other_responses({404: 'Mission not found'})
def get_byGalaxy(galaxy):
    """Retrieve list of missions by galaxy
    """
    return db.session.scalar(Mission.select().filter_by(galaxy=galaxy)) or \
        abort(404)

@missions.route('/accounts/<int:id>/missions', methods=['GET'])
@authenticate(token_auth)
@paginated_response(missions_schema, order_by=Mission.created, 
                    order_direction='desc',
                    pagination_schema=DateTimePaginationSchema)
@other_responses({404: 'Account not found'})
def get_byOwner(id):
    """Retrieve list of missions published by this account
    """
    account = db.session.get(Account, id) or abort(404)
    return account.missions_published.select()

@missions.route('/missions/<int:id>/accepts', methods=['POST'])
@authenticate(token_auth, role=[Role.MISSION_RUNNER])
@response(EmptySchema, status_code=204,
          description='User accepts mission successfully')
@other_responses({400: "Mission already accepted by others", 403: "User cannot accepts mission published by himself", 409: "User already accepts the mission", 404: 'Mission not found'})
def accepts(id):
     """Accepts a mission
    **Note**: Only activated user can accepts mission.
    """

    # Issuer
    user = token_auth.current_user()

    # Setup
    mission = db.session.get(Mission, id) or abort(404)
    prev_user = mission.runner

    # Gatekeeper
    if mission.runner is not None:
        if mission.runner_id == user.id:
            abort(409)
        else:
            abort(400)
    if mission.publisher.owner_id == user.id:
        abort(403)

    # Modification
    mission.runner = user
    mission.status = Status.ACCEPTED.value

    # Track changes
    change = ChangeLog(
        object_type=type(mission).__name__,
        object_id = mission.id,
        operation=Action.UPDATE.value,
        requester_id=user.id,
        attribute_name='runner',
        old_value=prev,
        new_value=account.activated
    )

    # Save data
    db.session.commit()
    return account