from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.sla import (
    SLAPolicyCreate,
    SLAPolicyUpdate,
    SLAPolicyResponse,
    SLAPolicyListResponse,
)
from app.services.sla_service import (
    create_sla_policy,
    list_sla_policies,
    get_sla_policy,
    update_sla_policy,
    delete_sla_policy,
)

sla_router = APIRouter(prefix="/sla", tags=["SLA Policies"])


@sla_router.get("/policies", response_model=SLAPolicyListResponse)
def get_all_policies(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.AGENT, UserRole.ADMIN])),
):
    """List all SLA policies (Staff only)."""
    items, total = list_sla_policies(db=db, actor=current_user, is_active=is_active)
    return SLAPolicyListResponse(
        items=[SLAPolicyResponse.model_validate(p) for p in items],
        total=total
    )


@sla_router.post("/policies", response_model=SLAPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_new_policy(
    req: SLAPolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
):
    """Create a new SLA policy (Admin only)."""
    policy = create_sla_policy(db=db, req=req, actor=current_user)
    return SLAPolicyResponse.model_validate(policy)


@sla_router.get("/policies/{policy_id}", response_model=SLAPolicyResponse)
def get_single_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.AGENT, UserRole.ADMIN])),
):
    """Get SLA policy by ID (Staff only)."""
    policy = get_sla_policy(db=db, policy_id=policy_id, actor=current_user)
    return SLAPolicyResponse.model_validate(policy)


@sla_router.put("/policies/{policy_id}", response_model=SLAPolicyResponse)
def update_existing_policy(
    policy_id: int,
    req: SLAPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
):
    """Update an SLA policy (Admin only)."""
    policy = update_sla_policy(db=db, policy_id=policy_id, req=req, actor=current_user)
    return SLAPolicyResponse.model_validate(policy)


@sla_router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
):
    """Delete an SLA policy (Admin only)."""
    delete_sla_policy(db=db, policy_id=policy_id, actor=current_user)
    return None
