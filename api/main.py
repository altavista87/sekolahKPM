"""EduSync API main application for Railway deployment."""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from api.routes import api_router
from config.settings import get_settings
from database.connection import init_db, check_db_connection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("🚀 EduSync API starting up on Railway...")
    
    # Validate configuration
    settings = get_settings()
    if settings.secret_key == "change-me-in-production":
        logger.warning("⚠️ WARNING: Using default secret key! Change in production.")
    
    # Initialize database
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        # Don't raise - let the app start anyway
    
    # Check database connection
    db_healthy = await check_db_connection()
    if db_healthy:
        logger.info("✅ Database connection: OK")
    else:
        logger.error("❌ Database connection: FAILED")
    
    yield
    
    # Shutdown
    logger.info("🛑 EduSync API shutting down...")


# Create FastAPI app with lifespan
app = FastAPI(
    title="EduSync API",
    version="1.0.0",
    description="Secure API for EduSync homework management platform",
    docs_url="/api/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/api/redoc" if os.getenv("ENVIRONMENT") != "production" else None,
    openapi_url="/api/openapi.json" if os.getenv("ENVIRONMENT") != "production" else None,
    lifespan=lifespan
)

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS: Allow Netlify frontend and local development
ALLOWED_ORIGINS = [
    # Netlify deployed site
    "https://sekolahkpm.netlify.app",
    "https://main--sekolahkpm.netlify.app",
    # Railway domain (for API testing)
    "https://*.up.railway.app",
    # Telegram
    "https://t.me",
    # Local development
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:8000",
]

# Add custom domain from environment if set
if os.getenv("FRONTEND_URL"):
    ALLOWED_ORIGINS.append(os.getenv("FRONTEND_URL"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-Telegram-Bot-Api-Secret-Token"],
    expose_headers=["X-Rate-Limit"],
    max_age=600,
)

# Trusted Host Middleware
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "*.railway.app",
    "*.up.railway.app",
]

# Add Railway app domain if available
if os.getenv("RAILWAY_PUBLIC_DOMAIN"):
    ALLOWED_HOSTS.append(os.getenv("RAILWAY_PUBLIC_DOMAIN"))

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS
)

# Include API routes with versioning
app.include_router(api_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to prevent leaking sensitive info."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Return generic error in production
    if os.getenv("ENVIRONMENT") == "production":
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    
    # Return detailed error in development
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )


# Health check endpoints (outside versioned router for load balancers)
@app.get("/health")
@limiter.limit("60/minute")
async def health_check(request: Request):
    """Health check endpoint for load balancers."""
    db_healthy = await check_db_connection()
    
    status = "healthy" if db_healthy else "degraded"
    status_code = 200 if db_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "version": "1.0.0",
            "database": "connected" if db_healthy else "disconnected",
            "environment": os.getenv("ENVIRONMENT", "development")
        }
    )


@app.get("/ready")
@limiter.limit("60/minute")
async def readiness_check(request: Request):
    """Readiness check for Kubernetes/Railway."""
    db_healthy = await check_db_connection()
    
    return JSONResponse(
        status_code=200 if db_healthy else 503,
        content={
            "ready": db_healthy,
            "database": "connected" if db_healthy else "disconnected"
        }
    )


@app.get("/metrics")
@limiter.limit("60/minute")
async def metrics(request: Request):
    """Prometheus metrics endpoint."""
    return {"requests_total": 0, "version": "1.0.0"}


# Telegram webhook endpoint (direct - not in router for easier config)
@app.post("/webhook/telegram")
async def telegram_webhook(update: dict):
    """Telegram webhook endpoint."""
    logger.info(f"Received Telegram update: {update.get('update_id')}")
    
    # TODO: Process the update through the bot
    # For now, just acknowledge receipt
    return {"ok": True}
