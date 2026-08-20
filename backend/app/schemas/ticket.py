from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import UserResponse, AgentSummary


# Category Schemas
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    default_sla_hours: int = 24
    is_active: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# Comment Summary for Ticket View
class CommentSummary(BaseModel):
    id: str
    ticket_id: str
    author_id: Optional[str]
    author: Optional[AgentSummary] = None
    comment_type: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Audit Log Summary for Ticket Timeline
class AuditLogSummary(BaseModel):
    id: str
    ticket_id: str
    actor_id: Optional[str]
    actor: Optional[AgentSummary] = None
    action: str
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Ticket Schemas
class TicketCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=5)
    category_id: Optional[int] = None
    priority: Optional[str] = "medium"


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    category_id: Optional[int] = None
    assignee_id: Optional[str] = None


class TicketResponse(BaseModel):
    id: str
    ticket_number: str
    title: str
    description: str
    status: str
    priority: str
    category_id: Optional[int] = None
    category: Optional[CategoryResponse] = None
    creator_id: str
    creator: Optional[UserResponse] = None
    assignee_id: Optional[str] = None
    assignee: Optional[AgentSummary] = None
    ai_suggested_category: Optional[str] = None
    ai_suggested_priority: Optional[str] = None
    ai_confidence_score: Optional[float] = None
    sla_due_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TicketDetailResponse(TicketResponse):
    comments: List[CommentSummary] = []
    audit_logs: List[AuditLogSummary] = []


class TicketListResponse(BaseModel):
    items: List[TicketResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
