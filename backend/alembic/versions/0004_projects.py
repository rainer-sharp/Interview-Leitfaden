"""Projekte: jede Gruppe (und damit jedes Interview) gehört zu einem Projekt.

Vorhandene Gruppen kommen in das Projekt „Standardprojekt“. Gruppennamen sind nur noch je Projekt eindeutig,
damit ein kopiertes Projekt dieselben Gruppennamen haben kann.
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

DEFAULT_PROJECT = "Standardprojekt"
# Benennt die unbenannte UNIQUE(name) aus 0001, damit der Batch-Modus sie entfernen kann.
NAMING = {"uq": "uq_%(table_name)s_%(column_0_name)s"}


def upgrade() -> None:
    project = op.create_table(
        "project",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("beschreibung", sa.Text, nullable=False),
        sa.Column("ki_anweisung", sa.Text, nullable=False),
        sa.Column("angelegt_am", sa.DateTime, nullable=False),
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    op.bulk_insert(
        project,
        [{"id": 1, "name": DEFAULT_PROJECT, "beschreibung": "", "ki_anweisung": "", "angelegt_am": now}],
    )
    with op.batch_alter_table("group", naming_convention=NAMING) as batch:
        batch.add_column(sa.Column("project_id", sa.Integer, nullable=False, server_default="1"))
        batch.drop_constraint("uq_group_name", type_="unique")
        batch.create_foreign_key("fk_group_project_id", "project", ["project_id"], ["id"], ondelete="CASCADE")
        batch.create_index("ix_group_project_id", ["project_id"])
        batch.create_unique_constraint("uq_group_project_id", ["project_id", "name"])
    # Der Standardwert war nur für die vorhandenen Zeilen da.
    with op.batch_alter_table("group") as batch:
        batch.alter_column("project_id", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("group") as batch:
        batch.drop_constraint("uq_group_project_id", type_="unique")
        batch.drop_index("ix_group_project_id")
        batch.drop_constraint("fk_group_project_id", type_="foreignkey")
        batch.drop_column("project_id")
        batch.create_unique_constraint("uq_group_name", ["name"])
    op.drop_table("project")
