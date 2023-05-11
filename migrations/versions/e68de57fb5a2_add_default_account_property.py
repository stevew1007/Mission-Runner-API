"""Add default_account property

Revision ID: e68de57fb5a2
Revises: 3be4d7b378d6
Create Date: 2023-04-13 23:33:33.456119

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e68de57fb5a2'
down_revision = '3be4d7b378d6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('mission', schema=None) as batch_op:
        batch_op.alter_column('runner_id',
               existing_type=sa.INTEGER(),
               nullable=True)

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('default_accunt_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key(batch_op.f('fk_users_default_accunt_id_accounts'), 'accounts', ['default_accunt_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_users_default_accunt_id_accounts'), type_='foreignkey')
        batch_op.drop_column('default_accunt_id')

    with op.batch_alter_table('mission', schema=None) as batch_op:
        batch_op.alter_column('runner_id',
               existing_type=sa.INTEGER(),
               nullable=False)

    # ### end Alembic commands ###