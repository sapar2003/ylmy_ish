from alembic import context
from sqlalchemy import create_engine

from app import models  # noqa: F401  (modelleri metadata-a hasaba alýar)
from app.core.config import settings
from app.db.base import Base
from app.db.session import make_engine

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # SQLite-de batch migrasiýa tablisany pozup täzeden gurýar: daşary açar barlagy açyk bolsa,
    # ON DELETE CASCADE bagly ýazgylary (meselem, mugallym bellemeleri) pozardy. Şonuň üçin FK-syz.
    url = settings.database_url
    engine = create_engine(url) if url.startswith("sqlite") else make_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
