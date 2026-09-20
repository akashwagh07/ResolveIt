from functools import lru_cache
import logging
from pathlib import Path
from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("resolveit.config")
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_LOGGED_DB_PATH = False


class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_FALLBACK_MODELS: str = "gemini-3.5-flash,gemini-3.7-flash"
    GEMINI_FALLBACK_MODEL: Optional[str] = None
    LLM_CACHE_DIR: str = "./.llm_cache"
    LLM_CACHE_ENABLED: bool = True
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 3
    TIME_SCALE: float = 1.0
    OFFICER_PASSCODE: str = "officer123"
    DATABASE_URL: str = "sqlite:///./resolveit.db"
    UPLOAD_DIR: str = "./uploads"
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    DEMO_MODE: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def _sync_fallback_models(self) -> "Settings":
        if self.GEMINI_FALLBACK_MODEL and (
            not self.GEMINI_FALLBACK_MODELS
            or self.GEMINI_FALLBACK_MODELS == "gemini-3.5-flash,gemini-3.7-flash"
        ):
            self.GEMINI_FALLBACK_MODELS = self.GEMINI_FALLBACK_MODEL
        return self

    @model_validator(mode="after")
    def _resolve_sqlite_url(self) -> "Settings":
        global _LOGGED_DB_PATH
        db_url = self.DATABASE_URL
        resolved_path_to_log: Optional[str] = None

        if db_url.startswith("sqlite:///"):
            path_part = db_url[len("sqlite:///"):]
            if path_part and path_part != ":memory:":
                p = Path(path_part)
                if not p.is_absolute():
                    resolved_file = (PROJECT_ROOT / p).resolve()
                    self.DATABASE_URL = f"sqlite:///{resolved_file.as_posix()}"
                    resolved_path_to_log = str(resolved_file)
                else:
                    resolved_path_to_log = str(p.resolve())
            elif path_part == ":memory:":
                resolved_path_to_log = ":memory:"
        elif db_url.startswith("sqlite://"):
            resolved_path_to_log = ":memory:"

        if resolved_path_to_log and not _LOGGED_DB_PATH:
            logger.info("%s", resolved_path_to_log)
            _LOGGED_DB_PATH = True

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

