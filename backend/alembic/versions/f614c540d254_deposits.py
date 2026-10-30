"""Saved deposits with monthly interest payouts."""
from alembic import op
import sqlalchemy as sa

revision = 'f614c540d254'
down_revision = 'e503b439c143'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('deposits',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(128), nullable=False),
        sa.Column('principal', sa.Numeric(12, 2), nullable=False),
        sa.Column('annual_rate', sa.Numeric(5, 2), nullable=False),
        sa.Column('months', sa.Integer(), nullable=False),
        sa.Column('opened_on', sa.Date(), nullable=False),
        sa.Column('paid_months', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_index('ix_deposits_user_id', 'deposits', ['user_id'])


def downgrade():
    op.drop_index('ix_deposits_user_id', table_name='deposits')
    op.drop_table('deposits')
