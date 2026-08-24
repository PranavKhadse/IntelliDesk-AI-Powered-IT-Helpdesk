from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class GroundingStatus(str, Enum):
    GROUNDED = "grounded"
    PARTIALLY_GROUNDED = "partially_grounded"
    NO_MATCH = "no_match"


class GroundedArticleReference(BaseModel):
    article_id: str
    slug: str
    title: str
    category: Optional[str] = None
    relevance_score: float = Field(ge=0.0, le=1.0)
    snippet: str


class ProviderGroundingResult(BaseModel):
    """Structured JSON contract expected from an AI provider for KB grounding."""
    grounding_status: GroundingStatus
    grounded_response: str = Field(min_length=1)
    cited_article_ids: List[str] = Field(default_factory=list)
    key_points: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(default="")


class TicketGroundingResponse(BaseModel):
    """Client-facing grounded AI recommendation with verified sources."""
    ticket_id: str
    ticket_number: str
    grounding_status: GroundingStatus
    recommendation: str
    key_points: List[str] = Field(default_factory=list)
    sources: List[GroundedArticleReference] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""
    no_match_reason: Optional[str] = None
