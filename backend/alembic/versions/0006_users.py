"""Mehrbenutzer: Benutzerkonten mit Rollen, Projektzuordnung, Interviewer je Interview, Benutzer im Audit-Log.

Das erste Admin-Konto legt die App beim Start an (Passwort aus ADMIN_PASSWORD), nicht diese Migration:
das Passwort soll nicht im Migrationsverlauf landen und der Hash braucht die App-Logik.
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_user",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("benutzername", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("passwort_hash", sa.String(300), nullable=False),
        sa.Column("rolle", sa.String(20), nullable=False),
        sa.Column("aktiv", sa.Boolean, nullable=False),
        sa.Column("sitzungs_version", sa.Integer, nullable=False),
        sa.Column("angelegt_am", sa.DateTime, nullable=False),
        sa.Column("letzte_anmeldung", sa.DateTime, nullable=True),
    )
    op.create_table(
        "project_member",
        sa.Column("project_id", sa.Integer, sa.ForeignKey("project.id", ondelete="CASCADE"), primary_key=True),
        sa.Column(
            "user_id", sa.Integer, sa.ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True, index=True
        ),
    )
    with op.batch_alter_table("interview") as batch:
        batch.add_column(sa.Column("user_id", sa.Integer, nullable=True))
        batch.create_foreign_key("fk_interview_user_id", "app_user", ["user_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_interview_user_id", ["user_id"])
    with op.batch_alter_table("audit_log") as batch:
        batch.add_column(sa.Column("benutzer_id", sa.Integer, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("audit_log") as batch:
        batch.drop_column("benutzer_id")
    with op.batch_alter_table("interview") as batch:
        batch.drop_index("ix_interview_user_id")
        batch.drop_constraint("fk_interview_user_id", type_="foreignkey")
        batch.drop_column("user_id")
    op.drop_table("project_member")
    op.drop_table("app_user")
