"""EduSync API main application for Railway deployment with Telegram Bot."""

import os
import sys
import logging
import asyncio
from contextlib import asynccontextmanager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state
db_status = "not_initialized"
app_started = False
bot_application = None  # Telegram bot application


try:
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, HTMLResponse
    logger.info("✅ FastAPI imported")
except ImportError as e:
    logger.error(f"❌ Failed to import FastAPI: {e}")
    raise


async def init_telegram_bot():
    """Initialize Telegram bot application."""
    global bot_application
    
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.warning("⚠️ TELEGRAM_BOT_TOKEN not set - bot disabled")
        return None
    
    try:
        from telegram.ext import Application
        from bot.config import BotConfig
        from bot.main import EduSyncBot
        
        config = BotConfig.from_env()
        bot = EduSyncBot(config)
        bot.setup()
        
        logger.info("✅ Telegram bot initialized")
        return bot.application
    except Exception as e:
        logger.error(f"❌ Failed to initialize bot: {e}")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    global db_status, app_started, bot_application
    
    logger.info("🚀 EduSync API starting up...")
    
    # Try to initialize database (sync version for psycopg2)
    try:
        from database.connection import init_db, check_db_connection
        init_db()
        db_healthy = check_db_connection()
        db_status = "connected" if db_healthy else "disconnected"
        logger.info(f"✅ Database: {db_status}")
    except Exception as e:
        db_status = f"error: {str(e)[:80]}"
        logger.error(f"❌ Database init failed: {e}")
    
    # Initialize Telegram bot
    bot_application = await init_telegram_bot()
    
    app_started = True
    logger.info("✅ Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("🛑 Application shutting down...")


# Create FastAPI app
app = FastAPI(
    title="EduSync",
    version="1.0.0",
    description="EduSync - AI Homework Management Platform",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# FIND STATIC DIRECTORY
# ==========================================

def find_static_dir():
    """Find static directory in various locations."""
    possible_paths = [
        "/app/static",
        "/workspace/static", 
        "/static",
        os.path.join(os.getcwd(), "static"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static"),
    ]
    
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path) and os.path.isdir(abs_path):
            logger.info(f"✅ Found static directory: {abs_path}")
            return abs_path
    
    logger.warning("⚠️ Static directory not found")
    return None


STATIC_DIR = find_static_dir()


# ==========================================
# API ROUTES
# ==========================================

@app.get("/health")
async def health_check():
    """Health check."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": db_status,
        "bot": "initialized" if bot_application else "disabled",
        "started": app_started,
        "static_dir": STATIC_DIR
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check."""
    return {"ready": app_started, "database": db_status}


@app.get("/api")
async def api_root():
    """API root."""
    return {
        "message": "EduSync API",
        "version": "1.0.0",
        "endpoints": ["/health", "/api/v1/homework", "/webhook/telegram", "/api/test/ai"]
    }


@app.get("/api/test/ai")
async def test_ai():
    """Test if Gemini API key is working."""
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    
    if not gemini_key:
        return {
            "status": "error",
            "message": "GEMINI_API_KEY not set",
            "configured": False
        }
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        
        models = genai.list_models()
        model_names = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content("Say 'EduSync API is working!'")
        
        return {
            "status": "success",
            "configured": True,
            "available_models": model_names[:5],
            "test_response": response.text.strip() if response.text else "No response",
            "message": "Gemini API is working!"
        }
    except Exception as e:
        return {
            "status": "error",
            "configured": True,
            "message": f"Gemini API error: {str(e)[:100]}"
        }


# ==========================================
# TELEGRAM BOT WEBHOOK
# ==========================================

@app.post("/webhook/telegram")
async def telegram_webhook(update: dict):
    """Telegram webhook - processes bot updates."""
    global bot_application
    
    update_id = update.get('update_id', 'unknown')
    logger.info(f"📨 Telegram update received: {update_id}")
    
    if not bot_application:
        logger.error("❌ Bot application not initialized")
        return {"ok": False, "error": "Bot not initialized"}
    
    try:
        from telegram import Update
        
        # Create Update object from JSON
        telegram_update = Update.de_json(update, bot_application.bot)
        
        # Process the update
        await bot_application.process_update(telegram_update)
        
        logger.info(f"✅ Update {update_id} processed")
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"❌ Error processing update {update_id}: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/webhook/telegram")
async def telegram_webhook_info():
    """Get webhook info (for debugging)."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return {"error": "TELEGRAM_BOT_TOKEN not set"}
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://api.telegram.org/bot{token}/getWebhookInfo")
            return response.json()
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/v1/homework")
async def create_homework(data: dict):
    """Create homework."""
    return {"id": f"hw-{os.urandom(4).hex()}", "created": True, "data": data}


@app.get("/api/v1/homework")
async def list_homework():
    """List homework."""
    return {
        "homework": [
            {"id": "1", "subject": "Mathematics", "title": "Algebra Exercise", "status": "pending"},
            {"id": "2", "subject": "Science", "title": "Biology Worksheet", "status": "pending"},
        ],
        "database": db_status
    }


# ==========================================
# STATIC FILES & FRONTEND
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve main index.html."""
    if STATIC_DIR:
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error reading index.html: {e}")
    
    return f"""<!DOCTYPE html>
    <html>
    <head><title>EduSync</title></head>
    <body>
        <h1>EduSync API</h1>
        <p>Bot: {"Running" if bot_application else "Not configured"}</p>
        <p>Database: {db_status}</p>
        <ul>
            <li><a href="/health">Health Check</a></li>
            <li><a href="/api">API Info</a></li>
            <li><a href="/webhook/telegram">Webhook Info</a></li>
        </ul>
    </body>
    </html>"""


@app.get("/test-ui", response_class=HTMLResponse)
async def serve_test_ui():
    """Serve test UI page."""
    if STATIC_DIR:
        test_ui_path = os.path.join(STATIC_DIR, "test-ui.html")
        if os.path.exists(test_ui_path):
            try:
                with open(test_ui_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error reading test-ui.html: {e}")
    return "<h1>Test UI not found</h1><a href='/'>Back to home</a>"


logger.info("✅ FastAPI app ready")
