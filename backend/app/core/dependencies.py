from typing import Generator, List, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Validate Bearer token and retrieve the corresponding active user."""
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise UnauthorizedError("Invalid token payload: missing user ID.")
    except Exception as e:
        raise UnauthorizedError(f"Could not validate credentials: {str(e)}")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise UnauthorizedError("User associated with this token does not exist.")
    if not user.is_active:
        raise ForbiddenError("User account has been deactivated.")
    return user


def require_roles(allowed_roles: List[str]) -> Callable[[User], User]:
    """Dependency factory that validates whether the authenticated user has one of the allowed roles."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenError(
                f"Access denied. Requires one of roles: {', '.join(allowed_roles)}. Your role is '{current_user.role}'."
            )
        return current_user
    return role_checker


# Role convenience dependencies
get_current_agent_or_admin = require_roles([UserRole.AGENT, UserRole.ADMIN])
get_current_admin = require_roles([UserRole.ADMIN])
