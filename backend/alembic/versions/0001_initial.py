"""Erstes Schema: Gruppen, Kataloge, Fragen, Interviews, Antworten, Audit-Log."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "group",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("beschreibung", sa.Text, nullable=False),
    )
    op.create_table(
        "questionnaire",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("group_id", sa.Integer, sa.ForeignKey("group.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("importiert_am", sa.DateTime, nullable=False),
        sa.UniqueConstraint("group_id", "name", "version"),
    )
    op.create_table(
        "question",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "questionnaire_id", sa.Integer, sa.ForeignKey("questionnaire.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("abschnitt", sa.String(200), nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("hinweis", sa.Text, nullable=False),
        sa.Column("pflicht", sa.Boolean, nullable=False),
        sa.Column("typ", sa.String(20), nullable=False),
    )
    op.create_table(
        "interview",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "questionnaire_id", sa.Integer, sa.ForeignKey("questionnaire.id", ondelete="RESTRICT"),
            nullable=False, index=True,
        ),
        sa.Column("person", sa.String(200), nullable=False),
        sa.Column("organisation", sa.String(200), nullable=False),
        sa.Column("datum", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("gesamtnotiz", sa.Text, nullable=False),
    )
    op.create_table(
        "answer",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("interview_id", sa.Integer, sa.ForeignKey("interview.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("question_snapshot", sa.JSON, nullable=False),
        sa.Column("notiz", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("geaendert_am", sa.DateTime, nullable=False),
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("entitaet", sa.String(100), nullable=False),
        sa.Column("aktion", sa.String(50), nullable=False),
        sa.Column("zeitpunkt", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    for table in ("audit_log", "answer", "interview", "question", "questionnaire", "group"):
        op.drop_table(table)
