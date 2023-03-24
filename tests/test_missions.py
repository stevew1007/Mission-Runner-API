from tests.base_test_case import BaseTestCase, TestConfigWithAuth
from api.app import db
from api.models import ChangeLog
from api.enums import Role


class MissionTest(BaseTestCase):
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

        # Register an account
        rv = self.client.post('/api/accounts', json={
            'name': 'nextorian2',
            "lp_point": 100
        }, headers={'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 201
        self.publihser_account_id = rv.json['id']

        # Activate account
        rv = self.client.post(
            f'/api/admin/accounts/{self.publihser_account_id}/activate',
            headers={'Authorization': f'Bearer {self.admin_access_token}'})
        assert rv.status_code == 204

        # Create runner
        rv = self.client.post('/api/users', json={
            'username': 'runner',
            'email': 'runner@example.com',
            'im_number': '268204239',
            'password': 'running'
        })
        assert rv.status_code == 201
        runner_id = rv.json['id']

        # Set runner role
        rv = self.client.put(f'/api/admin/users/{runner_id}/setrole', json={
            'role': Role.MISSION_RUNNER.value
        }, headers={'Authorization': f'Bearer {self.admin_access_token}'})
        assert rv.status_code == 204

        # Login with runner
        rv = self.client.post('/api/tokens', auth=('runner', 'running'))
        assert rv.status_code == 200
        self.runner_access_token = rv.json['access_token']

    def test_publish_mission(self):
        rv = self.client.post(
            f'/api/accounts/{self.publihser_account_id}/publish_mission', json={
                'title': 'jump gate',
                'galaxy': 'YP-J33',
                'created': '2023-03-20T03:28:00Z',
                'expired': '2023-04-20T03:28:00Z',
                'bounty': 15000000
            },
            headers={'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 201
        mission_id = rv.json['id']

        # Check if the action is logged
        last_log = db.session.scalar(
            ChangeLog.select().order_by(ChangeLog.id.desc()))
        assert type(last_log) is ChangeLog
        assert last_log.object_type == 'Mission'
        assert last_log.object_id == mission_id
        assert last_log.requester_id == self.publihser_user_id
        assert last_log.attribute_name == ""
        assert last_log.old_value == ""
        assert last_log.new_value == f"Add Mission ID: {mission_id}"
