"""EduSync API main application with security hardening."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from api.routes import api_router
from config.settings import get_settings

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title="EduSync API",
    version="1.0.0",
    description="Secure API for EduSync homework management platform",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security: Restricted CORS - NOT allowing all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://edusync.app",
        "https://www.edusync.app",
        "https://api.edusync.app",
        "https://t.me",
        # Add localhost for development (remove in production)
        "http://localhost:3000",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-Rate-Limit"],
    max_age=600,  # 10 minutes
)

# Security: Trusted Host Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "edusync.app",
        "www.edusync.app",
        "api.edusync.app",
        "*.edusync.app",
        "localhost",  # Remove in production
    ]
)

# Include API routes with versioning
app.include_router(api_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to prevent leaking sensitive info."""
    settings = get_settings()
    
    # Log the full exception for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Return generic error in production
    if settings.environment == "production":
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
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/ready")
@limiter.limit("60/minute")
async def readiness_check(request: Request):
    """Readiness check for Kubernetes."""
    # TODO: Add database connectivity check
    return {"ready": True}


@app.get("/metrics")
@limiter.limit("60/minute")
async def metrics(request: Request):
    """Prometheus metrics endpoint."""
    # TODO: Implement actual Prometheus metrics
    return {"requests_total": 0}


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("EduSync API starting up...")
    
    # Validate configuration
    settings = get_settings()
    if settings.secret_key == "change-me-in-production":
        logger.warning("WARNING: Using default secret key! Change in production.")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("EduSync API shutting down...")
