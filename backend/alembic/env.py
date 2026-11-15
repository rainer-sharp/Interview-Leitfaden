from alembic import context
from sqlalchemy import create_engine, pool

from app.config import get_settings
from app.models import Base


def run_migrations() -> None:
    # Tests können eine andere Datenbank vorgeben (z. B. um einen alten Migrationsstand zu erzeugen).
    url = context.config.attributes.get("database_url") or get_settings().database_url
    if context.is_offline_mode():
        context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


run_migrations()
