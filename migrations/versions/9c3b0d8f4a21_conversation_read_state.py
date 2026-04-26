"""conversation read state

Revision ID: 9c3b0d8f4a21
Revises: e2e2a8858e20
Create Date: 2026-04-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9c3b0d8f4a21'
down_revision = 'e2e2a8858e20'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'conversation_read_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('peer_id', sa.Integer(), nullable=False),
        sa.Column('last_read_time', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['peer_id'], ['user.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'peer_id',
                            name='uq_conversation_read_state_user_peer'),
    )
    with op.batch_alter_table('conversation_read_state', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_conversation_read_state_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_conversation_read_state_peer_id'), ['peer_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_conversation_read_state_last_read_time'), ['last_read_time'], unique=False)


def downgrade():
    with op.batch_alter_table('conversation_read_state', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_conversation_read_state_last_read_time'))
        batch_op.drop_index(batch_op.f('ix_conversation_read_state_peer_id'))
        batch_op.drop_index(batch_op.f('ix_conversation_read_state_user_id'))
    op.drop_table('conversation_read_state')
