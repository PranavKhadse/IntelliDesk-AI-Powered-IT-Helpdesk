from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import AgentSummary


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)
    comment_type: str = Field("public", description="public, internal_note, system_event, ai_resolution_draft")


class CommentResponse(BaseModel):
    id: str
    ticket_id: str
    author_id: Optional[str] = None
    author: Optional[AgentSummary] = None
    comment_type: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
