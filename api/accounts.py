import requests
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
from api.models import Account
from api.models import ChangeLog
from api.schemas import AccountSchema
from api.schemas import EmptySchema
from api.schemas import StringPaginationSchema
from api.schemas import UpdateUserSchema
from api.schemas import UserSchema

accounts = Blueprint('accounts', __name__)
user_schema = UserSchema()
users_schema = UserSchema(many=True)
update_user_schema = UpdateUserSchema(partial=True)
account_schema = AccountSchema()
accounts_schema = AccountSchema(many=True)
update_account_schema = AccountSchema(partial=True)


@accounts.route('/accounts', methods=['POST'])
@authenticate(token_auth)
@body(account_schema)
@response(account_schema, 201)
@other_responses({
    404: 'Cannot find valid account',
})
def new(args):
    """Register a new account

    Account is registered under the logined user.
    **Note**: Only admin can edit account owned by other user.
    """
    # Issuer
    user = token_auth.current_user()

    # Gatekeeper
    url = 'https://esi.evetech.net/latest/universe/' +\
        'ids/?datasource=tranquility&language=en'

    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache',
    }

    response = requests.post(url, json=[args.get('name')], headers=headers)
    if response.status_code == 200:
        id_data = response.json()
        if not id_data:
            abort(404)
        character_id = id_data['characters'][0]['id']
        args['esi_id'] = character_id

    # Setup
    account = Account(owner=user, **args)
    db.session.add(account)
    db.session.commit()

    # Track changes
    change = ChangeLog(
        object_type=type(account).__name__,
        object_id=account.id,
        operation=Action.INSERT.value,
        requester_id=user.id,
        attribute_name='',
        old_value='',
        new_value=f'Add Account ID: {account.id}',
    )

    # Save data
    db.session.add(change)
    db.session.commit()
    return account


@accounts.route('/accounts/<int:id>', methods=['GET'])
@authenticate(token_auth)
@response(account_schema)
@other_responses({
    401: 'User cannot access account info from others',
    404: 'Account not found',
})
def get(id):
    """Retrieve a account by id
    **Note**: User can only view the account owned by himself.
    """

    user = token_auth.current_user()
    account = db.session.get(Account, id) or abort(404)

    if account.owner_id != user.id:
        abort(401)

    return account


@accounts.route('/accounts/<account_name>', methods=['GET'])
@authenticate(token_auth)
@response(account_schema)
@other_responses({
    401: 'User cannot access account info from others',
    404: 'User not found',
})
def get_by_username(account_name):
    """Retrieve a account by name
    **Note**: User can only view the account owned by himself.
    """

    user = token_auth.current_user()
    account = db.session.scalar(
        Account.select().filter_by(name=account_name),
    ) or \
        abort(404)

    if account.owner_id != user.id:
        abort(401)

    return account


@accounts.route('/accounts/<int:id>', methods=['PUT'])
@authenticate(token_auth)
@body(update_account_schema)
@response(account_schema)
@other_responses({
    401: 'User cannot edit account info for others',
    404: 'Account not found',
})
def put(data, id):
    """Edit account information
    **Note**: User can only edit account info for account that belong to him
    """

    # Issuer
    user = token_auth.current_user()

    # Setup
    account = db.session.get(Account, id) or abort(404)
    prev = {key: getattr(account, key) for key in dict(data).keys()}

    # Gatekeeper
    if account.owner_id != user.id:
        abort(401)

    # Modification
    account.update(data)

    # Track changes
    for key in prev.keys():
        if getattr(account, key) == prev[key]:
            # No need to log if the change is same as the origional value.
            continue
        change = ChangeLog(
            object_type=type(account).__name__,
            object_id=account.id,
            operation=Action.UPDATE.value,
            requester_id=user.id,
            attribute_name=key,
            old_value=prev[key],
            new_value=getattr(account, key),
        )
        db.session.add(change)

    # Save data
    db.session.commit()
    return account


@accounts.route('/accounts/<int:id>/default', methods=['PUT'])
@authenticate(token_auth)
@response(
    EmptySchema, status_code=204,
    description='Set default account successfully.',
)
@other_responses({
    401: 'User cannot set default account that belongs to others',
    404: 'Account not found',
})
def setdefault(id):
    """Set account as default payment account
    """

    # Issuer
    user = token_auth.current_user()

    # Setup
    account = db.session.get(Account, id) or abort(404)
    prev = user.default_account_id or ''

    # Gatekeeper
    if account.owner_id != user.id:
        abort(401)

    # Modification
    user.default_account_id = account.id

    # Track changes
    change = ChangeLog(
        object_type=type(account).__name__,
        object_id=account.id,
        operation=Action.UPDATE.value,
        requester_id=user.id,
        attribute_name='default_account_id',
        old_value=prev,
        new_value=account.id,
    )
    db.session.add(change)
    # Save data
    db.session.commit()


@accounts.route('/accounts/default', methods=['GET'])
@authenticate(token_auth)
@response(account_schema)
@other_responses({
    404: 'User did not setup default account',
})
def get_default():
    """Retrieve the default payment account
    """
    user = token_auth.current_user()
    account = user.default_account or abort(404)
    return account


@accounts.route('/accounts', methods=['GET'])
@authenticate(token_auth)
@paginated_response(
    accounts_schema, order_by=Account.id,
    order_direction='asc',
    pagination_schema=StringPaginationSchema,
)
def account_all():
    """Retrieve all accounts
    **Note**: User can only view the account owned by himself.
    """
    user = token_auth.current_user()
    return user.accounts.select()
