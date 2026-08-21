from enum import Enum
from typing import List, Literal
from pydantic import BaseModel, Field


class TriageUrgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TriageImpact(str, Enum):
    INDIVIDUAL = "individual"
    TEAM = "team"
    DEPARTMENT = "department"
    ORGANIZATION_WIDE = "organization_wide"


class TicketTriageInput(BaseModel):
    """The minimum ticket and controlled application context sent to the AI service."""

    title: str
    description: str
    available_categories: List[str] = Field(min_length=1)
    valid_priorities: List[str] = Field(min_length=1)
    available_teams: List[str] = Field(min_length=1)


class ProviderTriageRecommendation(BaseModel):
    """Structured JSON contract expected from an AI provider."""

    category: str = Field(min_length=1, max_length=100)
    priority: str = Field(min_length=1, max_length=50)
    urgency: TriageUrgency
    impact: TriageImpact
    suggested_team: str = Field(min_length=1, max_length=100)
    confidence: float = Field(ge=0, le=1)
    evidence: List[str] = Field(min_length=1, max_length=3)
    priority_evidence: List[str] = Field(min_length=1, max_length=3)
    category_evidence: List[str] = Field(min_length=1, max_length=3)
    urgency_impact_evidence: List[str] = Field(min_length=1, max_length=3)


class TicketTriageRecommendationBase(BaseModel):
    """Validated, recommendation-only triage result returned to clients."""

    category: str
    priority: str
    urgency: TriageUrgency
    impact: TriageImpact
    suggested_team: str
    confidence: float = Field(ge=0, le=1)
    confidence_level: str = "Medium"
    evidence: List[str]
    priority_reason: str
    category_reason: str
    urgency_impact_reason: str
    explanation: str


class TicketTriageRecommendation(TicketTriageRecommendationBase):
    recommendation_id: str


class TriageDecisionRequest(BaseModel):
    recommendation_id: str = Field(min_length=1, max_length=36)


class TriageDecisionResponse(BaseModel):
    recommendation_id: str
    decision: Literal["accepted", "rejected"]
