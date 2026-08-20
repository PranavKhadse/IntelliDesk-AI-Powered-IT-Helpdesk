from typing import Tuple
from sqlalchemy.orm import Session
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from app.core.config import settings
from app.core.exceptions import UnauthorizedError, ConflictError, NotFoundError
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse


def register_user(db: Session, req: RegisterRequest) -> User:
    """Register a new user after verifying email uniqueness."""
    existing_user = db.query(User).filter(User.email == req.email.lower()).first()
    if existing_user:
        raise ConflictError(f"A user with email '{req.email}' already exists.")

    # Validate role assignment
    role = req.role if req.role in UserRole.ALL else UserRole.USER

    user = User(
        email=req.email.lower(),
        hashed_password=get_password_hash(req.password),
        full_name=req.full_name,
        department=req.department or "General",
        role=role,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, req: LoginRequest) -> Tuple[User, TokenResponse]:
    """Authenticate credentials and issue JWT access and refresh tokens."""
    user = db.query(User).filter(User.email == req.email.lower()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise UnauthorizedError("Incorrect email or password.")

    if not user.is_active:
        raise UnauthorizedError("Your account has been deactivated.")

    token_data = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    token_response = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    return user, token_response


def refresh_access_token(db: Session, refresh_token_str: str) -> TokenResponse:
    """Validate refresh token and issue a fresh access token."""
    try:
        payload = decode_token(refresh_token_str)
        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid token type. Refresh token required.")
        
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedError("Invalid token payload.")
    except Exception as e:
        raise UnauthorizedError(f"Invalid or expired refresh token: {str(e)}")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise UnauthorizedError("User is no longer active or does not exist.")

    token_data = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name
    }

    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
