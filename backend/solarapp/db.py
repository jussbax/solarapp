from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from . import models  # noqa: F401  (register tables)

_engine: Engine | None = None


def init_engine(db_path: Path) -> Engine:
    global _engine
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(_engine)
    return _engine


def get_engine() -> Engine:
    assert _engine is not None, "database not initialised"
    return _engine


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
