from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Environment variables use the SOLARAPP_ prefix."""

    data_dir: Path = Path("data")
    db_path: Optional[Path] = None  # default: <data_dir>/solarapp.db
    app_username: str = "admin"
    app_password: str = "change-me"
    secret_key: str = "change-me-to-a-long-random-string"
    company_name: str = "PL Development Inc."
    company_contact: str = "Pila, Laguna"
    static_dir: Optional[Path] = None  # built frontend (dist); served at /
    session_hours: int = 24 * 14

    model_config = SettingsConfigDict(env_prefix="SOLARAPP_", env_file=".env", extra="ignore")

    @property
    def database_path(self) -> Path:
        return self.db_path or (self.data_dir / "solarapp.db")


@lru_cache
def get_settings() -> Settings:
    return Settings()
