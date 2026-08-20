import math
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.ticket import Category
from app.schemas.ticket import (
    TicketCreate, TicketUpdate, TicketResponse, TicketDetailResponse, TicketListResponse,
    CategoryResponse
)
from app.schemas.comment import CommentCreate, CommentResponse
from app.services.ticket_service import (
    create_ticket, get_ticket_by_id, list_tickets, update_ticket, add_ticket_comment
)

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.get("/categories", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    """List all active ticket categories with SLA targets."""
    return db.query(Category).filter(Category.is_active == True).all()


@router.get("/", response_model=TicketListResponse)
def get_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    assigned_to_me: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List tickets with pagination, search, status/priority filtering, and role scoping."""
    items, total = list_tickets(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        status=status,
        priority=priority,
        category_id=category_id,
        search=search,
        assigned_to_me=assigned_to_me
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    return TicketListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_new_ticket(
    req: TicketCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new service desk ticket."""
    return create_ticket(db, req, current_user)


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket_detail(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get full ticket details including comments and audit log timeline."""
    ticket = get_ticket_by_id(db, ticket_id, current_user)
    
    # Filter out internal notes if viewer is a regular user
    filtered_comments = ticket.comments
    if current_user.role == "user":
        filtered_comments = [c for c in ticket.comments if c.comment_type != "internal_note"]
    
    return TicketDetailResponse(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        category_id=ticket.category_id,
        category=ticket.category,
        creator_id=ticket.creator_id,
        creator=ticket.creator,
        assignee_id=ticket.assignee_id,
        assignee=ticket.assignee,
        ai_suggested_category=ticket.ai_suggested_category,
        ai_suggested_priority=ticket.ai_suggested_priority,
        ai_confidence_score=ticket.ai_confidence_score,
        sla_due_at=ticket.sla_due_at,
        resolved_at=ticket.resolved_at,
        closed_at=ticket.closed_at,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        comments=filtered_comments,
        audit_logs=ticket.audit_logs
    )


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket_endpoint(
    ticket_id: str,
    req: TicketUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update ticket status, priority, assignment, or metadata."""
    return update_ticket(db, ticket_id, req, current_user)


@router.post("/{ticket_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def post_comment(
    ticket_id: str,
    req: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a public comment or internal agent note to a ticket."""
    return add_ticket_comment(db, ticket_id, req, current_user)
