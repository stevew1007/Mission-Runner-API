from tests.base_test_case import BaseTestCase, TestConfigWithAuth
# from api.app import db
# from api.models import Account, ChangeLog
from api.enums import Role


class AdminTest(BaseTestCase):
    config = TestConfigWithAuth

    def setUp(self):
        super().setUp()

        # Login with admin
        rv = self.client.post('/api/tokens', auth=('test', 'foo'))
        assert rv.status_code == 200
        self.admin_access_token = rv.json['access_token']

        # Create publisher
        rv = self.client.post('/api/users', json={
            'username': 'publisher',
            'email': 'publisher@example.com',
            'im_number': '268204232',
            'password': 'publish'
        })
        assert rv.status_code == 201
        self.publihser_user_id = rv.json['id']

        # Login with publisher
        rv = self.client.post('/api/tokens', auth=('publisher', 'publish'))
        assert rv.status_code == 200
        self.publisher_access_token = rv.json['access_token']
        name = 'Qxlt4 14'
        rv = self.client.post('/api/accounts', json={
            'name': name,
            "lp_point": 100
        }, headers={'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 201
        self.publihser_account_id = rv.json['id']

    def test_get_all_user(self):
        rv = self.client.get(
            '/api/admin/users',
            headers={'Authorization': f'Bearer {self.admin_access_token}'})
        assert rv.status_code == 200
        for usr_ser in rv.json['data']:
            id = usr_ser["id"]
            user_rv = self.client.get(
                f"/api/users/{id}",
                headers={
                    'Authorization': f'Bearer {self.publisher_access_token}'}
            )
            assert user_rv.status_code == 200

            for key in usr_ser.keys():
                if key != 'last_seen':
                    assert user_rv.json[key] == usr_ser[key]

        rv = self.client.get(
            '/api/admin/users',
            headers={'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 403

    def test_get_all_account(self):
        rv = self.client.get(
            '/api/admin/accounts',
            headers={'Authorization': f'Bearer {self.admin_access_token}'})
        assert rv.status_code == 200

        # account_lst = Account.select().order_by(Account.id.desc())

        # assert len(rv.json['data']) == last_account.id

        for acc_ser in rv.json['data']:
            id = acc_ser["id"]
            acc_rv = self.client.get(
                f"/api/accounts/{id}",
                headers={
                    'Authorization': f'Bearer {self.publisher_access_token}'}
            )
            assert acc_rv.status_code == 200

            for key in acc_ser.keys():
                if key != 'owner':
                    assert acc_rv.json[key] == acc_ser[key]

    def test_activate_account(self):
        # Activate account
        rv = self.client.post(
            f'/api/admin/accounts/{self.publihser_account_id}/activate',
            headers={'Authorization': f'Bearer {self.admin_access_token}'})
        assert rv.status_code == 204

        account_rv = self.client.get(
            f"/api/accounts/{self.publihser_account_id}",
            headers={'Authorization': f'Bearer {self.publisher_access_token}'}
        )
        assert account_rv.status_code == 200
        assert account_rv.json['activated']

        # Deactivate account
        rv = self.client.post(
            f'/api/admin/accounts/{self.publihser_account_id}/deactivate',
            headers={'Authorization': f'Bearer {self.admin_access_token}'})
        assert rv.status_code == 204

        account_rv = self.client.get(
            f"/api/accounts/{self.publihser_account_id}",
            headers={'Authorization': f'Bearer {self.publisher_access_token}'}
        )
        assert account_rv.status_code == 200
        assert not account_rv.json['activated']

    def test_set_role(self):
        # Set runner role
        rv = self.client.put(
            f'/api/admin/users/{self.publihser_user_id}/setrole', json={
                'role': Role.MISSION_RUNNER.value
            }, headers={'Authorization': f'Bearer {self.admin_access_token}'})
        assert rv.status_code == 204

        user_rv = self.client.get(
            f"/api/users/{self.publihser_user_id}",
            headers={'Authorization': f'Bearer {self.publisher_access_token}'}
        )
        assert user_rv.status_code == 200
        assert user_rv.json['role'] == Role.MISSION_RUNNER.value

        # # Create runner
        # rv = self.client.post('/api/users', json={
        #     'username': 'runner',
        #     'email': 'runner@example.com',
        #     'im_number': '268204239',
        #     'password': 'running'
        # })
        # assert rv.status_code == 201
        # runner_id = rv.json['id']

        # # Set runner role
        # rv = self.client.put(f'/api/admin/user/{runner_id}/setrole', json={
        #     'role': Role.MISSION_RUNNER.value
        # }, headers={'Authorization': f'Bearer {self.admin_access_token}'})
        # assert rv.status_code == 204

        # # Login with runner
        # rv = self.client.post('/api/tokens', auth=('runner', 'running'))
        # assert rv.status_code == 200
        # self.runner_access_token = rv.json['access_token']
