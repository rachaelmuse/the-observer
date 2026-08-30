from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), extra="ignore")

    observer_host: str = "127.0.0.1"
    observer_port: int = 8730
    observer_database_url: str = "sqlite:///./data/observer.db"
    observer_archive_dir: str = "./data/archive"
    observer_user_agent: str = "TheObserver/0.1 (independent research)"
    observer_rate_limit_seconds: float = 2.0
    observer_max_fetch_bytes: int = 5_242_880
    observer_search_adapter: str = "duckduckgo"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = ""
    brave_search_api_key: str = ""
    courtlistener_token: str = ""


def load_settings() -> Settings:
    return Settings()


def resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = ROOT / path
    return path
