"""API routes package."""

from fastapi import APIRouter

from api.routes.auth import router as auth_router
from api.routes.users import router as users_router
from api.routes.homework import router as homework_router
from api.routes.students import router as students_router
from api.routes.webhooks import router as webhooks_router

# Main API router
api_router = APIRouter(prefix="/api/v1")

# Include all routers
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(homework_router, prefix="/homework", tags=["homework"])
api_router.include_router(students_router, prefix="/students", tags=["students"])
api_router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])

__all__ = ["api_router"]
