import math
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.ticket import Category
from app.models.comment import CommentType
from app.schemas.ticket import (
    TicketCreate, TicketUpdate, TicketResponse, TicketDetailResponse, TicketListResponse,
    CategoryResponse
)
from app.core.exceptions import ForbiddenError
from app.schemas.comment import CommentCreate, CommentResponse
from app.schemas.response_draft import ResponseDraft
from app.schemas.triage import TicketTriageRecommendation, TriageDecisionRequest, TriageDecisionResponse
from app.services.ticket_service import (
    create_ticket, get_ticket_by_id, list_tickets, update_ticket, add_ticket_comment
)
from app.services.ai_service import get_ai_service
from app.services.response_draft_service import generate_response_draft
from app.services.triage_service import (
    approve_ticket_triage,
    build_ticket_triage_input,
    generate_ticket_triage,
    reject_ticket_triage,
    store_ticket_triage,
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
    
    # Filter comments: regular users only see public comments
    filtered_comments = ticket.comments
    if current_user.role == UserRole.USER:
        filtered_comments = [c for c in ticket.comments if c.comment_type == CommentType.PUBLIC]
    
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


@router.post("/{ticket_id}/ai-triage", response_model=TicketTriageRecommendation)
def triage_ticket(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Return a validated AI triage recommendation without modifying the ticket."""
    ticket = get_ticket_by_id(db, ticket_id, current_user)
    categories = [category.name for category in db.query(Category).filter(Category.is_active == True).all()]
    teams = [
        department for (department,) in db.query(User.department).filter(
            User.role.in_([UserRole.AGENT, UserRole.ADMIN]),
            User.is_active == True
        ).distinct().all() if department
    ]
    triage_input = build_ticket_triage_input(ticket, categories, teams)
    recommendation = generate_ticket_triage(triage_input, get_ai_service())
    return store_ticket_triage(db, ticket, current_user, recommendation)


@router.post("/{ticket_id}/ai-triage/approve", response_model=TriageDecisionResponse)
def approve_ticket_decision(
    ticket_id: str,
    req: TriageDecisionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply a previously generated AI recommendation only after human approval."""
    ticket = get_ticket_by_id(db, ticket_id, current_user)
    approve_ticket_triage(db, ticket, current_user, req.recommendation_id)
    return TriageDecisionResponse(recommendation_id=req.recommendation_id, decision="accepted")


@router.post("/{ticket_id}/ai-triage/reject", response_model=TriageDecisionResponse)
def reject_ticket_decision(
    ticket_id: str,
    req: TriageDecisionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Decline a previously generated AI recommendation without changing the ticket."""
    ticket = get_ticket_by_id(db, ticket_id, current_user)
    reject_ticket_triage(db, ticket, current_user, req.recommendation_id)
    return TriageDecisionResponse(recommendation_id=req.recommendation_id, decision="rejected")


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket_endpoint(
    ticket_id: str,
    req: TicketUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update ticket status, priority, assignment, or metadata."""
    return update_ticket(db, ticket_id, req, current_user)


@router.post("/{ticket_id}/ai-response-draft", response_model=ResponseDraft)
def draft_ticket_response_endpoint(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an AI-assisted customer response draft for support staff (Agent/Admin only)."""
    if current_user.role not in [UserRole.AGENT, UserRole.ADMIN]:
        raise ForbiddenError("Only support staff can generate AI response drafts.")
    ticket = get_ticket_by_id(db, ticket_id, current_user)
    return generate_response_draft(ticket, get_ai_service())


@router.post("/{ticket_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def post_comment(
    ticket_id: str,
    req: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a public comment or internal agent note to a ticket."""
    return add_ticket_comment(db, ticket_id, req, current_user)
