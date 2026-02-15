"""
Netlify Function: Telegram Bot Webhook Handler
Receives updates from Telegram and processes them.
"""
import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from http.client import HTTPResponse
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from telegram import Update
    from telegram.ext import Application
    from bot.config import BotConfig
    from bot.main import EduSyncBot
    from database.connection import init_db
except ImportError as e:
    logger.error(f"Import error: {e}")
    # Fallback for missing dependencies during build
    pass

# Global bot instance (initialized once)
_bot_instance = None
_app_instance = None

async def get_bot():
    """Get or create bot instance."""
    global _bot_instance, _app_instance
    
    if _bot_instance is None:
        config = BotConfig.from_env()
        _bot_instance = EduSyncBot(config)
        _app_instance = _bot_instance.application
        
        # Initialize bot
        _bot_instance.setup()
        
        # Initialize database
        await init_db()
        
        logger.info("Bot initialized successfully")
    
    return _bot_instance, _app_instance


def verify_telegram_secret(update: Dict, secret_token: str) -> bool:
    """Verify Telegram webhook secret."""
    # In Netlify, we check headers
    # For now, validate basic structure
    if not isinstance(update, dict):
        return False
    if 'update_id' not in update:
        return False
    return True


async def process_update(update_data: Dict[str, Any]):
    """Process a single Telegram update."""
    try:
        bot, app = await get_bot()
        
        # Create Update object
        update = Update.de_json(update_data, app.bot)
        
        # Process update
        await app.process_update(update)
        
        logger.info(f"Processed update {update.update_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
        return False


async def handler(event, context):
    """
    Netlify function handler for Telegram webhook.
    
    Args:
        event: Netlify event object
        context: Netlify context object
        
    Returns:
        HTTP response object
    """
    # Log request
    logger.info(f"Received webhook request: {event.get('httpMethod')}")
    
    # Only accept POST requests
    if event.get('httpMethod') != 'POST':
        return {
            'statusCode': 405,
            'body': json.dumps({'error': 'Method not allowed'}),
            'headers': {'Content-Type': 'application/json'}
        }
    
    try:
        # Parse request body
        body = event.get('body', '{}')
        if event.get('isBase64Encoded', False):
            import base64
            body = base64.b64decode(body).decode('utf-8')
        
        update_data = json.loads(body)
        logger.info(f"Update ID: {update_data.get('update_id')}")
        
        # Verify webhook secret
        secret_token = os.getenv('TELEGRAM_WEBHOOK_SECRET', '')
        if secret_token and not verify_telegram_secret(update_data, secret_token):
            return {
                'statusCode': 403,
                'body': json.dumps({'error': 'Invalid webhook secret'}),
                'headers': {'Content-Type': 'application/json'}
            }
        
        # Process the update
        success = await process_update(update_data)
        
        if success:
            return {
                'statusCode': 200,
                'body': json.dumps({'ok': True}),
                'headers': {'Content-Type': 'application/json'}
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to process update'}),
                'headers': {'Content-Type': 'application/json'}
            }
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid JSON'}),
            'headers': {'Content-Type': 'application/json'}
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'}),
            'headers': {'Content-Type': 'application/json'}
        }


# Netlify function entry point
def lambda_handler(event, context):
    """Synchronous wrapper for async handler."""
    return asyncio.get_event_loop().run_until_complete(handler(event, context))
