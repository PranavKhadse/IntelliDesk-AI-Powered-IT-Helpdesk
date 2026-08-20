from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_admin, get_current_agent_or_admin
from app.models.user import User, UserRole
from app.schemas.user import UserResponse, AgentSummary, UserUpdate
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/agents", response_model=List[AgentSummary])
def get_agents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_agent_or_admin)
):
    """List all active support agents and admins for assignment."""
    agents = db.query(User).filter(
        User.role.in_([UserRole.AGENT, UserRole.ADMIN]),
        User.is_active == True
    ).all()
    return agents


@router.get("/", response_model=List[UserResponse])
def list_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """List all registered users (Admin only)."""
    return db.query(User).order_by(User.created_at.desc()).all()


@router.patch("/{user_id}", response_model=UserResponse)
def update_user_status(
    user_id: str,
    req: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Update user role or active status (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User", user_id)

    if req.role and req.role in UserRole.ALL:
        user.role = req.role
    if req.department is not None:
        user.department = req.department
    if req.full_name is not None:
        user.full_name = req.full_name
    if req.is_active is not None:
        user.is_active = req.is_active

    db.commit()
    db.refresh(user)
    return user
