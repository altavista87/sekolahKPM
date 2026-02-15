"""Authentication routes."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt, JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Initialize limiter for auth routes
limiter = Limiter(key_func=get_remote_address)

from api.deps import get_db, get_current_user
from api.schemas.auth import Token, UserLogin, UserCreate, TokenRefresh, LogoutRequest
from api.schemas.user import UserResponse
from config.settings import get_settings
from database.models import User

router = APIRouter()


def create_access_token(
    data: dict, 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token.
    
    Args:
        data: Payload data
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    settings = get_settings()
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create JWT refresh token with longer expiration.
    
    Args:
        data: Payload data
        
    Returns:
        Encoded JWT refresh token
    """
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(
    request: Request,
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens.
    
    Supports authentication via:
    - Telegram ID
    - WhatsApp phone number
    - Email (if password is provided)
    """
    user: Optional[User] = None
    
    # Try Telegram ID
    if login_data.telegram_id:
        query = select(User).where(User.telegram_id == login_data.telegram_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
    
    # Try WhatsApp phone
    elif login_data.whatsapp_phone:
        query = select(User).where(User.whatsapp_phone == login_data.whatsapp_phone)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
    
    # Try Email (would need password verification in production)
    elif login_data.email:
        query = select(User).where(User.email == login_data.email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    token_data = {"sub": str(user.id)}
    access_token = create_access_token(
        token_data, 
        expires_delta=timedelta(minutes=30)
    )
    refresh_token = create_refresh_token(token_data)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=1800,  # 30 minutes
        user_id=user.id
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user.
    """
    # Check if user already exists
    if user_data.telegram_id:
        query = select(User).where(User.telegram_id == user_data.telegram_id)
        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this Telegram ID already exists"
            )
    
    if user_data.whatsapp_phone:
        query = select(User).where(User.whatsapp_phone == user_data.whatsapp_phone)
        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this WhatsApp phone already exists"
            )
    
    # Create new user
    user = User(
        name=user_data.name,
        role=user_data.role,
        telegram_id=user_data.telegram_id,
        whatsapp_phone=user_data.whatsapp_phone,
        email=user_data.email,
        preferred_language=user_data.preferred_language,
        timezone=user_data.timezone,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


@router.post("/refresh", response_model=Token)
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    refresh_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            refresh_data.refresh_token, 
            settings.secret_key, 
            algorithms=["HS256"]
        )
        
        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            raise credentials_exception
            
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # Verify user still exists
    from uuid import UUID
    query = select(User).where(User.id == UUID(user_id))
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    # Create new tokens
    token_data = {"sub": str(user.id)}
    access_token = create_access_token(
        token_data, 
        expires_delta=timedelta(minutes=30)
    )
    new_refresh_token = create_refresh_token(token_data)
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=1800,
        user_id=user.id
    )


@router.post("/logout")
async def logout(
    logout_data: LogoutRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Logout user and optionally revoke refresh tokens.
    
    In production, this would add tokens to a revocation list
    or remove them from a whitelist.
    """
    # In a production system, you would:
    # 1. Add the refresh token to a Redis revocation list
    # 2. Or remove from whitelist if using that approach
    # 3. Set short TTL on the revoked entry (matching token expiry)
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    """
    return current_user
