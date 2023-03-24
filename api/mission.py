from apifairy.decorators import other_responses
from apifairy import authenticate, body, response

from flask import Blueprint, abort

from api import db
from api.models import Account, ChangeLog, Mission
from api.enums import Action, Status, Role
from api.schemas import AccountSchema, DateTimePaginationSchema,\
    MissionSchema, EmptySchema, MissionMultAcceptsSchema
from api.auth import token_auth
from api.decorators import paginated_response

missions = Blueprint('missions', __name__)
# user_schema = UserSchema()
# users_schema = UserSchema(many=True)
# update_user_schema = UpdateUserSchema(partial=True)
# account_schema = AccountSchema()
# accounts_schema = AccountSchema(many=True)
mission_schema = MissionSchema()
missions_schema = MissionSchema(many=True)
multiaccept_shema = MissionMultAcceptsSchema()
update_account_schema = AccountSchema(partial=True)


@missions.route('/accounts/<int:id>/publish_mission', methods=['POST'])
@authenticate(token_auth)
@body(mission_schema)
@response(mission_schema, 201)
@other_responses({401: 'User cannot edit account info for others',
                  403: 'Account is not activated',
                  404: 'Account not found'})
def publish(args, id):
    """Publish a mission from an account
    **Note**: User can only publish mission
     from an activated account that belongs to him
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
        object_type=type(mission).__name__,
        object_id=mission.id,
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


@missions.route('/mission/<galaxy>', methods=['GET'])
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
    """Retrieve missions published by account
    """
    account = db.session.get(Account, id) or abort(404)
    return account.missions_published.select()


@missions.route('/missions/<int:id>/accepts', methods=['POST'])
@authenticate(token_auth, role=[Role.MISSION_RUNNER.value, Role.ADMIN.value])
@response(EmptySchema, status_code=204,
          description='User accepts mission successfully')
@other_responses({400: "Mission already accepted by others",
                  403: "This mission cannot be accepted",
                  404: 'Mission not found'})
def accepts(id):
    """Accepts a mission
    **Note**: Only mission runner or admin can accepts mission.
    """

    # Issuer
    user = token_auth.current_user()

    # Setup
    mission = db.session.get(Mission, id) or abort(404)
    prev = {
        'runner': mission.runner,
        'status': mission.status
    }
    data = {
        'runner_id': user,
        'status': Status.ACCEPTED.value
    }

    # Gatekeeper
    if mission.status in \
        [Status.DRAFT.value, Status.ACCEPTED.value,
         Status.COMPLETED.value, Status.ARCHIVED.value]:
        if mission.runner is not None:
            if mission.runner_id != user.id:
                abort(400)
            if mission.publisher.owner_id == user.id:
                abort(403)
        else:
            abort(403)

    # Modification
    mission.update(data)

    # Track changes
    for key in dict(data).keys():
        if getattr(user, key) is not None:
            change = ChangeLog(
                object_type=type(mission).__name__,
                object_id=mission.id,
                operation=Action.UPDATE.value,
                requester_id=user.id,
                attribute_name=key,
                old_value=prev[key],
                new_value=getattr(user, key)
            )
            db.session.add(change)

    # Save data
    db.session.commit()

@missions.route('/missions/accept_missions', methods=['POST'])
@authenticate(token_auth, role=[Role.MISSION_RUNNER.value, Role.ADMIN.value])
@body(multiaccept_shema)
@response(EmptySchema, status_code=204,
          description='User accepts mission successfully')
@other_responses({400: "One of the Mission has already accepted by others",
                  403: "One of the mission cannot be accepted",
                  404: 'One of the Mission is not found'})
def accept_multiple(data):
    """Accepts multiple mission
    **Note**: Only mission runner or admin can accepts mission.
    """

    # Issuer
    user = token_auth.current_user()

    # Setup
    target_val = {
        'runner_id': user,
        'status': Status.ACCEPTED.value
    }

    # Gatekeeper
    # Makesure each ID checks out before changes in Database.
    for id in data["mission_id_list"]:
        mission = db.session.get(Mission, id) or abort(404)
        if mission.status in \
            [Status.DRAFT.value, Status.ACCEPTED.value,
             Status.COMPLETED.value, Status.ARCHIVED.value]:
            if mission.runner is not None:
                if mission.runner_id != user.id:
                    abort(400)
                if mission.publisher.owner_id == user.id:
                    abort(403)
            else:
                abort(403)

    # Modification
    prev = dict()
    for id in data["mission_id_list"]:
        mission = db.session.get(Mission, id) or abort(404)
        prev = {key: getattr(mission, key) for key in dict(target_val).keys()}

        mission.update(target_val)

        # Track changes
        for key in dict(target_val).keys():
            if getattr(mission, key) is not None:
                change = ChangeLog(
                    object_type=type(mission).__name__,
                    object_id=mission.id,
                    operation=Action.UPDATE.value,
                    requester_id=user.id,
                    attribute_name=key,
                    old_value=prev[key],
                    new_value=getattr(user, key)
                )
                db.session.add(change)

    # Save data
    db.session.commit()
