from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, desc
from app.models.ticket import Ticket, Category, TicketStatus, TicketPriority
from app.models.comment import TicketComment, CommentType
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog, AuditAction
from app.schemas.ticket import TicketCreate, TicketUpdate


from app.schemas.comment import CommentCreate
from app.core.exceptions import NotFoundError, ForbiddenError, ValidationError
from app.services.audit_service import log_ticket_event


def generate_ticket_number(db: Session) -> str:
    """Generate sequential, human-friendly ticket identifier (e.g., IT-1001)."""
    count = db.query(func.count(Ticket.id)).scalar() or 0
    return f"IT-{1001 + count}"


def calculate_sla_due_at(db: Session, category_id: Optional[int], priority: str) -> datetime:
    """Calculate SLA target deadline based on Category SLA hours and Priority multiplier."""
    sla_hours = 24  # default
    if category_id:
        category = db.query(Category).filter(Category.id == category_id).first()
        if category and category.default_sla_hours:
            sla_hours = category.default_sla_hours

    # Priority multipliers
    multipliers = {
        TicketPriority.CRITICAL: 0.25,  # 4x faster (e.g. 6 hours)
        TicketPriority.HIGH: 0.5,       # 2x faster (e.g. 12 hours)
        TicketPriority.MEDIUM: 1.0,     # Standard
        TicketPriority.LOW: 2.0         # 2x longer
    }
    multiplier = multipliers.get(priority, 1.0)
    effective_hours = max(1.0, sla_hours * multiplier)

    return datetime.now(timezone.utc) + timedelta(hours=effective_hours)


def create_ticket(db: Session, req: TicketCreate, creator: User) -> Ticket:
    """Create a new ticket and record audit creation entry."""
    ticket_num = generate_ticket_number(db)
    priority = req.priority.lower() if req.priority and req.priority.lower() in TicketPriority.ALL else TicketPriority.MEDIUM
    sla_due = calculate_sla_due_at(db, req.category_id, priority)

    ticket = Ticket(
        ticket_number=ticket_num,
        title=req.title,
        description=req.description,
        status=TicketStatus.OPEN,
        priority=priority,
        category_id=req.category_id,
        creator_id=creator.id,
        sla_due_at=sla_due,
    )
    db.add(ticket)
    db.flush()

    # Log audit trail
    log_ticket_event(
        db=db,
        ticket_id=ticket.id,
        actor_id=creator.id,
        action=AuditAction.CREATED,
        new_state={"title": ticket.title, "status": ticket.status, "priority": ticket.priority}
    )

    db.commit()
    db.refresh(ticket)
    return ticket


def get_ticket_by_id(db: Session, ticket_id: str, current_user: User) -> Ticket:
    """Fetch ticket details with relationships and enforce role-based access."""
    ticket = db.query(Ticket).options(
        joinedload(Ticket.category),
        joinedload(Ticket.creator),
        joinedload(Ticket.assignee),
        joinedload(Ticket.comments).joinedload(TicketComment.author),
        joinedload(Ticket.audit_logs).joinedload(AuditLog.actor)
    ).filter(or_(Ticket.id == ticket_id, Ticket.ticket_number == ticket_id)).first()

    if not ticket:
        raise NotFoundError("Ticket", ticket_id)

    # Regular users can only view their own tickets
    if current_user.role == UserRole.USER and ticket.creator_id != current_user.id:
        raise ForbiddenError("You are not authorized to view this ticket.")

    return ticket


