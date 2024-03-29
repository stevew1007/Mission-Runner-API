"""Make default_account nullable

Revision ID: f2b7cc524715
Revises: e68de57fb5a2
Create Date: 2023-04-13 23:43:39.369273

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2b7cc524715'
down_revision = 'e68de57fb5a2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('default_accunt_id',
               existing_type=sa.INTEGER(),
               nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('default_accunt_id',
               existing_type=sa.INTEGER(),
               nullable=False)

    # ### end Alembic commands ###
