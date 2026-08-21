from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field


class AIRequest(BaseModel):
    """Provider-neutral input for future IntelliDesk AI capabilities."""

    capability: str = Field(..., min_length=1, max_length=100)
    prompt: str = Field(..., min_length=1)
    context: Dict[str, Any] = Field(default_factory=dict)
    max_output_tokens: Optional[int] = Field(default=None, ge=1, le=4096)
    response_format: Literal["text", "json_object"] = "text"


class AIResponse(BaseModel):
    """Provider-neutral output that safely represents degraded operation."""

    content: Optional[str] = None
    status: Literal["success", "fallback"]
    used_fallback: bool
    error_code: Optional[Literal["AI_NOT_CONFIGURED", "AI_TIMEOUT", "AI_PROVIDER_ERROR"]] = None


class AIHealthResponse(BaseModel):
    """Sanitized availability status; deliberately excludes provider and credentials."""

    available: bool
    status: Literal["available", "unavailable"]
