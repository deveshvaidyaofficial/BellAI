import logging
from typing import Iterator

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)


def init_db() -> None:
    # Import models so their tables are registered on SQLModel.metadata.
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)

    # Migrate existing sqlite database tables if needed
    if settings.database_url.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                # Check if calllog table exists and whether extracted_note column is present
                cols = [row[1] for row in conn.execute(text("PRAGMA table_info(calllog);")).fetchall()]
                if cols and "extracted_note" not in cols:
                    log.info("Migrating existing calllog table: adding extracted_note column")
                    conn.execute(text("ALTER TABLE calllog ADD COLUMN extracted_note VARCHAR;"))
                    conn.commit()
        except Exception:
            log.exception("Database migration check failed")


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
