# from api import mission
from tests.base_test_case import BaseTestCase, TestConfigWithAuth
# from api.app import db
# from api.models import Mission
from api.enums import Role, Action, Status
from tests.util import check_last_log_entry


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
        self.runner_id = rv.json['id']

        # Set runner role
        rv = self.client.put(
            f'/api/admin/users/{self.runner_id}/setrole', json={
                'role': Role.MISSION_RUNNER.value
            }, headers={'Authorization': f'Bearer {self.admin_access_token}'})
        assert rv.status_code == 204

        # Login with runner
        rv = self.client.post('/api/tokens', auth=('runner', 'running'))
        assert rv.status_code == 200
        self.runner_access_token = rv.json['access_token']

        # Data options to be used in tests
        self.galaxies = ['YP-J33', 'N5Y-4N', 'H-PA29']
        self.titles = [
            'jump gate', 'blood raider',
            'guristas', 'angel', 'serpentis', 'sansha']

    def test_publish_mission(self):
        rv = self.client.post(
            f'/api/accounts/{self.publihser_account_id}/publish_mission',
            json={
                'title': 'jump gate',
                'galaxy': 'YP-J33',
                'created': '2023-03-20T03:28:00Z',
                'expired': '2023-04-20T03:28:00Z',
                'bounty': 15000000
            },
            headers={'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 201
        mission_id = rv.json['id']

        # Check if the mission is created
        mission_rv = self.client.get(
            f'/api/missions/{mission_id}',
            headers={'Authorization': f'Bearer {self.publisher_access_token}'})
        assert mission_rv.status_code == 200

        # Check if the mission info is correct
        assert mission_rv.json['title'] == 'jump gate'
        assert mission_rv.json['galaxy'] == 'YP-J33'
        assert mission_rv.json['created'] == '2023-03-20T03:28:00Z'
        assert mission_rv.json['expired'] == '2023-04-20T03:28:00Z'
        assert mission_rv.json['bounty'] == 15000000
        assert mission_rv.json['status'] == Status.PUBLISHED.value
        assert mission_rv.json['publisher']['id'] == self.publihser_account_id

        check_last_log_entry(
            n=1, old={}, new={},
            object_type='Mission', object_id=mission_id,
            requester_id=self.publihser_user_id, operation=Action.INSERT)

    # Test if user can get missions by galaxy
    def test_get_missions_by_galaxy(self):
        # generate 10 missions with random galaxy and title
        for i in range(10):
            rv = self.client.post(
                f"/api/accounts/{self.publihser_account_id}/publish_mission",
                json={
                    'title': self.titles[i % 6],
                    'galaxy': self.galaxies[i % 3],
                    'created': '2023-03-20T03:28:00Z',
                    'expired': '2023-04-20T03:28:00Z',
                    'bounty': 15000000
                },
                headers={
                    'Authorization': f'Bearer {self.publisher_access_token}'})
            assert rv.status_code == 201
            mission_id = rv.json['id']

            check_last_log_entry(
                n=1, old={}, new={},
                object_type='Mission', object_id=mission_id,
                requester_id=self.publihser_user_id, operation=Action.INSERT)

        # get missions by galaxy
        for galaxy in self.galaxies:
            rv = self.client.get(
                f"/api/missions/{galaxy}",
                headers={
                    'Authorization': f'Bearer {self.publisher_access_token}'})
            assert rv.status_code == 200
            # assert len(rv.json) == len()

            # check if the missions are correct
            for mission in rv.json['data']:
                assert mission['galaxy'] == galaxy

    def test_get_missions_by_account(self):
        # Create new user
        rv = self.client.post('/api/users', json={
            'username': 'new',
            'email': 'new@example.com',
            'im_number': '268201234',
            'password': 'new'
        })
        assert rv.status_code == 201
        user_id = rv.json['id']

        # Login with publisher
        rv = self.client.post('/api/tokens', auth=('new', 'new'))
        assert rv.status_code == 200
        user_access = rv.json['access_token']
        # user_id = rv.json['user_id']

        # generate 3 accounts
        accounts_info = list()
        for i in range(3):
            rv = self.client.post('/api/accounts', json={
                'name': f'{i+1}0seconds',
                "lp_point": 100
            }, headers={
                'Authorization': f'Bearer {user_access}'})
            assert rv.status_code == 201
            acc_id = rv.json['id']
            accounts_info.append(acc_id)

            check_last_log_entry(
                n=1, old={}, new={},
                object_type='Account', object_id=acc_id,
                requester_id=user_id, operation=Action.INSERT
            )

            # Activate account
            rv = self.client.post(
                f'/api/admin/accounts/{acc_id}/activate',
                headers={'Authorization': f'Bearer {self.admin_access_token}'})
            assert rv.status_code == 204

            check_last_log_entry(
                n=1, old={'activated': '0'}, new={'activated': '1'},
                object_type='Account', object_id=acc_id,
                requester_id=self.admin_id, operation=Action.UPDATE
            )

        mission_data = {id: [] for id in accounts_info}

        # generate 10 missions with random account
        for i in range(10):
            rv = self.client.post(
                f"/api/accounts/{accounts_info[i % 3]}/publish_mission",
                json={
                    'title': self.titles[i % 6],
                    'galaxy': self.galaxies[i % 3],
                    'created': '2023-03-20T03:28:00Z',
                    'expired': '2023-04-20T03:28:00Z',
                    'bounty': 15000000
                },
                headers={
                    'Authorization': f'Bearer {user_access}'})
            assert rv.status_code == 201
            mission_data[accounts_info[i % 3]].append(rv.json)

            check_last_log_entry(
                n=1, old={}, new={},
                object_type='Mission', object_id=rv.json['id'],
                requester_id=user_id, operation=Action.INSERT
            )

        # Get missions by account
        for account_id in accounts_info:
            rv = self.client.get(
                f"/api/accounts/{account_id}/missions",
                headers={
                    'Authorization': f'Bearer {user_access}'})
            assert rv.status_code == 200

            # check if the rv.json['data'] have same data as mission_data
            # (only check id for publisher because User.last_seen changes)
            for ret, data in zip(rv.json['data'], mission_data[account_id]):
                assert ret['publisher']['id'] == data['publisher']['id']
                for key in ret.keys():
                    if key != 'publisher':
                        assert ret[key] == data[key]

    def test_accept_mission(self):
        rv = self.client.post(
            f"/api/accounts/{self.publihser_account_id}/publish_mission",
            json={
                'title': self.titles[0],
                'galaxy': self.galaxies[0],
                'created': '2023-03-20T03:28:00Z',
                'expired': '2023-04-20T03:28:00Z',
                'bounty': 15000000
            },
            headers={
                'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 201

        mission_id = rv.json['id']

        # Accept mission
        rv = self.client.post(
            f"/api/missions/{mission_id}/accept",
            headers={
                'Authorization': f'Bearer {self.runner_access_token}'})
        assert rv.status_code == 204

        # Check if the action is logged
        old = {'runner': '', 'status': Status.PUBLISHED.value}
        new = {'runner': self.runner_id, 'status': Status.ACCEPTED.value}
        check_last_log_entry(
            n=2, old=old, new=new,
            object_type='Mission', object_id=mission_id,
            requester_id=self.runner_id, operation=Action.UPDATE)
