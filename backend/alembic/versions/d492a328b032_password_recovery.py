"""One-time password recovery codes."""
from alembic import op
import sqlalchemy as sa

revision = 'd492a328b032'
down_revision = 'c381f218a021'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('web_recovery_codes',
                    sa.Column('account_id', sa.Integer(), sa.ForeignKey('web_accounts.id'), primary_key=True),
                    sa.Column('token_hash', sa.String(64), nullable=False))


def downgrade():
    op.drop_table('web_recovery_codes')
