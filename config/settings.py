"""Application settings."""

from functools import lru_cache
from typing import Optional, List

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "EduSync"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    secret_key: str = Field(default="change-me-in-production")
    
    # Database
    database_url: str = "postgresql+asyncpg://localhost/edusync"
    database_pool_size: int = 20
    database_max_overflow: int = 10
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_url: Optional[str] = None
    telegram_webhook_secret: Optional[str] = None
    
    # WhatsApp
    whatsapp_api_key: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_business_account_id: str = ""
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 2000
    
    # OCR
    tesseract_cmd: str = "/usr/bin/tesseract"
    ocr_language: str = "eng+chi_sim+chi_tra+msa"
    
    # Security
    encryption_key: Optional[str] = None
    pdpa_consent_required: bool = True
    data_retention_days: int = 365
    
    # Webhook Secrets
    telegram_webhook_secret: Optional[str] = None
    whatsapp_webhook_secret: Optional[str] = None
    webhook_verify_token: Optional[str] = None
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = 100
    webhook_rate_limit_per_minute: int = 20
    
    # Feature Flags
    enable_whatsapp: bool = True
    enable_telegram: bool = True
    enable_batch_processing: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
