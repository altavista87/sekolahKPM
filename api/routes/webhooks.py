"""Webhook routes with signature validation."""

import hmac

from fastapi import Request as FastAPIRequest
import hashlib
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Header
from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize limiter for webhook routes
limiter = Limiter(key_func=get_remote_address)
from pydantic import BaseModel, Field

from config.settings import get_settings

router = APIRouter()


def verify_telegram_signature(
    secret_token: Optional[str],
    bot_token: str
) -> bool:
    """
    Verify Telegram webhook signature.
    
    Telegram sends a custom secret token in the X-Telegram-Bot-Api-Secret-Token header
    that should match the webhook secret configured in the bot.
    
    Args:
        secret_token: The secret token from X-Telegram-Bot-Api-Secret-Token header
        bot_token: The expected bot token
        
    Returns:
        True if signature is valid
    """
    settings = get_settings()
    expected_secret = settings.telegram_webhook_secret
    
    if not expected_secret:
        # If no secret is configured, skip validation (not recommended for production)
        return True
    
    if not secret_token:
        return False
    
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(secret_token, expected_secret)


def verify_whatsapp_signature(
    payload: bytes,
    signature: Optional[str],
    app_secret: str
) -> bool:
    """
    Verify WhatsApp webhook signature using HMAC-SHA256.
    
    WhatsApp signs webhook payloads with the app secret using HMAC-SHA256.
    The signature is sent in the X-Hub-Signature-256 header.
    
    Args:
        payload: Raw request body bytes
        signature: The signature from X-Hub-Signature-256 header
        app_secret: The WhatsApp app secret
        
    Returns:
        True if signature is valid
    """
    if not signature:
        return False
    
    # WhatsApp signature format: sha256=<hex_encoded_hmac>
    expected_signature = f"sha256={hmac.new(
        app_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()}"
    
    # Constant-time comparison
    return hmac.compare_digest(signature, expected_signature)


class TelegramUpdate(BaseModel):
    """Telegram update model."""
    update_id: int
    message: Optional[dict] = None
    callback_query: Optional[dict] = None
    inline_query: Optional[dict] = None


class WhatsAppMessage(BaseModel):
    """WhatsApp message model."""
    object: str = Field(default="whatsapp_business_account")
    entry: list = Field(default_factory=list)


@router.post("/telegram")
@limiter.limit("60/minute")  # Higher limit for webhooks but still protected
async def telegram_webhook(
    request: FastAPIRequest,
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None, alias="X-Telegram-Bot-Api-Secret-Token")
):
    """
    Handle Telegram webhook with signature validation.
    
    Validates the X-Telegram-Bot-Api-Secret-Token header against configured secret.
    """
    settings = get_settings()
    
    # Verify signature
    if not verify_telegram_signature(
        x_telegram_bot_api_secret_token,
        settings.telegram_bot_token
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    # Parse update
    try:
        body = await request.json()
        update = TelegramUpdate(**body)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request body: {str(e)}"
        )
    
    # Process the update (implement your business logic here)
    # This would typically call your bot service to handle the message
    
    return {"ok": True, "update_id": update.update_id}


@router.post("/whatsapp")
@limiter.limit("60/minute")
async def whatsapp_webhook(
    request: FastAPIRequest,
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256")
):
    """
    Handle WhatsApp webhook with HMAC signature validation.
    
    Validates the X-Hub-Signature-256 header against the payload.
    """
    settings = get_settings()
    
    # Get raw body for signature verification
    body = await request.body()
    
    # Verify signature
    # Note: In production, you should store the app secret securely
    # and not use the API key directly
    app_secret = settings.whatsapp_api_key  # Or a separate webhook secret
    
    if not verify_whatsapp_signature(body, x_hub_signature_256, app_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    # Parse payload
    try:
        payload = json.loads(body)
        message = WhatsAppMessage(**payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request body: {str(e)}"
        )
    
    # Process the message (implement your business logic here)
    # This would typically call your WhatsApp service to handle the message
    
    return {"ok": True}


@router.get("/whatsapp")
async def whatsapp_webhook_verify(
    hub_mode: Optional[str] = None,
    hub_verify_token: Optional[str] = None,
    hub_challenge: Optional[str] = None
):
    """
    Handle WhatsApp webhook verification during setup.
    
    WhatsApp sends a GET request to verify the webhook endpoint.
    """
    settings = get_settings()
    
    if hub_mode == "subscribe" and hub_verify_token:
        # In production, verify against a configured verify token
        # For now, we accept the challenge
        return hub_challenge
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid verification request"
    )


@router.head("/telegram")
async def telegram_webhook_health():
    """
    Health check endpoint for Telegram webhook.
    """
    return {"status": "healthy"}


@router.head("/whatsapp")
async def whatsapp_webhook_health():
    """
    Health check endpoint for WhatsApp webhook.
    """
    return {"status": "healthy"}
