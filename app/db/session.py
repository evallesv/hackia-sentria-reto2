"""Gestión de sesiones, conexiones y migraciones automáticas con SQLAlchemy 2 (T03)."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def get_engine(database_url: str) -> Engine:
    """Crea y configura el motor SQLAlchemy con soporte para WAL y FK en SQLite."""
    if database_url.startswith("sqlite"):
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON;")
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.close()

        return engine

    return create_engine(database_url)


def run_migrations(engine: Engine) -> None:
    """Ejecuta migraciones pendientes de Alembic contra el motor configurado."""
    project_root = Path(__file__).resolve().parent.parent.parent
    alembic_ini_path = project_root / "alembic.ini"
    migrations_dir = project_root / "migrations"

    if alembic_ini_path.exists() and migrations_dir.exists():
        alembic_cfg = Config(str(alembic_ini_path))
        alembic_cfg.set_main_option("script_location", str(migrations_dir))
        alembic_cfg.attributes["skip_logging_config"] = True

        with engine.connect() as connection:
            alembic_cfg.attributes["connection"] = connection
            command.upgrade(alembic_cfg, "head")
    else:
        from app.db.schema import Base

        Base.metadata.create_all(bind=engine)


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Crea una fábrica de sesiones configurada."""
    return sessionmaker(bind=engine, expire_on_commit=False)
