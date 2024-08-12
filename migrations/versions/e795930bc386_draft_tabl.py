"""draft tabl

Revision ID: e795930bc386
Revises: 3da917c729a1
Create Date: 2024-08-11 17:32:13.752714

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e795930bc386'
down_revision = '3da917c729a1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('fixture_staff', schema=None) as batch_op:
        batch_op.drop_column('published')

    with op.batch_alter_table('fixture_staff_draft', schema=None) as batch_op:
        batch_op.drop_column('published')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('fixture_staff_draft', schema=None) as batch_op:
        batch_op.add_column(sa.Column('published', sa.BOOLEAN(), autoincrement=False, nullable=True))

    with op.batch_alter_table('fixture_staff', schema=None) as batch_op:
        batch_op.add_column(sa.Column('published', sa.BOOLEAN(), autoincrement=False, nullable=True))

    # ### end Alembic commands ###
