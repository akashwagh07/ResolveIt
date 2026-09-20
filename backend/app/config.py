from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = ""
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
