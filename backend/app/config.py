from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./bellai.db"

    bolna_mock: bool = True
    bolna_api_key: str = ""
    bolna_agent_id: str = "c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c"
    bolna_base_url: str = "https://api.bolna.ai"
    bolna_from_phone_number: str = ""
    bolna_webhook_secret: str = ""
    bolna_timeout_seconds: int = 15

    scheduler_enabled: bool = True
    scheduler_interval_seconds: int = 30

    frontend_origin: str = "http://localhost:3000"

    google_client_id: str = ""
    auth_secret: str = "dev-only-change-me"
    otp_mock: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
