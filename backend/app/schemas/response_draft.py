from typing import List
from pydantic import BaseModel, Field


class ProviderResponseDraft(BaseModel):
    """Structured JSON contract expected from an AI provider for customer response drafts."""

    draft_response: str = Field(min_length=1)
    tone: str = Field(min_length=1, max_length=50)
    key_points: List[str] = Field(min_length=1, max_length=10)
    confidence: float = Field(ge=0, le=1)


class ResponseDraft(BaseModel):
    """Client-facing response draft representation."""

    draft_response: str
    tone: str
    key_points: List[str]
    confidence: float = Field(ge=0, le=1)
