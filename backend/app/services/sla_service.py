from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.models.ticket import Ticket, Category, TicketStatus, TicketPriority
from app.models.sla_policy import SLAPolicy
from app.models.user import User, UserRole
from app.schemas.sla import (
    SLAState,
    FirstResponseStatus,
    TicketSLAMetrics,
    TicketSLAResponse,
    SLAPolicyCreate,
    SLAPolicyUpdate,
)
from app.core.exceptions import NotFoundError, ForbiddenError, ValidationError, ConflictError


def get_effective_sla_policy(
    db: Session,
    priority: Optional[str],
    category_id: Optional[int]
) -> Tuple[str, float, float, float, float]:
    """
    Determine the effective SLA policy and target durations.
    Returns: (policy_name, first_response_hours, resolution_hours, warning_threshold_pct, escalation_threshold_pct)
    
    Hierarchy:
    1. Active policy matching both category_id and priority
    2. Active policy matching priority (category_id is NULL)
    3. Active policy matching category_id (priority is NULL)
    4. Default standard policy computed from category.default_sla_hours and priority multipliers
    """
    normalized_priority = priority.lower() if priority else TicketPriority.MEDIUM

    # 1. Match both category and priority
    if category_id:
        policy = db.query(SLAPolicy).filter(
            SLAPolicy.category_id == category_id,
            SLAPolicy.priority == normalized_priority,
            SLAPolicy.is_active == True
        ).first()
        if policy:
            return (
                policy.name,
                policy.first_response_hours,
                policy.resolution_hours,
                policy.warning_threshold_pct,
                policy.escalation_threshold_pct
            )

    # 2. Match priority only
    policy = db.query(SLAPolicy).filter(
        SLAPolicy.priority == normalized_priority,
        SLAPolicy.category_id == None,
        SLAPolicy.is_active == True
    ).first()
    if policy:
        return (
            policy.name,
            policy.first_response_hours,
            policy.resolution_hours,
            policy.warning_threshold_pct,
            policy.escalation_threshold_pct
        )

    # 3. Match category only
    if category_id:
        policy = db.query(SLAPolicy).filter(
            SLAPolicy.category_id == category_id,
            SLAPolicy.priority == None,
            SLAPolicy.is_active == True
        ).first()
        if policy:
            return (
                policy.name,
                policy.first_response_hours,
                policy.resolution_hours,
                policy.warning_threshold_pct,
                policy.escalation_threshold_pct
            )

    # 4. Standard Default Fallback
    base_sla_hours = 24.0
    if category_id:
        category = db.query(Category).filter(Category.id == category_id).first()
        if category and category.default_sla_hours:
            base_sla_hours = float(category.default_sla_hours)

    multipliers = {
        TicketPriority.CRITICAL: (1.0, 4.0),   # 1h first response, 4h resolution
        TicketPriority.HIGH: (2.0, 8.0),       # 2h first response, 8h resolution
        TicketPriority.MEDIUM: (4.0, 24.0),    # 4h first response, 24h resolution
        TicketPriority.LOW: (8.0, 48.0),       # 8h first response, 48h resolution
    }

    first_resp_h, res_h = multipliers.get(normalized_priority, (4.0, base_sla_hours))
    # If category SLA is customized, adjust resolution hours proportionally
    if category_id and base_sla_hours != 24.0:
        priority_factor = {
            TicketPriority.CRITICAL: 0.25,
            TicketPriority.HIGH: 0.5,
            TicketPriority.MEDIUM: 1.0,
            TicketPriority.LOW: 2.0,
        }.get(normalized_priority, 1.0)
        res_h = max(1.0, base_sla_hours * priority_factor)
        first_resp_h = max(0.5, min(first_resp_h, res_h * 0.25))

    return (
        f"Standard {normalized_priority.capitalize()} SLA Policy",
        first_resp_h,
        res_h,
        0.75,
        0.90
    )


