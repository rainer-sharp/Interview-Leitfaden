"""Audio-Aufnahmen mit Transkript je Interview und Einstellungen (Transkriptions-Server)."""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recording",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "interview_id", sa.Integer, sa.ForeignKey("interview.id", ondelete="CASCADE"), nullable=False, index=True
        ),
        sa.Column("dateiname", sa.String(255), nullable=False),
        sa.Column("pfad", sa.String(255), nullable=False),
        sa.Column("groesse", sa.BigInteger, nullable=False),
        sa.Column("hochgeladen_am", sa.DateTime, nullable=False),
        sa.Column("transkript_status", sa.String(20), nullable=False),
        sa.Column("transkript_optionen", sa.JSON, nullable=False),
        sa.Column("transkript", sa.Text, nullable=False),
        sa.Column("transkript_fehler", sa.Text, nullable=False),
        sa.Column("transkript_log", sa.Text, nullable=False),
        sa.Column("transkript_start", sa.DateTime, nullable=True),
        sa.Column("transkript_ende", sa.DateTime, nullable=True),
    )
    op.create_table(
        "setting",
        sa.Column("schluessel", sa.String(100), primary_key=True),
        sa.Column("wert", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("setting")
    op.drop_table("recording")
