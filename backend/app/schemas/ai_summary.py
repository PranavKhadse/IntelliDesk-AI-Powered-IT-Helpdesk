from typing import List
from pydantic import BaseModel, Field


class ProviderTicketSummary(BaseModel):
    """Structured JSON contract expected from an AI provider for ticket summaries."""

    summary: str = Field(min_length=1)
    customer_issue: str = Field(min_length=1)
    important_facts: List[str] = Field(default_factory=list)
    actions_taken: List[str] = Field(default_factory=list)
    suggested_next_steps: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class TicketSummaryResponse(BaseModel):
    """Client-facing ticket summary and action insights representation."""

    summary: str
    customer_issue: str
    important_facts: List[str]
    actions_taken: List[str]
    suggested_next_steps: List[str]
    missing_information: List[str]
    risk_flags: List[str]
    confidence: float = Field(ge=0.0, le=1.0)
