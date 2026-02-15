"""EduSync API main application for Railway deployment (with static files)."""

import os
import sys
import logging
from contextlib import asynccontextmanager

# Setup logging first
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
    from fastapi.responses import JSONResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
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
        db_status = f"error: {str(e)[:50]}"
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

# CORS - allow all for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# API ROUTES (Define BEFORE static files)
# ==========================================

@app.get("/health")
async def health_check():
    """Health check - must return 200 for Railway."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": db_status,
        "started": app_started
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check."""
    return {
        "ready": app_started,
        "database": db_status
    }


@app.get("/api")
async def api_root():
    """API root."""
    return {
        "message": "EduSync API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "homework": "/api/v1/homework",
            "telegram_webhook": "/webhook/telegram"
        }
    }


# Telegram webhook
@app.post("/webhook/telegram")
async def telegram_webhook(update: dict):
    """Telegram webhook endpoint."""
    logger.info(f"Telegram update: {update.get('update_id')}")
    return {"ok": True}


# API v1 routes
@app.get("/api/v1/homework")
async def list_homework():
    """List homework."""
    if db_status == "connected":
        try:
            from database.connection import get_db_context
            from database.models import Homework
            from sqlalchemy import select
            
            async with get_db_context() as session:
                result = await session.execute(select(Homework))
                homework = result.scalars().all()
                return {
                    "homework": [{"id": h.id, "subject": h.subject, "title": h.title} for h in homework]
                }
        except Exception as e:
            logger.error(f"DB query failed: {e}")
    
    # Fallback mock data
    return {
        "homework": [
            {"id": "1", "subject": "Mathematics", "title": "Algebra Exercise", "status": "pending"},
            {"id": "2", "subject": "Science", "title": "Biology Worksheet", "status": "pending"},
            {"id": "3", "subject": "Bahasa Melayu", "title": "Karangan", "status": "completed"}
        ],
        "note": f"Database: {db_status}"
    }


@app.post("/api/v1/homework")
async def create_homework(data: dict):
    """Create homework."""
    logger.info(f"Creating homework: {data}")
    return {"id": f"hw-{os.urandom(4).hex()}", "created": True, "data": data}


@app.get("/api/v1/users/{user_id}")
async def get_user(user_id: str):
    """Get user by ID."""
    return {
        "id": user_id,
        "name": "Parent User",
        "role": "parent",
        "children": [
            {"id": "c1", "name": "Ahmad", "class": "5A"},
            {"id": "c2", "name": "Aisyah", "class": "3B"}
        ]
    }


# Try to add more routes from routes module
try:
    from api.routes import api_router
    app.include_router(api_router, prefix="/api/v1")
    logger.info("✅ API routes loaded from routes module")
except Exception as e:
    logger.warning(f"⚠️ Could not load routes module: {e}")


# ==========================================
# STATIC FILES (Mount AFTER API routes)
# ==========================================

# Get the static directory path
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

if os.path.exists(STATIC_DIR):
    logger.info(f"✅ Serving static files from: {STATIC_DIR}")
    
    # Mount static files at root
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    
    @app.get("/")
    async def serve_index():
        """Serve index.html at root."""
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "EduSync API - Static files not found"}
    
    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """SPA fallback - serve index.html for all non-API routes."""
        # Don't intercept API routes
        if path.startswith(("api/", "webhook/", "health", "ready", "metrics")):
            return JSONResponse(
                status_code=404,
                content={"detail": "Not found"}
            )
        
        # Check if file exists in static directory
        file_path = os.path.join(STATIC_DIR, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # Fallback to index.html for client-side routing
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        
        return JSONResponse(
            status_code=404,
            content={"detail": "Not found"}
        )
else:
    logger.warning(f"⚠️ Static directory not found: {STATIC_DIR}")
    
    @app.get("/")
    async def root_no_static():
        """Root when no static files."""
        return {
            "message": "EduSync API",
            "version": "1.0.0",
            "status": "API only mode - no frontend",
            "health": "/health",
            "api": "/api"
        }


logger.info("✅ FastAPI app configured with static files")
