"""Independent web accounts and revocable persistent sessions."""
from alembic import op
from app.models.auth import WebAccount, WebSession
revision = "b214a11c0180"
down_revision = "59aa15b75bdf"
branch_labels = None
depends_on = None


def upgrade():
    WebAccount.__table__.create(op.get_bind())
    WebSession.__table__.create(op.get_bind())


def downgrade():
    WebSession.__table__.drop(op.get_bind())
    WebAccount.__table__.drop(op.get_bind())
