from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./faultlab.db"
    db_host: str | None = None
    db_name: str = "faultlab"
    db_user: str = "faultlab"
    db_password: str | None = None
    redis_url: str = "redis://localhost:6379/0"
    internal_token: str = "local-development-only"
    demo_payment_url: str = "http://localhost:8003"
    demo_gateway_url: str = "http://localhost:8001"
    db_timeout_seconds: int = 5
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def managed_database(self):
        if self.db_host:
            if not self.db_password:
                raise ValueError("DB_PASSWORD is required when DB_HOST is set")
            self.database_url = (f"postgresql+psycopg://{quote_plus(self.db_user)}:"
                                 f"{quote_plus(self.db_password)}@{self.db_host}:5432/"
                                 f"{quote_plus(self.db_name)}?sslmode=require")
        return self


settings = Settings()
