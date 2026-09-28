"""Adaptador SQLite con motor SQLAlchemy 2 y migraciones Alembic (T03)."""

from pathlib import Path

from app.db.repository import SqlAlchemyClaimRepository
from app.db.session import get_engine, run_migrations


class SqliteClaimRepository(SqlAlchemyClaimRepository):
    """Adaptador de compatibilidad para SqlAlchemyClaimRepository usando SQLite."""

    def __init__(self, db_path: Path, storage_dir: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        storage_dir = Path(storage_dir)
        storage_dir.mkdir(parents=True, exist_ok=True)

        engine = get_engine(f"sqlite:///{self.db_path}")
        run_migrations(engine)
        super().__init__(engine=engine, storage_dir=storage_dir)
