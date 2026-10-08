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
    # Website origins allowed to call the public estimate API (comma separated), e.g. https://pldevinc.com,https://www.pldevinc.com
    public_origins: str = ""
    # Public address of this server, used in links the estimate page and the card print (e.g. https://solar.pldevinc.com)
    public_url: str = ""
    # Optional email notice for each website lead; off unless smtp_host and notify_email are set
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    notify_email: str = ""

    model_config = SettingsConfigDict(env_prefix="SOLARAPP_", env_file=".env", extra="ignore")

    @property
    def database_path(self) -> Path:
        return self.db_path or (self.data_dir / "solarapp.db")

    @property
    def origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.public_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
