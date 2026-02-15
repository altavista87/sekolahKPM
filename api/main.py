"""EduSync API main application for Railway deployment."""

import os
import sys
import logging
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


try:
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, HTMLResponse
    logger.info("✅ FastAPI imported")
except ImportError as e:
    logger.error(f"❌ Failed to import FastAPI: {e}")
    raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    global db_status, app_started
    
    logger.info("🚀 EduSync API starting up...")
    
    # Try to initialize database
    try:
        from database.connection import init_db, check_db_connection
        await init_db()
        db_healthy = await check_db_connection()
        db_status = "connected" if db_healthy else "disconnected"
        logger.info(f"✅ Database: {db_status}")
    except Exception as e:
        db_status = f"error: {str(e)[:80]}"
        logger.error(f"❌ Database init failed: {e}")
    
    app_started = True
    logger.info("✅ Application startup complete")
    
    yield
    
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
        # Railway deployment paths
        "/app/static",
        "/workspace/static", 
        "/static",
        # Relative paths
        os.path.join(os.getcwd(), "static"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static"),
        # Parent of current file
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
    
    # Try to use Gemini
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        
        # List available models
        models = genai.list_models()
        model_names = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        
        # Try a simple test
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content("Say 'EduSync API is working!'")
        
        return {
            "status": "success",
            "configured": True,
            "available_models": model_names[:5],  # First 5 models
            "test_response": response.text.strip() if response.text else "No response",
            "message": "Gemini API is working!"
        }
    except Exception as e:
        return {
            "status": "error",
            "configured": True,
            "message": f"Gemini API error: {str(e)[:100]}"
        }


@app.post("/webhook/telegram")
async def telegram_webhook(update: dict):
    """Telegram webhook."""
    logger.info(f"Telegram update: {update.get('update_id')}")
    return {"ok": True}


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


@app.post("/api/v1/homework")
async def create_homework(data: dict):
    """Create homework."""
    return {"id": f"hw-{os.urandom(4).hex()}", "created": True}


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
    
    # Fallback HTML
    return """<!DOCTYPE html>
    <html>
    <head><title>EduSync</title></head>
    <body>
        <h1>EduSync API</h1>
        <p>Frontend not found. API is running.</p>
        <p>Database: """ + db_status + """</p>
        <ul>
            <li><a href="/health">Health Check</a></li>
            <li><a href="/api">API Info</a></li>
            <li><a href="/api/v1/homework">Homework API</a></li>
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


@app.get("/js/{filename}")
async def serve_js(filename: str):
    """Serve JS files."""
    if STATIC_DIR:
        js_path = os.path.join(STATIC_DIR, "js", filename)
        if os.path.exists(js_path):
            with open(js_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read(), media_type="application/javascript")
    return JSONResponse(status_code=404, content={"error": "Not found"})


logger.info("✅ FastAPI app ready")
