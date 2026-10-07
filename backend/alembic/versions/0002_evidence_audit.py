"""Persist the evidence audit alongside each assistant response."""
from alembic import op
import sqlalchemy as sa

revision = "0002_evidence_audit"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    # 0001 builds from live metadata; new databases may already contain this column.
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("chat_messages")}
    if "audit_json" not in columns:
        op.add_column("chat_messages", sa.Column("audit_json", sa.Text(), nullable=False, server_default="{}"))


def downgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("chat_messages")}
    if "audit_json" in columns:
        op.drop_column("chat_messages", "audit_json")
