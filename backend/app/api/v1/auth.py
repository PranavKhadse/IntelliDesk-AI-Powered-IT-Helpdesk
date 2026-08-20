from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, RefreshTokenRequest
from app.schemas.user import UserResponse
from app.services.auth_service import register_user, authenticate_user, refresh_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account."""
    user = register_user(db, req)
    return user


@router.post("/login", response_model=TokenResponse)
def login_json(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email and password to receive JWT tokens."""
    _, tokens = authenticate_user(db, req)
    return tokens


@router.post("/token", response_model=TokenResponse, include_in_schema=False)
def login_oauth2(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 compatible token login for Swagger UI."""
    req = LoginRequest(email=form_data.username, password=form_data.password)
    _, tokens = authenticate_user(db, req)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh(req: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access token."""
    tokens = refresh_access_token(db, req.refresh_token)
    return tokens


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve the profile of the currently authenticated user."""
    return current_user
