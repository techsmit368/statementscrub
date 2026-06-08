from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    anthropic_api_key: str
    secret_key: str = "dev-secret-change-in-production"
    database_url: str = "sqlite:///./bankanalyzer.db"
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    app_url: str = "https://statementscrub.com"
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 20
    telegram_bot_token: str = ""
    smtp_user: str = ""
    smtp_password: str = ""
    notify_email: str = "patelsmit368@gmail.com"

    class Config:
        env_file = ".env"


settings = Settings()
