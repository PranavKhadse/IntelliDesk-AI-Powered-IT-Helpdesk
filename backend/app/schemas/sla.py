from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SLAState(str, Enum):
    ON_TRACK = "ON_TRACK"
    AT_RISK = "AT_RISK"
    BREACHED = "BREACHED"
    PAUSED = "PAUSED"
    RESOLVED_MET = "RESOLVED_MET"
    RESOLVED_BREACHED = "RESOLVED_BREACHED"


class FirstResponseStatus(str, Enum):
    MET = "met"
    PENDING = "pending"
    BREACHED = "breached"
    BREACHED_PENDING = "breached_pending"


# ==============================================================================
# SLA Policy Schemas
# ==============================================================================

class SLAPolicyBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    priority: Optional[str] = Field(None, max_length=50)
    category_id: Optional[int] = None
    first_response_hours: float = Field(gt=0, le=720, description="Target hours for first response")
    resolution_hours: float = Field(gt=0, le=2160, description="Target hours for resolution")
    warning_threshold_pct: float = Field(default=0.75, ge=0.1, le=0.99, description="Threshold ratio to mark AT_RISK (e.g. 0.75)")
    escalation_threshold_pct: float = Field(default=0.90, ge=0.2, le=1.0, description="Threshold ratio for escalation warning")
    is_active: bool = True


class SLAPolicyCreate(SLAPolicyBase):
    pass


class SLAPolicyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    priority: Optional[str] = Field(None, max_length=50)
    category_id: Optional[int] = None
    first_response_hours: Optional[float] = Field(None, gt=0, le=720)
    resolution_hours: Optional[float] = Field(None, gt=0, le=2160)
    warning_threshold_pct: Optional[float] = Field(None, ge=0.1, le=0.99)
    escalation_threshold_pct: Optional[float] = Field(None, ge=0.2, le=1.0)
    is_active: Optional[bool] = None


class SLAPolicyResponse(SLAPolicyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class SLAPolicyListResponse(BaseModel):
    items: List[SLAPolicyResponse]
    total: int


# ==============================================================================
# Ticket SLA State & Metrics Schemas (System-Calculated Ground Truth)
# ==============================================================================

class TicketSLAMetrics(BaseModel):
    policy_name: str
    target_first_response_hours: float
    target_resolution_hours: float
    first_response_status: FirstResponseStatus
    first_response_at: Optional[datetime] = None
    first_response_elapsed_seconds: Optional[float] = None
    resolution_at: Optional[datetime] = None
    resolution_elapsed_seconds: float
    remaining_seconds: float
    percentage_consumed: float
    sla_state: SLAState
    sla_due_at: Optional[datetime] = None
    is_breached: bool
    is_at_risk: bool
    warning_threshold_pct: float
    escalation_threshold_pct: float


class TicketSLAResponse(BaseModel):
    ticket_id: str
    ticket_number: str
    priority: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    status: str
    created_at: datetime
    sla_metrics: TicketSLAMetrics


# ==============================================================================
# AI SLA Risk & Escalation Intelligence Schemas
# ==============================================================================

class ProviderSLARiskResponse(BaseModel):
    """Structured JSON contract expected from LLM provider."""
    risk_level: str = Field(description="low, medium, high, or critical")
    confidence: float = Field(ge=0.0, le=1.0)
    is_at_risk_of_breach: bool
    predicted_time_to_breach: Optional[str] = None
    risk_factors: List[str] = Field(min_length=1, max_length=10)
    recommended_action: str = Field(min_length=1, max_length=1000)
    escalation_recommended: bool
    escalation_urgency: str = Field(description="low, medium, high, or immediate")
    recommended_priority: str = Field(description="low, medium, high, or critical")
    recommended_team: str = Field(min_length=1, max_length=100)
    evidence: List[str] = Field(min_length=1, max_length=10)

    @field_validator("risk_factors", "evidence", mode="before")
    @classmethod
    def coerce_to_list(cls, value: object) -> object:
        if isinstance(value, str):
            lines = [line.strip("- *").strip() for line in value.split("\n") if line.strip()]
            return lines if lines else [value]
        return value


class AISLARiskAssessment(BaseModel):
    """Validated AI risk analysis and escalation recommendation."""
    recommendation_id: str
    risk_level: str  # low, medium, high, critical
    confidence: float
    confidence_level: str  # Low, Medium, High
    is_at_risk_of_breach: bool
    predicted_time_to_breach: Optional[str] = None
    risk_factors: List[str]
    recommended_action: str
    escalation_recommended: bool
    escalation_urgency: str  # low, medium, high, immediate
    recommended_priority: str
    recommended_team: str
    evidence: List[str]


class TicketAIRiskResponse(BaseModel):
    ticket_id: str
    ticket_number: str
    sla_metrics: TicketSLAMetrics
    ai_risk_assessment: AISLARiskAssessment


class EscalationDecisionRequest(BaseModel):
    recommendation_id: str = Field(min_length=1, max_length=36)
    apply_priority: bool = True
    note: Optional[str] = Field(None, max_length=500)


class EscalationDecisionResponse(BaseModel):
    recommendation_id: str
    decision: Literal["accepted", "rejected"]
    applied_priority: Optional[str] = None
    message: str
