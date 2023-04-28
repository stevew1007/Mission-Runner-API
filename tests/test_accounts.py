from tests.base_test_case import BaseTestCase, TestConfigWithAuth
from api.app import db
from api.models import ChangeLog
from tests.util import check_last_log_entry
from api.enums import Action


class AccountTest(BaseTestCase):
    config = TestConfigWithAuth

    def setUp(self):
        super().setUp()
        # Create another user
        rv = self.client.post('/api/users', json={
            'username': 'user',
            'email': 'user@example.com',
            'im_number': '268204231',
            'password': 'dog'
        })
        assert rv.status_code == 201

        # Login with registered user
        rv = self.client.post('/api/tokens', auth=('user', 'dog'))
        assert rv.status_code == 200
        self.user_access_token = rv.json['access_token']

        # Verify with authenticated user information
        rv = self.client.get('/api/me', headers={
            'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 200
        assert rv.json['username'] == 'user'
        self.user_id = rv.json['id']

    def test_create_account(self):
        # Add account
        rv = self.client.post('/api/accounts', json={
            'name': 'nextorian',
            "lp_point": 100
        }, headers={'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 201
        account_id = rv.json['id']

        # Check if the action is logged
        last_log = db.session.scalar(
            ChangeLog.select().order_by(ChangeLog.id.desc()))
        assert type(last_log) is ChangeLog
        assert last_log.object_type == 'Account'
        assert last_log.object_id == 1
        assert last_log.requester_id == 2
        assert last_log.attribute_name == ""
        assert last_log.old_value == ""
        assert last_log.new_value == f"Add Account ID: {account_id}"

        check_last_log_entry(
            n=1, old={}, new={},
            object_type='Account', object_id=account_id,
            requester_id=self.user_id, operation=Action.INSERT)

        # Check if name should be unique
        rv = self.client.post('/api/accounts', json={
            'name': 'nextorian',
            'lp_point': 100
        }, headers={'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 400

    def test_get_account(self):
        name = 'nextorioan'
        # Add account
        rv = self.client.post('/api/accounts', json={
            'name': name,
            "lp_point": 100
        }, headers={'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 201
        account_id = rv.json['id']

        # Get by ID
        rv = self.client.get(
            f'/api/accounts/{account_id}',
            headers={'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 200
        assert rv.json['name'] == name
        assert rv.json['lp_point'] == 100

        # Get by name
        rv = self.client.get(
            f'/api/accounts/{name}',
            headers={'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 200
        assert rv.json['name'] == name
        assert rv.json['lp_point'] == 100

    def test_get_account_with_wrong_user(self):
        # Create another user
        rv = self.client.post('/api/users', json={
            'username': 'user2',
            'email': 'user2@example.com',
            'im_number': '268204232',
            'password': 'cat'
        })
        assert rv.status_code == 201

        # Add account
        name = 'nextorioan'
        rv = self.client.post('/api/accounts', json={
            'name': name,
            "lp_point": 100
        }, headers={'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 201
        account_id = rv.json['id']

        # Login with registered user
        rv = self.client.post('/api/tokens', auth=('user2', 'cat'))
        assert rv.status_code == 200
        another_access_token = rv.json['access_token']

        # Get by ID
        rv = self.client.get(
            f'/api/accounts/{account_id}',
            headers={'Authorization': f'Bearer {another_access_token}'})
        assert rv.status_code == 401

        # Get by name
        rv = self.client.get(
            f'/api/accounts/{name}',
            headers={'Authorization': f'Bearer {another_access_token}'})
        assert rv.status_code == 401

    def test_get_account_404(self):

        # Get by ID
        rv = self.client.get(
            '/api/accounts/100',
            headers={'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 404

        # Get by name
        rv = self.client.get(
            '/api/accounts/nextorian100',
            headers={'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 404

    def test_edit_account_no_changes(self):
        name = 'nextorioan'
        # Add account
        rv = self.client.post('/api/accounts', json={
            'name': name,
            "lp_point": 100
        }, headers={'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 201
        account_id = rv.json['id']
        log1 = db.session.scalar(
            ChangeLog.select().order_by(ChangeLog.id.desc()))

        rv = self.client.put(f'/api/accounts/{account_id}', json={
            'name': name,
            "lp_point": 100
        }, headers={'Authorization': f'Bearer {self.user_access_token}'})

        # Endpoint will successfully run
        assert rv.status_code == 200

        # But no log entry will be saved
        log2 = db.session.scalar(
            ChangeLog.select().order_by(ChangeLog.id.desc()))
        assert log1.id == log2.id

    def test_edit_account(self):
        name = 'nextorioan'
        # Add account
        rv = self.client.post('/api/accounts', json={
            'name': name,
            "lp_point": 100
        }, headers={'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 201
        account_id = rv.json['id']

        # Change Name
        rv = self.client.put(f'/api/accounts/{account_id}', json={
            'name': 'noraus'
        }, headers={'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 200
        assert rv.json['name'] == 'noraus'
        assert rv.json['lp_point'] == 100

        last_log = db.session.scalar(
            ChangeLog.select().order_by(ChangeLog.id.desc()))
        assert last_log.object_type == 'Account'
        assert last_log.object_id == account_id
        assert last_log.requester_id == self.user_id
        assert last_log.attribute_name == 'name'
        assert last_log.old_value == name
        assert last_log.new_value == 'noraus'

        # Change LP Point
        rv = self.client.put(f'/api/accounts/{account_id}', json={
            'lp_point': 20000
        }, headers={'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 200
        assert rv.json['name'] == 'noraus'
        assert rv.json['lp_point'] == 20000

        last_log = db.session.scalar(
            ChangeLog.select().order_by(ChangeLog.id.desc()))
        assert last_log.object_type == 'Account'
        assert last_log.object_id == account_id
        assert last_log.requester_id == self.user_id
        assert last_log.attribute_name == "lp_point"
        assert last_log.old_value == '100'
        assert last_log.new_value == '20000'

    def test_edit_account_by_other(self):
        name = 'nextorioan'
        # Add account
        rv = self.client.post('/api/accounts', json={
            'name': name,
            "lp_point": 100
        }, headers={'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 201
        account_id = rv.json['id']

        # Create another user
        rv = self.client.post('/api/users', json={
            'username': 'user2',
            'email': 'user2@example.com',
            'im_number': '268204232',
            'password': 'cat'
        })
        assert rv.status_code == 201

        # Login with another user
        rv = self.client.post('/api/tokens', auth=('user2', 'cat'))
        assert rv.status_code == 200
        another_access_token = rv.json['access_token']

        # Change Name
        rv = self.client.put(f'/api/accounts/{account_id}', json={
            'name': 'noraus'
        }, headers={'Authorization': f'Bearer {another_access_token}'})
        assert rv.status_code == 401

    def test_set_default(self):
        # Try to get default account when nothing setup yet.
        rv = self.client.get('/api/accounts/default', headers={
            'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 404

        # Add account
        name = 'nextorioan'
        rv = self.client.post('/api/accounts', json={
            'name': name,
            "lp_point": 100
        }, headers={'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 201
        account_id = rv.json['id']

        # Set default account
        rv = self.client.put(f'/api/accounts/{account_id}/default', headers={
            'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 204

        # Get default account
        rv = self.client.get('/api/accounts/default', headers={
            'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 200
        assert rv.json['id'] == account_id

        # Login with admin
        rv = self.client.post('/api/tokens', auth=('test', 'foo'))
        assert rv.status_code == 200
        admin_token = rv.json['access_token']

        # Add account to admin
        rv = self.client.post('/api/accounts', json={
            'name': 'nextorian3',
            "lp_point": 100
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert rv.status_code == 201
        account2_id = rv.json['id']

        # Set default account to admin
        rv = self.client.put(f'/api/accounts/{account2_id}/default', headers={
            'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 401

    def test_list_all_but_empty(self):
        rv = self.client.get(
            '/api/accounts',
            headers={'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 200
        assert rv.json['data'] == []

    def test_list_all(self):
        # Create another user
        rv = self.client.post('/api/users', json={
            'username': 'user2',
            'email': 'user2@example.com',
            'im_number': '268204232',
            'password': 'cat'
        })
        assert rv.status_code == 201

        # Login with registered user
        rv = self.client.post('/api/tokens', auth=('user2', 'cat'))
        assert rv.status_code == 200
        another_access_token = rv.json['access_token']

        user1_account_id = list()

        for i in range(10):
            rv = self.client.post('/api/accounts', json={
                'name': f'nextorian{i}',
                "lp_point": 100
            }, headers={'Authorization': f'Bearer {self.user_access_token}'})
            assert rv.status_code == 201
            user1_account_id.append(rv.json['id'])

        user2_account_id = list()

        for i in range(5):
            rv = self.client.post('/api/accounts', json={
                'name': f'{i}0seconds',
                "lp_point": 100
            }, headers={'Authorization': f'Bearer {another_access_token}'})
            assert rv.status_code == 201
            user2_account_id.append(rv.json['id'])

        rv = self.client.get(
            '/api/accounts',
            headers={'Authorization': f'Bearer {self.user_access_token}'})
        assert rv.status_code == 200

        assert len(rv.json['data']) == len(user1_account_id)

        for entry, id in zip(rv.json['data'], user1_account_id):
            assert entry['id'] == id

        rv = self.client.get(
            '/api/accounts',
            headers={'Authorization': f'Bearer {another_access_token}'})
        assert rv.status_code == 200

        assert len(rv.json['data']) == len(user2_account_id)

        for entry, id in zip(rv.json['data'], user2_account_id):
            assert entry['id'] == id