def list_tickets(
    db: Session,
    current_user: User,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    assigned_to_me: bool = False
) -> Tuple[List[Ticket], int]:
    """List tickets with filtering, pagination, and role-scoped visibility."""
    query = db.query(Ticket).options(
        joinedload(Ticket.category),
        joinedload(Ticket.creator),
        joinedload(Ticket.assignee)
    )

    # Scoping: Users only see their tickets
    if current_user.role == UserRole.USER:
        query = query.filter(Ticket.creator_id == current_user.id)
    elif assigned_to_me and current_user.role in [UserRole.AGENT, UserRole.ADMIN]:
        query = query.filter(Ticket.assignee_id == current_user.id)

    # Filters
    if status and status in TicketStatus.ALL:
        query = query.filter(Ticket.status == status)
    if priority and priority in TicketPriority.ALL:
        query = query.filter(Ticket.priority == priority)
    if category_id:
        query = query.filter(Ticket.category_id == category_id)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Ticket.ticket_number.ilike(search_filter),
                Ticket.title.ilike(search_filter),
                Ticket.description.ilike(search_filter)
            )
        )

    total = query.count()
    items = query.order_by(desc(Ticket.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    return items, total


def update_ticket(
    db: Session,
    ticket_id: str,
    req: TicketUpdate,
    actor: User
) -> Ticket:
    """Update ticket fields, validate transitions, and record audit log."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise NotFoundError("Ticket", ticket_id)

    # Role check: Only agents/admins can update status, priority, assignment
    if actor.role == UserRole.USER:
        # Users can only update their own ticket title/description if still OPEN
        if ticket.creator_id != actor.id:
            raise ForbiddenError("You can only edit your own tickets.")
        if ticket.status != TicketStatus.OPEN:
            raise ForbiddenError("Cannot edit ticket details once it has entered processing.")
        
        if req.title:
            ticket.title = req.title
        if req.description:
            ticket.description = req.description
        db.commit()
        db.refresh(ticket)
        return ticket

    # Agent / Admin updates
    prev_state = {
        "status": ticket.status,
        "priority": ticket.priority,
        "assignee_id": ticket.assignee_id,
        "category_id": ticket.category_id
    }

    if req.status and req.status in TicketStatus.ALL:
        if ticket.status != req.status:
            ticket.status = req.status
            log_ticket_event(
                db=db,
                ticket_id=ticket.id,
                actor_id=actor.id,
                action=AuditAction.STATUS_CHANGED,
                previous_state={"status": prev_state["status"]},
                new_state={"status": req.status}
            )
            if req.status == TicketStatus.RESOLVED:
                ticket.resolved_at = datetime.now(timezone.utc)
            elif req.status == TicketStatus.CLOSED:
                ticket.closed_at = datetime.now(timezone.utc)

    if req.priority and req.priority in TicketPriority.ALL:
        if ticket.priority != req.priority:
            ticket.priority = req.priority
            # Recalculate SLA
            ticket.sla_due_at = calculate_sla_due_at(db, ticket.category_id, req.priority)
            log_ticket_event(
                db=db,
                ticket_id=ticket.id,
                actor_id=actor.id,
                action=AuditAction.PRIORITY_CHANGED,
                previous_state={"priority": prev_state["priority"]},
                new_state={"priority": req.priority}
            )

    if req.assignee_id is not None:
        if req.assignee_id != ticket.assignee_id:
            ticket.assignee_id = req.assignee_id if req.assignee_id != "" else None
            log_ticket_event(
                db=db,
                ticket_id=ticket.id,
                actor_id=actor.id,
                action=AuditAction.ASSIGNED,
                previous_state={"assignee_id": prev_state["assignee_id"]},
                new_state={"assignee_id": ticket.assignee_id}
            )

    if req.category_id is not None:
        ticket.category_id = req.category_id

    if req.title:
        ticket.title = req.title
    if req.description:
        ticket.description = req.description

    db.commit()
    db.refresh(ticket)
    return ticket


def add_ticket_comment(
    db: Session,
    ticket_id: str,
    req: CommentCreate,
    author: User
) -> TicketComment:
    """Add a public comment or internal agent note to a ticket."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise NotFoundError("Ticket", ticket_id)

    # Permission check for internal note
    if req.comment_type == CommentType.INTERNAL_NOTE and author.role == UserRole.USER:
        raise ForbiddenError("End-users cannot post internal agent notes.")

    # Regular users can only comment on their own tickets
    if author.role == UserRole.USER and ticket.creator_id != author.id:
        raise ForbiddenError("You cannot comment on a ticket that does not belong to you.")

    comment = TicketComment(
        ticket_id=ticket.id,
        author_id=author.id,
        comment_type=req.comment_type if req.comment_type in CommentType.ALL else CommentType.PUBLIC,
        content=req.content
    )
    db.add(comment)

    # If ticket was pending customer and user commented, transition to in_progress
    if author.role == UserRole.USER and ticket.status == TicketStatus.PENDING_CUSTOMER:
        ticket.status = TicketStatus.IN_PROGRESS

    log_ticket_event(
        db=db,
        ticket_id=ticket.id,
        actor_id=author.id,
        action=AuditAction.COMMENT_ADDED,
        new_state={"comment_type": comment.comment_type}
    )

    db.commit()
    db.refresh(comment)
    return comment
