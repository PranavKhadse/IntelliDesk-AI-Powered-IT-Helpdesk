from enum import Enum
from typing import List, Literal
from pydantic import BaseModel, Field, field_validator


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

    @field_validator("impact", mode="before")
    @classmethod
    def normalize_impact(cls, value: object) -> object:
        if isinstance(value, str):
            val_clean = value.strip().lower()
            mapping = {
                "low": TriageImpact.INDIVIDUAL,
                "minor": TriageImpact.INDIVIDUAL,
                "single_user": TriageImpact.INDIVIDUAL,
                "individual": TriageImpact.INDIVIDUAL,
                "medium": TriageImpact.TEAM,
                "moderate": TriageImpact.TEAM,
                "team": TriageImpact.TEAM,
                "high": TriageImpact.DEPARTMENT,
                "major": TriageImpact.DEPARTMENT,
                "department": TriageImpact.DEPARTMENT,
                "critical": TriageImpact.ORGANIZATION_WIDE,
                "company_wide": TriageImpact.ORGANIZATION_WIDE,
                "organization_wide": TriageImpact.ORGANIZATION_WIDE,
                "organization": TriageImpact.ORGANIZATION_WIDE,
            }
            if val_clean in mapping:
                return mapping[val_clean]
        return value


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
