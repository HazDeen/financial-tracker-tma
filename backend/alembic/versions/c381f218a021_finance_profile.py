"""Opening balance for personal finance profiles."""
from alembic import op
import sqlalchemy as sa
revision = 'c381f218a021'
down_revision = 'b214a11c0180'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('finance_profiles', sa.Column('user_id', sa.Integer(), primary_key=True),
                    sa.Column('opening_balance', sa.Numeric(12, 2), nullable=False))


def downgrade():
    op.drop_table('finance_profiles')
