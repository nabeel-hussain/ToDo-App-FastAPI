from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    reminder_poll_seconds: float = 5.0
    reminder_resync_seconds: float = 60.0


settings = Settings()
