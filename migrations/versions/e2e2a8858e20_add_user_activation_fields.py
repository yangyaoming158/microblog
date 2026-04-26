"""add user activation fields

Revision ID: e2e2a8858e20
Revises: f78d6f43dd8e
Create Date: 2026-04-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2e2a8858e20'
down_revision = 'f78d6f43dd8e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=False,
                                      server_default=sa.true()))
        batch_op.add_column(sa.Column('activation_token', sa.String(length=128),
                                      nullable=True))


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('activation_token')
        batch_op.drop_column('is_active')
