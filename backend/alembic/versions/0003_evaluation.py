"""KI-Bewertung je Interview (Zusammenfassung und Gesamteinschätzung durch ein LLM)."""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evaluation",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "interview_id",
            sa.Integer,
            sa.ForeignKey("interview.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("fehler", sa.Text, nullable=False),
        sa.Column("modell", sa.String(300), nullable=False),
        sa.Column("mit_transkript", sa.Boolean, nullable=False),
        sa.Column("bearbeitet", sa.Boolean, nullable=False),
        sa.Column("gestartet_am", sa.DateTime, nullable=True),
        sa.Column("fertig_am", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("evaluation")