def calculate_ticket_sla_metrics(
    db: Session,
    ticket: Ticket,
    now_dt: Optional[datetime] = None
) -> TicketSLAMetrics:
    """
    Calculate accurate, real-time SLA state and consumption metrics for a ticket.
    Guarantees timezone-aware UTC datetime arithmetic.
    """
    now_utc = now_dt or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    ticket_created = ticket.created_at.replace(tzinfo=timezone.utc) if ticket.created_at.tzinfo is None else ticket.created_at

    policy_name, first_resp_h, res_h, warning_pct, escalation_pct = get_effective_sla_policy(
        db=db,
        priority=ticket.priority,
        category_id=ticket.category_id
    )

    # --------------------------------------------------------------------------
    # 1. First Response SLA Calculation
    # --------------------------------------------------------------------------
    first_response_target_seconds = first_resp_h * 3600.0
    staff_comments = [
        c for c in (ticket.comments or [])
        if c.author_id != ticket.creator_id
    ]

    if staff_comments:
        first_comment = min(staff_comments, key=lambda c: c.created_at)
        comment_created = first_comment.created_at.replace(tzinfo=timezone.utc) if first_comment.created_at.tzinfo is None else first_comment.created_at
        first_response_at = comment_created
        first_response_elapsed_seconds = max(0.0, (comment_created - ticket_created).total_seconds())
        if first_response_elapsed_seconds <= first_response_target_seconds:
            first_response_status = FirstResponseStatus.MET
        else:
            first_response_status = FirstResponseStatus.BREACHED
    elif ticket.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
        # One-touch resolution: resolving the ticket satisfies the initial response
        resolved_raw = ticket.resolved_at or ticket.closed_at or ticket.updated_at
        res_dt = resolved_raw.replace(tzinfo=timezone.utc) if resolved_raw.tzinfo is None else resolved_raw
        first_response_at = res_dt
        first_response_elapsed_seconds = max(0.0, (res_dt - ticket_created).total_seconds())
        if first_response_elapsed_seconds <= first_response_target_seconds:
            first_response_status = FirstResponseStatus.MET
        else:
            first_response_status = FirstResponseStatus.BREACHED
    else:
        first_response_at = None
        first_response_elapsed_seconds = None
        current_elapsed_from_creation = max(0.0, (now_utc - ticket_created).total_seconds())
        if current_elapsed_from_creation > first_response_target_seconds:
            first_response_status = FirstResponseStatus.BREACHED_PENDING
        else:
            first_response_status = FirstResponseStatus.PENDING

    # --------------------------------------------------------------------------
    # 2. Resolution SLA Calculation
    # --------------------------------------------------------------------------
    resolution_target_seconds = res_h * 3600.0
    if ticket.sla_due_at:
        due_at_utc = ticket.sla_due_at.replace(tzinfo=timezone.utc) if ticket.sla_due_at.tzinfo is None else ticket.sla_due_at
        resolution_target_seconds = max(1.0, (due_at_utc - ticket_created).total_seconds())
    else:
        due_at_utc = ticket_created + timedelta(seconds=resolution_target_seconds)

    is_resolved_or_closed = ticket.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]

    if is_resolved_or_closed:
        resolved_raw = ticket.resolved_at or ticket.closed_at or ticket.updated_at
        resolution_at = resolved_raw.replace(tzinfo=timezone.utc) if resolved_raw.tzinfo is None else resolved_raw
        resolution_elapsed_seconds = max(0.0, (resolution_at - ticket_created).total_seconds())
        remaining_seconds = max(0.0, resolution_target_seconds - resolution_elapsed_seconds)
        
        if resolution_target_seconds > 0:
            percentage_consumed = min(100.0, round((resolution_elapsed_seconds / resolution_target_seconds) * 100.0, 1))
        else:
            percentage_consumed = 100.0

        is_resolution_breached = resolution_elapsed_seconds > resolution_target_seconds
        is_first_resp_breached = first_response_status in [FirstResponseStatus.BREACHED, FirstResponseStatus.BREACHED_PENDING]
        is_breached = is_resolution_breached or is_first_resp_breached
        is_at_risk = False

        if is_resolution_breached:
            sla_state = SLAState.RESOLVED_BREACHED
        else:
            sla_state = SLAState.RESOLVED_MET

    else:
        # Active Ticket (OPEN, IN_PROGRESS, PENDING_CUSTOMER)
        resolution_at = None
        resolution_elapsed_seconds = max(0.0, (now_utc - ticket_created).total_seconds())
        remaining_seconds = max(0.0, resolution_target_seconds - resolution_elapsed_seconds)

        if resolution_target_seconds > 0:
            percentage_consumed = min(100.0, round((resolution_elapsed_seconds / resolution_target_seconds) * 100.0, 1))
        else:
            percentage_consumed = 100.0

        is_resolution_breached = resolution_elapsed_seconds >= resolution_target_seconds
        is_first_resp_breached = first_response_status in [FirstResponseStatus.BREACHED, FirstResponseStatus.BREACHED_PENDING]
        is_breached = is_resolution_breached or is_first_resp_breached

        is_at_risk = (percentage_consumed >= (warning_pct * 100.0)) and not is_breached

        if ticket.status == TicketStatus.PENDING_CUSTOMER:
            sla_state = SLAState.PAUSED
        elif is_breached:
            sla_state = SLAState.BREACHED
        elif is_at_risk:
            sla_state = SLAState.AT_RISK
        else:
            sla_state = SLAState.ON_TRACK

    return TicketSLAMetrics(
        policy_name=policy_name,
        target_first_response_hours=first_resp_h,
        target_resolution_hours=round(resolution_target_seconds / 3600.0, 2),
        first_response_status=first_response_status,
        first_response_at=first_response_at,
        first_response_elapsed_seconds=round(first_response_elapsed_seconds, 1) if first_response_elapsed_seconds is not None else None,
        resolution_at=resolution_at,
        resolution_elapsed_seconds=round(resolution_elapsed_seconds, 1),
        remaining_seconds=round(remaining_seconds, 1),
        percentage_consumed=percentage_consumed,
        sla_state=sla_state,
        sla_due_at=due_at_utc,
        is_breached=is_breached,
        is_at_risk=is_at_risk,
        warning_threshold_pct=warning_pct,
        escalation_threshold_pct=escalation_pct,
    )


