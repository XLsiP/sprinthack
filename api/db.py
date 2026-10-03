import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATA_DIR = Path(__file__).resolve().parent / "data"
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///%s" % (DATA_DIR / "app.db"))

if DATABASE_URL.startswith("sqlite"):
    DATA_DIR.mkdir(exist_ok=True)
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _enforce_foreign_keys(dbapi_connection, _record) -> None:
        # SQLite ignores foreign keys unless asked; Postgres always enforces them.
        dbapi_connection.execute("PRAGMA foreign_keys=ON")
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
