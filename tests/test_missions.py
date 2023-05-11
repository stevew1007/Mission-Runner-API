# from api import mission
from unittest import mock
from tests.base_test_case import BaseTestCase, TestConfigWithAuth
# from api.app import db
# from api.models import Mission
from api.enums import Role, Action, Status
from tests.util import check_last_log_entry
from datetime import datetime
from datetime import timedelta


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
            'name': 'Isakko II',
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

    def test_publish_mission_unactiviated_account(self):
        # Register an account
        rv = self.client.post('/api/accounts', json={
            'name': 'Qxlt4 14',
            "lp_point": 100
        }, headers={'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 201
        unactivated_id = rv.json['id']

        rv = self.client.post(
            f'/api/accounts/{unactivated_id}/publish_mission',
            json={
                'title': 'jump gate',
                'galaxy': 'YP-J33',
                'created': '2023-03-20T03:28:00Z',
                'expired': (
                    datetime.utcnow()+timedelta(days=3)
                ).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'bounty': 15000000
            },
            headers={'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 403

    def test_publish_mission_account_own_by_others(self):
        # Register an account
        rv = self.client.post('/api/accounts', json={
            'name': 'isakko I',
            "lp_point": 100
        }, headers={'Authorization': f'Bearer {self.admin_access_token}'})
        assert rv.status_code == 201
        admin_account_id = rv.json['id']

        # Activate account
        rv = self.client.post(
            f'/api/admin/accounts/{admin_account_id}/activate',
            headers={'Authorization': f'Bearer {self.admin_access_token}'})
        assert rv.status_code == 204

        rv = self.client.post(
            f'/api/accounts/{admin_account_id}/publish_mission',
            json={
                'title': 'jump gate',
                'galaxy': 'YP-J33',
                'created': '2023-03-20T03:28:00Z',
                'expired': (
                    datetime.utcnow()+timedelta(days=3)
                ).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'bounty': 15000000
            },
            headers={'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 401

    def test_publish_mission_invalid_expire_time(self):
        rv = self.client.post(
            f'/api/accounts/{self.publihser_account_id}/publish_mission',
            json={
                'title': 'jump gate',
                'galaxy': 'YP-J33',
                'created': '2023-03-20T03:28:00Z',
                'expired': (
                    datetime.utcnow()-timedelta(days=1)
                ).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'bounty': 15000000
            },
            headers={'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 400

    def test_publish_mission_duplicate(self):
        timestamp = (
            datetime.utcnow()+timedelta(days=3)
        ).strftime('%Y-%m-%dT%H:%M:%SZ')
        rv = self.client.post(
            f'/api/accounts/{self.publihser_account_id}/publish_mission',
            json={
                'title': 'jump gate',
                'galaxy': 'YP-J33',
                'created': '2023-03-20T03:28:00Z',
                'expired': timestamp,
                'bounty': 15000000
            },
            headers={'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 201

        rv = self.client.post(
            f'/api/accounts/{self.publihser_account_id}/publish_mission',
            json={
                'title': 'jump gate',
                'galaxy': 'YP-J33',
                'created': '2023-03-20T03:28:00Z',
                'expired': timestamp,
                'bounty': 15000000
            },
            headers={'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 400
        assert rv.json['description'] == 'Mission already published'

        timestamp = (
            datetime.utcnow()+timedelta(days=3)
        ).strftime('%Y-%m-%dT%H:%M:%SZ')
        rv = self.client.post(
            f'/api/accounts/{self.publihser_account_id}/publish_mission',
            json={
                'title': '萨沙混乱地点 ( 跃迁门 )',
                'galaxy': 'CSOA-B',
                'created': '2023-04-20T22:58:00Z',
                'expired': timestamp,
                'bounty': 15000000
            },
            headers={'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 201

    def test_publish_mission(self):
        timestamp = (
            datetime.utcnow()+timedelta(days=3)
        ).strftime('%Y-%m-%dT%H:%M:%SZ')
        rv = self.client.post(
            f'/api/accounts/{self.publihser_account_id}/publish_mission',
            json={
                'title': 'jump gate',
                'galaxy': 'YP-J33',
                'created': '2023-03-20T03:28:00Z',
                'expired': timestamp,
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
        assert mission_rv.json['expired'] == timestamp
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
            # time.sleep(1)
            rv = self.client.post(
                f"/api/accounts/{self.publihser_account_id}/publish_mission",
                json={
                    'title': self.titles[i % 6],
                    'galaxy': self.galaxies[i % 3],
                    'created': (
                        datetime.utcnow()-timedelta(hours=i)
                    ).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'expired': (
                        datetime.utcnow()+timedelta(days=3)
                    ).strftime('%Y-%m-%dT%H:%M:%SZ'),
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
                f"/api/missions/galaxy/{galaxy}",
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
            # time.sleep(1)
            rv = self.client.post(
                f"/api/accounts/{accounts_info[i % 3]}/publish_mission",
                json={
                    'title': self.titles[i % 6],
                    'galaxy': self.galaxies[i % 3],
                    'created': (
                        datetime.now()-timedelta(hours=i)
                    ).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'expired': (
                        datetime.now()+timedelta(days=3)
                    ).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'bounty': 15000000
                },
                headers={
                    'Authorization': f'Bearer {user_access}'})
            # assert rv.json == {'message': 'Mission published'}
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

            rv_data = sorted(rv.json['data'], key=lambda x: x['id'])
            mission_data[account_id] = sorted(
                mission_data[account_id],
                key=lambda x: x['id']
            )
            # check if the rv.json['data'] have same data as mission_data
            # (only check id for publisher because User.last_seen changes)
            for ret, data in zip(rv_data, mission_data[account_id]):
                assert ret['publisher']['id'] == data['publisher']['id']
                for key in ret.keys():
                    if key != 'publisher':
                        assert ret[key] == data[key]

    def test_get_mission_by_user_and_state(self):
        # create_multiple_account
        accounts_info = list()
        for i in range(3):
            rv = self.client.post('/api/accounts', json={
                'name': f'{i+1}0seconds',
                "lp_point": 100
            }, headers={
                'Authorization': f'Bearer {self.publisher_access_token}'})
            assert rv.status_code == 201
            acc_id = rv.json['id']
            accounts_info.append(acc_id)

            check_last_log_entry(
                n=1, old={}, new={},
                object_type='Account', object_id=acc_id,
                requester_id=self.publihser_user_id, operation=Action.INSERT
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
            # time.sleep(1)
            rv = self.client.post(
                f"/api/accounts/{accounts_info[i % 3]}/publish_mission",
                json={
                    'title': self.titles[i % 6],
                    'galaxy': self.galaxies[i % 3],
                    'created': (
                        datetime.now()-timedelta(hours=i)
                    ).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'expired': (
                        datetime.now()+timedelta(days=3)
                    ).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'bounty': 15000000
                },
                headers={
                    'Authorization': f'Bearer {self.publisher_access_token}'})
            # assert rv.json == {'message': 'Mission published'}
            assert rv.status_code == 201
            # mission_data[accounts_info[i % 3]].append(rv.json)

            check_last_log_entry(
                n=1, old={}, new={},
                object_type='Mission', object_id=rv.json['id'],
                requester_id=self.publihser_user_id, operation=Action.INSERT
            )

        # Accept some mission
        for i in range(3, 10):
            # accept 3 to 10 mission
            rv = self.client.post(
                f"/api/missions/{i}/{Status.ACCEPTED.value}",
                headers={
                    'Authorization': f'Bearer {self.runner_access_token}'})
            assert rv.status_code == 204

        # Complete some mission
        for i in range(3, 7):
            rv = self.client.post(
                f"/api/missions/{i}/{Status.COMPLETED.value}",
                headers={
                    'Authorization': f'Bearer {self.runner_access_token}'})
            assert rv.status_code == 204

        # Mark some mission tobe paid
        for i in range(3, 5):
            rv = self.client.post(
                f"/api/missions/{i}/{Status.PAID.value}",
                headers={
                    'Authorization': f'Bearer {self.publisher_access_token}'})
            assert rv.status_code == 204

        # Mark some mission to be done
        rv = self.client.post(
            f"/api/missions/{3}/{Status.DONE.value}",
            headers={
                'Authorization': f'Bearer {self.runner_access_token}'})
        assert rv.status_code == 204

        mission_data = {state.value: [] for state in Status}
        for i in range(1, 11):
            # get mission status by id
            rv = self.client.get(
                f"/api/missions/{i}", headers={
                    'Authorization': f'Bearer {self.publisher_access_token}'})
            assert rv.status_code == 200
            mission_data[rv.json['status']].append(rv.json)

        rv = self.client.get(
            "/api/missions/count",
            headers={
                'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 200
        num_mission_by_state = rv.json

        for status in Status:
            # get mission by user and state
            rv = self.client.get(
                f"/api/missions/state/{status.value}", headers={
                    'Authorization': f'Bearer {self.publisher_access_token}'})
            assert rv.status_code == 200

            rv_data = sorted(rv.json['data'], key=lambda x: x['id'])
            mission_data[status.value] = sorted(
                mission_data[status.value],
                key=lambda x: x['id']
            )
            assert len(rv_data) == len(mission_data[status.value])
            if f"num_missions_{status.value}" in num_mission_by_state:
                assert len(rv_data) == num_mission_by_state[
                    f"num_missions_{status.value}"]
            # check if the rv.json['data'] have same data as mission_data
            # (only check id for publisher because User.last_seen changes)
            for ret, data in zip(rv_data, mission_data[status.value]):
                assert ret['publisher']['id'] == data['publisher']['id']
                for key in ret.keys():
                    if key != 'publisher':
                        assert ret[key] == data[key]

    def test_mission_workflow(self):
        # publish a mission
        rv = self.client.post(
            f"/api/accounts/{self.publihser_account_id}/publish_mission",
            json={
                'title': self.titles[0],
                'galaxy': self.galaxies[0],
                'created': (
                    datetime.now()-timedelta(hours=15)
                ).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'expired': (
                    datetime.utcnow()+timedelta(days=3)
                ).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'bounty': 15000000
            },
            headers={
                'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 201
        mission_id = rv.json['id']
        assert rv.json['status'] == Status.PUBLISHED.value
        assert rv.json['next_step'] == Status.next(Status.PUBLISHED.value)

        # Attempt to try invalid action
        for action in Status:
            if action.value not in Status.next(Status.PUBLISHED.value):
                rv = self.client.post(
                    f"/api/missions/{mission_id}/{action.value}",
                    headers={
                        'Authorization': f'Bearer {self.runner_access_token}'})
                assert rv.status_code == 400

        # try to accept by publisher (invalid)
        rv = self.client.post(
            f"/api/missions/{mission_id}/{Status.ACCEPTED.value}",
            headers={
                'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 401

        # accept the mission
        rv = self.client.post(
            f"/api/missions/{mission_id}/{Status.ACCEPTED.value}",
            headers={
                'Authorization': f'Bearer {self.runner_access_token}'})
        assert rv.status_code == 204

        # check if the mission is accepted
        rv = self.client.get(
            f"/api/missions/{mission_id}",
            headers={
                'Authorization': f'Bearer {self.runner_access_token}'})
        assert rv.status_code == 200
        assert rv.json['status'] == Status.ACCEPTED.value
        assert rv.json['next_step'] == Status.next(Status.ACCEPTED.value)

        old = {
            'status': Status.PUBLISHED.value,
            'runner': ""
        }
        new = {
            'status': Status.ACCEPTED.value,
            'runner': self.runner_id
        }
        check_last_log_entry(
            n=2, old=old, new=new,
            object_type='Mission', object_id=mission_id,
            requester_id=self.runner_id,
            operation=Action.UPDATE
        )

        # Attempt to try invalid action
        for action in Status:
            if action.value not in Status.next(Status.ACCEPTED.value):
                rv = self.client.post(
                    f"/api/missions/{mission_id}/{action.value}",
                    headers={
                        'Authorization': f'Bearer {self.runner_access_token}'})
                assert rv.status_code == 400

        # try to complete by publisher (invalid)
        rv = self.client.post(
            f"/api/missions/{mission_id}/{Status.COMPLETED.value}",
            headers={
                'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 401

        # complete the mission
        rv = self.client.post(
            f"/api/missions/{mission_id}/{Status.COMPLETED.value}",
            headers={
                'Authorization': f'Bearer {self.runner_access_token}'})
        assert rv.status_code == 204

        # check if the mission is completed
        rv = self.client.get(
            f"/api/missions/{mission_id}",
            headers={
                'Authorization': f'Bearer {self.runner_access_token}'})
        assert rv.status_code == 200
        assert rv.json['status'] == Status.COMPLETED.value
        assert rv.json['next_step'] == Status.next(Status.COMPLETED.value)

        check_last_log_entry(
            n=1, old={'status': Status.ACCEPTED.value},
            new={'status': Status.COMPLETED.value},
            object_type='Mission', object_id=mission_id,
            requester_id=self.runner_id,
            operation=Action.UPDATE
        )

        # Attempt to try invalid action
        for action in Status:
            if action.value not in Status.next(Status.COMPLETED.value):
                rv = self.client.post(
                    f"/api/missions/{mission_id}/{action.value}",
                    headers={
                        'Authorization': f'Bearer {self.admin_access_token}'})
                assert rv.status_code == 400

        # try to set paid by anyone other than owner (invalid)
        rv = self.client.post(
            f"/api/missions/{mission_id}/{Status.PAID.value}",
            headers={
                'Authorization': f'Bearer {self.runner_access_token}'})
        assert rv.status_code == 401
        rv = self.client.post(
            f"/api/missions/{mission_id}/{Status.PAID.value}",
            headers={
                'Authorization': f'Bearer {self.admin_access_token}'})
        assert rv.status_code == 401

        # set the mission paid
        rv = self.client.post(
            f"/api/missions/{mission_id}/{Status.PAID.value}",
            headers={
                'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 204

        # check if the mission is paid
        rv = self.client.get(
            f"/api/missions/{mission_id}",
            headers={
                'Authorization': f'Bearer {self.runner_access_token}'})
        assert rv.status_code == 200
        assert rv.json['status'] == Status.PAID.value
        assert rv.json['next_step'] == Status.next(Status.PAID.value)

        check_last_log_entry(
            n=1, old={'status': Status.COMPLETED.value},
            new={'status': Status.PAID.value},
            object_type='Mission', object_id=mission_id,
            requester_id=self.publihser_user_id,
            operation=Action.UPDATE
        )

        # Attempt to try invalid action
        for action in Status:
            if action.value not in Status.next(Status.PAID.value):
                rv = self.client.post(
                    f"/api/missions/{mission_id}/{action.value}",
                    headers={
                        'Authorization': f'Bearer {self.admin_access_token}'})
                assert rv.status_code == 400

        # try to set done by anyone other than owner (invalid)
        rv = self.client.post(
            f"/api/missions/{mission_id}/{Status.DONE.value}",
            headers={
                'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 401
        rv = self.client.post(
            f"/api/missions/{mission_id}/{Status.DONE.value}",
            headers={
                'Authorization': f'Bearer {self.admin_access_token}'})
        assert rv.status_code == 401

        # set the mission done
        rv = self.client.post(
            f"/api/missions/{mission_id}/{Status.DONE.value}",
            headers={
                'Authorization': f'Bearer {self.runner_access_token}'})
        assert rv.status_code == 204

        # check if the mission is done
        rv = self.client.get(
            f"/api/missions/{mission_id}",
            headers={
                'Authorization': f'Bearer {self.runner_access_token}'})
        assert rv.status_code == 200
        assert rv.json['status'] == Status.DONE.value
        assert rv.json['next_step'] == Status.next(Status.DONE.value)

        check_last_log_entry(
            n=1, old={'status': Status.PAID.value},
            new={'status': Status.DONE.value},
            object_type='Mission', object_id=mission_id,
            requester_id=self.runner_id,
            operation=Action.UPDATE
        )

        # All action at this point will be invalid
        for action in Status:
            rv = self.client.post(
                f"/api/missions/{mission_id}/{action.value}",
                headers={
                    'Authorization': f'Bearer {self.admin_access_token}'})
            assert rv.status_code == 400

    def test_quit_mission(self):
        # publish a mission
        rv = self.client.post(
            f"/api/accounts/{self.publihser_account_id}/publish_mission",
            json={
                'title': self.titles[0],
                'galaxy': self.galaxies[0],
                'created': '2023-03-20T03:28:00Z',
                'expired': (
                    datetime.utcnow()+timedelta(days=3)
                ).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'bounty': 15000000
            },
            headers={
                'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 201
        mission_id = rv.json['id']

        # accept the mission
        rv = self.client.post(
            f"/api/missions/{mission_id}/{Status.ACCEPTED.value}",
            headers={
                'Authorization': f'Bearer {self.runner_access_token}'})
        assert rv.status_code == 204

        # check if the mission is returned to published
        rv = self.client.get(
            f"/api/missions/{mission_id}",
            headers={
                'Authorization': f'Bearer {self.runner_access_token}'})
        assert rv.status_code == 200
        assert rv.json['status'] == Status.ACCEPTED.value

        # quit the mission by wrone id
        rv = self.client.post(
            f"/api/missions/{mission_id}/{Status.PUBLISHED.value}",
            headers={
                'Authorization': f'Bearer {self.admin_access_token}'})
        assert rv.status_code == 401
        rv = self.client.post(
            f"/api/missions/{mission_id}/{Status.PUBLISHED.value}",
            headers={
                'Authorization': f'Bearer {self.publihser_account_id}'})
        assert rv.status_code == 401

        # quit the mission
        rv = self.client.post(
            f"/api/missions/{mission_id}/{Status.PUBLISHED.value}",
            headers={
                'Authorization': f'Bearer {self.runner_access_token}'})
        assert rv.status_code == 204

        check_last_log_entry(
            n=1, old={'status': Status.ACCEPTED.value},
            new={'status': Status.PUBLISHED.value},
            object_type='Mission', object_id=mission_id,
            requester_id=self.runner_id,
            operation=Action.UPDATE
        )

        # check if the mission is returned to published
        rv = self.client.get(
            f"/api/missions/{mission_id}",
            headers={
                'Authorization': f'Bearer {self.runner_access_token}'})
        assert rv.status_code == 200
        assert rv.json['status'] == Status.PUBLISHED.value

    def test_unpublish(self):
        # publish a mission
        rv = self.client.post(
            f"/api/accounts/{self.publihser_account_id}/publish_mission",
            json={
                'title': self.titles[0],
                'galaxy': self.galaxies[0],
                'created': '2023-03-20T03:28:00Z',
                'expired': (
                    datetime.utcnow()+timedelta(days=3)
                ).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'bounty': 15000000
            },
            headers={
                'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 201
        mission_id = rv.json['id']

        # quit the mission by wrone id
        rv = self.client.post(
            f"/api/missions/{mission_id}/{Status.ARCHIVED.value}",
            headers={
                'Authorization': f'Bearer {self.admin_access_token}'})
        assert rv.status_code == 401
        rv = self.client.post(
            f"/api/missions/{mission_id}/{Status.ARCHIVED.value}",
            headers={
                'Authorization': f'Bearer {self.runner_id}'})
        assert rv.status_code == 401

        # unpublish the mission
        rv = self.client.post(
            f"/api/missions/{mission_id}/{Status.ARCHIVED.value}",
            headers={
                'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 204

    def test_with_expired_mission(self):
        # publish a mission
        rv = self.client.post(
            f"/api/accounts/{self.publihser_account_id}/publish_mission",
            json={
                'title': self.titles[0],
                'galaxy': self.galaxies[0],
                'created': '2023-03-20T03:28:00Z',
                'expired': (
                    datetime.utcnow() + timedelta(days=1)
                ).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'bounty': 15000000
            },
            headers={
                'Authorization': f'Bearer {self.publisher_access_token}'})
        assert rv.status_code == 201
        mission_id = rv.json['id']

        with mock.patch('api.mission.datetime') as dt:
            # Need to login again as the token is expired
            dt.utcnow.return_value = datetime.utcnow() + timedelta(days=2)
            rv = self.client.post('/api/tokens', auth=('runner', 'running'))
            assert rv.status_code == 200
            temp = rv.json['access_token']

            rv = self.client.post(
                f"/api/missions/{mission_id}/{Status.ACCEPTED.value}",
                headers={
                    'Authorization': f'Bearer {temp}'})
            assert rv.status_code == 403

        # accept the mission
        rv = self.client.post(
            f"/api/missions/{mission_id}/{Status.ACCEPTED.value}",
            headers={
                'Authorization': f'Bearer {self.runner_access_token}'})
        assert rv.status_code == 204

        # Other state will not effect by expriation time
        with mock.patch('api.mission.datetime') as dt:
            dt.utcnow.return_value = datetime.utcnow() + timedelta(days=2)
            # Need to login again as the token is expired
            rv = self.client.post('/api/tokens', auth=('runner', 'running'))
            assert rv.status_code == 200
            self.runner_access_token = rv.json['access_token']
            rv = self.client.post('/api/tokens', auth=('publisher', 'publish'))
            assert rv.status_code == 200
            self.publihser_access_token = rv.json['access_token']
            rv = self.client.post(
                f"/api/missions/{mission_id}/{Status.COMPLETED.value}",
                headers={
                    'Authorization': f'Bearer {self.runner_access_token}'})
            assert rv.status_code == 204

            rv = self.client.post(
                f"/api/missions/{mission_id}/{Status.PAID.value}",
                headers={
                    'Authorization': f'Bearer {self.publihser_access_token}'})
            assert rv.status_code == 204

            rv = self.client.post(
                f"/api/missions/{mission_id}/{Status.DONE.value}",
                headers={
                    'Authorization': f'Bearer {self.runner_access_token}'})
            assert rv.status_code == 204
