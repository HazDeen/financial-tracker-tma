"""Private company reports and financial figures."""
from alembic import op
import sqlalchemy as sa

revision = 'e503b439c143'
down_revision = 'd492a328b032'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('company_reports',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('company', sa.String(160), nullable=False),
        sa.Column('period', sa.String(80), nullable=False),
        sa.Column('filename', sa.String(200), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('metrics', sa.JSON(), nullable=False),
        sa.Column('content', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False))
    op.create_index('ix_company_reports_user_id', 'company_reports', ['user_id'])


def downgrade():
    op.drop_index('ix_company_reports_user_id', table_name='company_reports')
    op.drop_table('company_reports')
