from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from . import models  # noqa: F401  (register tables)

_engine: Engine | None = None


def init_engine(db_path: Path) -> Engine:
    global _engine
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # busy timeout: the public estimate's writes and the owner's saves share one file; wait rather than fail
    _engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False, "timeout": 30})

    @event.listens_for(_engine, "connect")
    def _pragmas(conn, _record):  # noqa: ANN001
        cur = conn.cursor()
        for pragma in ("PRAGMA journal_mode=WAL", "PRAGMA synchronous=NORMAL", "PRAGMA busy_timeout=30000", "PRAGMA foreign_keys=ON"):
            cur.execute(pragma)
        cur.close()

    SQLModel.metadata.create_all(_engine)
    return _engine


def get_engine() -> Engine:
    assert _engine is not None, "database not initialised"
    return _engine


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
