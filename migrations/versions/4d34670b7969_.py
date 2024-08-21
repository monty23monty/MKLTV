"""empty message

Revision ID: 4d34670b7969
Revises: 8f2f19ab5aff
Create Date: 2024-08-21 15:42:55.994160

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4d34670b7969'
down_revision = '8f2f19ab5aff'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('scoreboard',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('home_score', sa.Integer(), nullable=False),
    sa.Column('away_score', sa.Integer(), nullable=False),
    sa.Column('clock', sa.String(length=10), nullable=False),
    sa.Column('period', sa.String(length=10), nullable=False),
    sa.Column('home_penalty_player1', sa.String(length=50), nullable=True),
    sa.Column('home_penalty_player2', sa.String(length=50), nullable=True),
    sa.Column('home_penalty_time1', sa.String(length=10), nullable=True),
    sa.Column('home_penalty_time2', sa.String(length=10), nullable=True),
    sa.Column('away_penalty_player1', sa.String(length=50), nullable=True),
    sa.Column('away_penalty_player2', sa.String(length=50), nullable=True),
    sa.Column('away_penalty_time1', sa.String(length=10), nullable=True),
    sa.Column('away_penalty_time2', sa.String(length=10), nullable=True),
    sa.Column('last_updated', sa.DateTime(), nullable=False),
    sa.Column('live_game_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['live_game_id'], ['live_game.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('live_game', schema=None) as batch_op:
        batch_op.add_column(sa.Column('clock', sa.String(length=10), nullable=True))
        batch_op.alter_column('period',
               existing_type=sa.INTEGER(),
               type_=sa.String(length=10),
               existing_nullable=True)
        batch_op.drop_column('away_team_sog')
        batch_op.drop_column('home_team_sog')
        batch_op.drop_column('time_remaining')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('live_game', schema=None) as batch_op:
        batch_op.add_column(sa.Column('time_remaining', sa.VARCHAR(length=50), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('home_team_sog', sa.INTEGER(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('away_team_sog', sa.INTEGER(), autoincrement=False, nullable=True))
        batch_op.alter_column('period',
               existing_type=sa.String(length=10),
               type_=sa.INTEGER(),
               existing_nullable=True)
        batch_op.drop_column('clock')

    op.drop_table('scoreboard')
    # ### end Alembic commands ###
