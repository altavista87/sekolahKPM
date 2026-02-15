"""Telegram Bot Configuration."""

import os
import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class BotConfig:
    """Bot configuration settings."""
    
    # Telegram
    bot_token: str
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    use_webhook: bool = False
    
    # Database
    database_url: str = "postgresql+asyncpg://localhost/edusync"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 2000
    openai_temperature: float = 0.7
    
    # Gemini
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash"
    
    # Together AI
    together_api_key: Optional[str] = None
    together_model: str = "meta-llama/Llama-4-Scout-17B-16E-Instruct"
    together_vision_model: str = "nim/meta/llama-3.2-90b-vision-instruct"
    
    # DeepSeek
    deepseek_api_key: Optional[str] = None
    deepseek_model: str = "deepseek-chat"
    
    # OCR
    tesseract_cmd: str = "/usr/bin/tesseract"
    ocr_language: str = "eng+chi_sim+chi_tra+msa"
    easyocr_gpu: bool = False
    
    # Advanced Vision OCR
    ocr_preferred_mode: str = "auto"  # auto, ensemble, vision, traditional
    ocr_enable_ensemble: bool = True
    ocr_ensemble_voting: bool = True
    ocr_fallback_enabled: bool = True
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 10
    
    # File Uploads
    max_file_size_mb: int = 20
    allowed_extensions: tuple = ("jpg", "jpeg", "png", "pdf")
    upload_path: str = "./uploads"
    
    # Features
    enable_ai_enhancement: bool = True
    enable_batch_processing: bool = True
    
    @classmethod
    def from_env(cls) -> "BotConfig":
        """Load configuration from environment variables with validation."""
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        
        # Validate token format (9-10 digits : 35 alphanumeric chars)
        if token and not re.match(r'^\d{9,10}:[A-Za-z0-9_-]{35}$', token):
            logger.warning("TELEGRAM_BOT_TOKEN format appears invalid")
        
        # Validate webhook secret if webhook is enabled
        use_webhook = os.getenv("USE_WEBHOOK", "false").lower() == "true"
        webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
        if use_webhook and not webhook_secret:
            logger.warning("Webhook enabled but TELEGRAM_WEBHOOK_SECRET not set")
        
        return cls(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            webhook_url=os.getenv("TELEGRAM_WEBHOOK_URL"),
            webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET"),
            use_webhook=os.getenv("USE_WEBHOOK", "false").lower() == "true",
            database_url=os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost/edusync"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4"),
            openai_max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "2000")),
            openai_temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            together_api_key=os.getenv("TOGETHER_API_KEY"),
            together_model=os.getenv("TOGETHER_MODEL", "meta-llama/Llama-4-Scout-17B-16E-Instruct"),
            together_vision_model=os.getenv("TOGETHER_VISION_MODEL", "nim/meta/llama-3.2-90b-vision-instruct"),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            tesseract_cmd=os.getenv("TESSERACT_CMD", "/usr/bin/tesseract"),
            ocr_language=os.getenv("OCR_LANGUAGE", "eng+chi_sim+chi_tra+msa"),
            easyocr_gpu=os.getenv("EASYOCR_GPU", "false").lower() == "true",
            ocr_preferred_mode=os.getenv("OCR_PREFERRED_MODE", "auto"),
            ocr_enable_ensemble=os.getenv("OCR_ENABLE_ENSEMBLE", "true").lower() == "true",
            ocr_ensemble_voting=os.getenv("OCR_ENSEMBLE_VOTING", "true").lower() == "true",
            ocr_fallback_enabled=os.getenv("OCR_FALLBACK_ENABLED", "true").lower() == "true",
            rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
            rate_limit_burst=int(os.getenv("RATE_LIMIT_BURST", "10")),
            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "20")),
            allowed_extensions=tuple(os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png,pdf").split(",")),
            upload_path=os.getenv("UPLOAD_PATH", "./uploads"),
            enable_ai_enhancement=os.getenv("ENABLE_AI_ENHANCEMENT", "true").lower() == "true",
            enable_batch_processing=os.getenv("ENABLE_BATCH_PROCESSING", "true").lower() == "true",
        )
