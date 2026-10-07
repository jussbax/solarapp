from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Assessment(SQLModel, table=True):
    __tablename__ = "assessments"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    customer_name: str = ""
    address: str = ""
    doc: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    results: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    results_stale: bool = False


class ApplianceCatalog(SQLModel, table=True):
    """Every appliance ever entered in an audit, for reuse. Keyed by name, brand and model."""

    __tablename__ = "appliance_catalog"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    brand: str = ""
    model: str = ""
    category: str = "other"
    input_power_w: float = 0.0
    use_count: int = 0
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class AppSetting(SQLModel, table=True):
    __tablename__ = "app_settings"

    key: str = Field(primary_key=True)
    value: str = ""
