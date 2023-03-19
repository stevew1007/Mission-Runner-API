# from datetime import datetime, timedelta
# import sqlalchemy as sa
import pytest
from api.app import db
from api.models import User
from tests.base_test_case import BaseTestCase


class UserModelTests(BaseTestCase):
    def test_password_hashing(self):
        u = User(username='susan', password='cat', im_number='10000')
        assert not u.verify_password('dog')
        assert u.verify_password('cat')
        with pytest.raises(AttributeError):
            u.password

    def test_url(self):
        u = User(
            username='john', email='john@example.com',
            password='cat', im_number='10086')
        db.session.add(u)
        db.session.commit()
        assert u.url == 'http://localhost:5000/api/users/' + str(u.id)

    def test_avatar(self):
        u = User(username='john', email='john@example.com')
        assert u.avatar_url == ('https://www.gravatar.com/avatar/'
                                'd4c74594d841139328695756648b6bd6'
                                '?d=identicon')
