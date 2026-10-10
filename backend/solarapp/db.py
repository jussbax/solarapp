from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from fastapi import Request
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
    ensure_columns(_engine, "passkeys", models.Passkey)
    ensure_columns(_engine, "assessments", models.Assessment)   # proposal_issued_at (round 4)
    ensure_columns(_engine, "datasheet_specs", models.DatasheetSpec)   # held_applied_at (round 12 review)
    return _engine


def ensure_columns(engine: Engine, table: str, model) -> list[str]:
    """SQLite keeps a table as it was created; columns added to the model since are added here at startup
    so an existing database keeps working. Returns the columns added."""
    from sqlalchemy import text

    with engine.connect() as conn:
        present = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})")).all()}
        if not present:
            return []
        added: list[str] = []
        for col in model.__table__.columns:
            if col.name in present:
                continue
            kind = col.type.__class__.__name__.upper()
            sql_type = "INTEGER" if kind in ("INTEGER", "BOOLEAN") else "REAL" if kind == "FLOAT" else "VARCHAR"
            default = " DEFAULT ''" if sql_type == "VARCHAR" and not col.nullable else ""
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col.name} {sql_type}{default}"))
            added.append(col.name)
        conn.commit()
    return added


def get_engine() -> Engine:
    assert _engine is not None, "database not initialised"
    return _engine


def get_session(request: Request) -> Iterator[Session]:
    """A session on the app's own engine (bound at start-up), so two apps in one process never share one."""
    engine = getattr(request.app.state, "engine", None) or get_engine()
    with Session(engine) as session:
        yield session
