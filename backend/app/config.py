from functools import lru_cache
from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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


@lru_cache
def get_settings() -> Settings:
    return Settings()
