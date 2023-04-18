from datetime import datetime

from apifairy import authenticate
from apifairy import body
from apifairy import response
from apifairy.decorators import other_responses
from flask import abort
from flask import Blueprint

from api import db
from api.auth import token_auth
from api.decorators import paginated_response
from api.enums import Action
from api.enums import Role
from api.enums import Status
from api.models import Account
from api.models import ChangeLog
from api.models import Mission
from api.schemas import AccountSchema
from api.schemas import DateTimePaginationSchema
from api.schemas import EmptySchema
from api.schemas import MissionMultAcceptsSchema
from api.schemas import MissionSchema

missions = Blueprint('missions', __name__)
mission_schema = MissionSchema()
missions_schema = MissionSchema(many=True)
multiaccept_shema = MissionMultAcceptsSchema()
update_account_schema = AccountSchema(partial=True)


@missions.route('/accounts/<int:id>/publish_mission', methods=['POST'])
@authenticate(token_auth)
@body(mission_schema)
@response(mission_schema, 201)
@other_responses({
    401: 'User cannot edit account info for others',
    403: 'Account is not activated',
    404: 'Account not found',
})
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
    if args.get('expired') is not None:
        # Make sure the expired time is valid
        if args.get('expired').timestamp() < datetime.utcnow().timestamp():
            abort(400, 'Expired time is invalid')

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
        old_value='',
        new_value=f'Add Mission ID: {mission.id}',
    )

    # Save data
    db.session.add(change)
    db.session.commit()
    return mission


@missions.route('/missions/<int:id>', methods=['GET'])
@authenticate(token_auth)
@response(mission_schema)
@other_responses({404: 'Mission not found'})
def get(id):
    """Retrieve a mission by id
    """
    return db.session.get(Mission, id) or abort(404)


@missions.route('/missions/<galaxy>', methods=['GET'])
@authenticate(token_auth)
@paginated_response(
    missions_schema, order_by=Mission.created,
    order_direction='desc',
    pagination_schema=DateTimePaginationSchema,
)
def get_byGalaxy(galaxy):
    """Retrieve list of missions by galaxy
    """
    return Mission.select().filter_by(galaxy=galaxy)


@missions.route('/accounts/<int:id>/missions', methods=['GET'])
@authenticate(token_auth)
@paginated_response(
    missions_schema, order_by=Mission.created,
    order_direction='desc',
    pagination_schema=DateTimePaginationSchema,
)
@other_responses({404: 'Account not found'})
def get_byOwner(id):
    """Retrieve missions published by account
    """
    account = db.session.get(Account, id) or abort(404)
    return account.missions_published.select()


@missions.route('/missions/<int:id>/<string:action>', methods=['POST'])
@authenticate(token_auth)
@response(
    EmptySchema, status_code=204,
    description='Mission status updated successfully',
)
@other_responses({
    401: 'Operation not allowed',
    403: 'Mission expired',
    404: 'Mission not found',
})
def next_step(id, action):
    """Update mission status
    Update mission status to the next step.

    You can only call action
    specified in the next_step property. Program will error out
    if action is invalid.

    Check `api.enums.Status.next` for the completed workflow

    Mark mission `ISSUE` if discripency found useing issue endpoint.
    """
    # Issuer
    user = token_auth.current_user()

    # Setup
    mission = db.session.get(Mission, id) or abort(404)
    prev = {
        'status': mission.status,
    }
    data = {
        'status': action,
    }

    # Gatekeeper
    if Status.isTerminal(mission.status):
        # Mission in terminal state cannot be updated by this EP.
        abort(401)

    if action not in mission.next_step:
        abort(401)

    if action == Status.PUBLISHED.value:
        # This handles the excption case when runner cannot complete mission
        # and make it available for other runner to accept
        if mission.runner_id != user.id:
            abort(401)

        prev['runner'] = '' if mission.runner is None else mission.runner.id
        data['runner'] = None

    if action == Status.ACCEPTED.value:
        if mission.expired < datetime.utcnow():
            abort(403)  # Only consider expiry when accepts mission.
        if user.role == Role.MISSION_PUBLISHER.value:
            abort(401)  # Publisher access cannot accepts mission

        prev['runner'] = '' if mission.runner is None else mission.runner.id
        data['runner'] = user

    # Accepted runner only
    if action in [Status.COMPLETED.value, Status.DONE.value]:
        if mission.runner_id != user.id:
            abort(401)

    # Mission Onwer only
    if action in [Status.PAID.value, Status.ARCHIVED.value]:
        if mission.publisher.owner_id != user.id:
            abort(401)

    # Modification
    mission.update(data)

    # Track changes
    for key in dict(data).keys():
        if getattr(mission, key) is not None:
            prev_val = prev[key]
            new_val = getattr(mission, key).id if key == 'runner' \
                else getattr(mission, key)
            change = ChangeLog(
                object_type=type(mission).__name__,
                object_id=mission.id,
                operation=Action.UPDATE.value,
                requester_id=user.id,
                attribute_name=key,
                old_value=prev_val,
                new_value=new_val,
            )
            db.session.add(change)

    # Save data
    db.session.commit()
