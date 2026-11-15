"""KI-Analyse je Projekt (Analyse und Kurzzusammenfassung) und eigene Analyse-Anweisung je Projekt."""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("project") as batch:
        batch.add_column(sa.Column("ki_analyse_anweisung", sa.Text, nullable=False, server_default=""))
    with op.batch_alter_table("project") as batch:
        batch.alter_column("ki_analyse_anweisung", server_default=None)
    op.create_table(
        "project_analysis",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "project_id", sa.Integer, sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False, unique=True
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("analyse", sa.Text, nullable=False),
        sa.Column("kurzfassung", sa.Text, nullable=False),
        sa.Column("fehler", sa.Text, nullable=False),
        sa.Column("fortschritt", sa.String(200), nullable=False),
        sa.Column("modell", sa.String(300), nullable=False),
        sa.Column("interviews", sa.Integer, nullable=False),
        sa.Column("umfang", sa.String(300), nullable=False),
        sa.Column("bearbeitet", sa.Boolean, nullable=False),
        sa.Column("gestartet_am", sa.DateTime, nullable=True),
        sa.Column("fertig_am", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("project_analysis")
    with op.batch_alter_table("project") as batch:
        batch.drop_column("ki_analyse_anweisung")
