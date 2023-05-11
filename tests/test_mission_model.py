# import pytest
from api.app import db
from api.models import Account, User, Mission
from tests.base_test_case import BaseTestCase
from datetime import datetime, timedelta


class MissionModelTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.user = db.session.scalar(
            User.select().order_by(User.id.desc()))
        self.account = Account(
            name='nextorian', lp_point=100, owner=self.user, esi_id=343563816)
        db.session.add(self.account)

    def test_create_mission(self):
        galaxies = ['YP-J33', 'N5Y-4N', 'H-PA29']
        titles = [
            'jump gate', 'blood raider',
            'guristas', 'angel', 'serpentis', 'sansha']

        # generate 10 missions and commit to database
        for i in range(10):
            mission = Mission(
                title=titles[i % 6],
                galaxy=galaxies[i % 3],
                created=datetime.utcnow(),
                expired=datetime.utcnow() + timedelta(days=30),
                bounty=15000000,
                publisher=self.account)
            db.session.add(mission)
            db.session.commit()

            # Check if the mission is created correctly
            assert mission.id == i + 1
            assert mission.title == titles[i % 6]
            assert mission.galaxy == galaxies[i % 3]
            # assert mission.created == datetime.utcnow()
