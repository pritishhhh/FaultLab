from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./faultlab.db"
    redis_url: str = "redis://localhost:6379/0"
    internal_token: str = "local-development-only"
    demo_payment_url: str = "http://localhost:8003"
    demo_gateway_url: str = "http://localhost:8001"
    db_timeout_seconds: int = 5
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
