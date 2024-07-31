"""Fixtures model2

Revision ID: 141ed05bfbf6
Revises: e50f7671ae0d
Create Date: 2024-07-31 14:09:16.607702

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '141ed05bfbf6'
down_revision = 'e50f7671ae0d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('fixture_staff', schema=None) as batch_op:
        batch_op.drop_constraint('fixture_staff_fixture_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(None, 'fixtures', ['fixture_id'], ['GameID'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('fixture_staff', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key('fixture_staff_fixture_id_fkey', 'games', ['fixture_id'], ['GameID'])

    # ### end Alembic commands ###
