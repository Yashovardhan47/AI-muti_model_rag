"""File revisions, read grants, and located extraction quality metadata."""
from alembic import op
import sqlalchemy as sa
from app.core.database import Base
import app.models  # noqa: F401

revision = "0003_source_intelligence"
down_revision = "0002_evidence_audit"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    columns = {column["name"] for column in sa.inspect(connection).get_columns("files")}
    additions = {
        "family_id": sa.Column("family_id", sa.String(36), nullable=True),
        "version": sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        "supersedes_id": sa.Column("supersedes_id", sa.String(36), sa.ForeignKey("files.id", ondelete="SET NULL"), nullable=True),
        "is_current": sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        "ocr_languages": sa.Column("ocr_languages", sa.String(40), nullable=False, server_default="eng"),
        "processing_started_at": sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    }
    for name, column in additions.items():
        if name not in columns:
            # SQLite requires a batch rewrite when adding a foreign key.
            with op.batch_alter_table("files") as batch:
                batch.add_column(column)
    connection.execute(sa.text("UPDATE files SET family_id = id WHERE family_id IS NULL"))
    indexes = {item["name"] for item in sa.inspect(connection).get_indexes("files")}
    if "ix_files_family_id" not in indexes:
        op.create_index("ix_files_family_id", "files", ["family_id"])
    if "ix_files_is_current" not in indexes:
        op.create_index("ix_files_is_current", "files", ["is_current"])
    constraints = {item["name"] for item in sa.inspect(connection).get_unique_constraints("files")}
    if "uq_owner_sha256" in constraints:
        with op.batch_alter_table("files") as batch:
            batch.drop_constraint("uq_owner_sha256", type_="unique")
    if "uq_file_family_version" not in {item["name"] for item in sa.inspect(connection).get_unique_constraints("files")}:
        with op.batch_alter_table("files") as batch:
            batch.create_unique_constraint("uq_file_family_version", ["family_id", "version"])

    chunk_columns = {column["name"] for column in sa.inspect(connection).get_columns("chunks")}
    for name in ("locator_json", "quality_json"):
        if name not in chunk_columns:
            op.add_column("chunks", sa.Column(name, sa.Text(), nullable=False, server_default="{}"))
    Base.metadata.tables["file_grants"].create(bind=connection, checkfirst=True)


def downgrade():
    connection = op.get_bind()
    Base.metadata.tables["file_grants"].drop(bind=connection, checkfirst=True)
    for name in ("quality_json", "locator_json"):
        if name in {c["name"] for c in sa.inspect(connection).get_columns("chunks")}:
            op.drop_column("chunks", name)
    for name in ("ix_files_family_id", "ix_files_is_current"):
        if name in {item["name"] for item in sa.inspect(connection).get_indexes("files")}:
            op.drop_index(name, table_name="files")
    if "uq_file_family_version" in {item["name"] for item in sa.inspect(connection).get_unique_constraints("files")}:
        with op.batch_alter_table("files") as batch:
            batch.drop_constraint("uq_file_family_version", type_="unique")
    if "uq_owner_sha256" not in {item["name"] for item in sa.inspect(connection).get_unique_constraints("files")}:
        with op.batch_alter_table("files") as batch:
            batch.create_unique_constraint("uq_owner_sha256", ["owner_id", "sha256"])
    with op.batch_alter_table("files") as batch:
        for name in ("processing_started_at", "ocr_languages", "is_current", "supersedes_id", "version", "family_id"):
            if name in {c["name"] for c in sa.inspect(connection).get_columns("files")}:
                batch.drop_column(name)
