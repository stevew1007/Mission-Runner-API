# import random
import click
from flask import Blueprint

# from faker import Faker
from api.app import db
from api.models import User
from api.enums import Role

cmd = Blueprint('cmd', __name__)
# faker = Faker()


@cmd.cli.command()
# @click.argument('num', type=int)
def admin():  # pragma: no cover
    """Create the admin user."""
    db.create_all()
    user = User(
            username='admin',
            email='admin@example.com',
            password='admin',
            im_number='10000',
            role=Role.ADMIN.value)
    
    db.session.add(user)
    db.session.commit()

    # db.session.commit()
    print('Admin added.')


@cmd.cli.command()
# @click.argument('num', type=int)
def dropall():
    """Reset database and drop all data."""
    db.session.close()
    db.drop_all()