def get_ticket_sla_response(db: Session, ticket: Ticket, current_user: User) -> TicketSLAResponse:
    """Retrieve full ticket SLA state payload with RBAC enforcement."""
    # User scoping: Regular users can only access their own ticket SLA metrics
    if current_user.role == UserRole.USER and ticket.creator_id != current_user.id:
        raise ForbiddenError("You are not authorized to view SLA metrics for this ticket.")

    metrics = calculate_ticket_sla_metrics(db, ticket)
    category_name = ticket.category.name if ticket.category else None

    return TicketSLAResponse(
        ticket_id=ticket.id,
        ticket_number=ticket.ticket_number,
        priority=ticket.priority,
        category_id=ticket.category_id,
        category_name=category_name,
        status=ticket.status,
        created_at=ticket.created_at,
        sla_metrics=metrics
    )


# ==============================================================================
# SLA Policy CRUD (Admin Only)
# ==============================================================================

def create_sla_policy(db: Session, req: SLAPolicyCreate, actor: User) -> SLAPolicy:
    if actor.role != UserRole.ADMIN:
        raise ForbiddenError("Only administrators can create SLA policies.")

    existing = db.query(SLAPolicy).filter(SLAPolicy.name == req.name).first()
    if existing:
        raise ConflictError(f"SLA policy with name '{req.name}' already exists.")

    if req.category_id:
        cat = db.query(Category).filter(Category.id == req.category_id).first()
        if not cat:
            raise NotFoundError("Category", req.category_id)

    policy = SLAPolicy(
        name=req.name,
        description=req.description,
        priority=req.priority.lower() if req.priority else None,
        category_id=req.category_id,
        first_response_hours=req.first_response_hours,
        resolution_hours=req.resolution_hours,
        warning_threshold_pct=req.warning_threshold_pct,
        escalation_threshold_pct=req.escalation_threshold_pct,
        is_active=req.is_active,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def list_sla_policies(db: Session, actor: User, is_active: Optional[bool] = None) -> Tuple[List[SLAPolicy], int]:
    if actor.role not in [UserRole.AGENT, UserRole.ADMIN]:
        raise ForbiddenError("Only staff members can list SLA policies.")

    query = db.query(SLAPolicy)
    if is_active is not None:
        query = query.filter(SLAPolicy.is_active == is_active)

    total = query.count()
    items = query.order_by(desc(SLAPolicy.created_at)).all()
    return items, total


def get_sla_policy(db: Session, policy_id: int, actor: User) -> SLAPolicy:
    if actor.role not in [UserRole.AGENT, UserRole.ADMIN]:
        raise ForbiddenError("Only staff members can view SLA policy details.")

    policy = db.query(SLAPolicy).filter(SLAPolicy.id == policy_id).first()
    if not policy:
        raise NotFoundError("SLAPolicy", policy_id)
    return policy


def update_sla_policy(db: Session, policy_id: int, req: SLAPolicyUpdate, actor: User) -> SLAPolicy:
    if actor.role != UserRole.ADMIN:
        raise ForbiddenError("Only administrators can update SLA policies.")

    policy = db.query(SLAPolicy).filter(SLAPolicy.id == policy_id).first()
    if not policy:
        raise NotFoundError("SLAPolicy", policy_id)

    if req.name and req.name != policy.name:
        existing = db.query(SLAPolicy).filter(SLAPolicy.name == req.name, SLAPolicy.id != policy_id).first()
        if existing:
            raise ConflictError(f"SLA policy with name '{req.name}' already exists.")
        policy.name = req.name

    if req.description is not None:
        policy.description = req.description
    if req.priority is not None:
        policy.priority = req.priority.lower() if req.priority else None
    if req.category_id is not None:
        if req.category_id != policy.category_id:
            cat = db.query(Category).filter(Category.id == req.category_id).first()
            if not cat:
                raise NotFoundError("Category", req.category_id)
            policy.category_id = cat.id
    if req.first_response_hours is not None:
        policy.first_response_hours = req.first_response_hours
    if req.resolution_hours is not None:
        policy.resolution_hours = req.resolution_hours
    if req.warning_threshold_pct is not None:
        policy.warning_threshold_pct = req.warning_threshold_pct
    if req.escalation_threshold_pct is not None:
        policy.escalation_threshold_pct = req.escalation_threshold_pct
    if req.is_active is not None:
        policy.is_active = req.is_active

    db.commit()
    db.refresh(policy)
    return policy


def delete_sla_policy(db: Session, policy_id: int, actor: User) -> None:
    if actor.role != UserRole.ADMIN:
        raise ForbiddenError("Only administrators can delete SLA policies.")

    policy = db.query(SLAPolicy).filter(SLAPolicy.id == policy_id).first()
    if not policy:
        raise NotFoundError("SLAPolicy", policy_id)

    db.delete(policy)
    db.commit()
