"""AI-assisted customer response drafting service."""

import re
from typing import Any, Dict, List
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import ServiceUnavailableError, ValidationError
from app.models.comment import CommentType
from app.models.ticket import Ticket
from app.schemas.ai import AIRequest
from app.schemas.response_draft import ProviderResponseDraft, ResponseDraft
from app.services.ai_service import AIService


def sanitize_context_text(text: str) -> str:
    """Mask credentials, bearer tokens, API keys, or secrets before sending to AI."""
    if not text:
        return ""
    # Redact common secret and token patterns
    scrubbed = re.sub(
        r"(?i)\b(bearer\s+[a-zA-Z0-9_\-\.]+)",
        "Bearer [REDACTED]",
        text,
    )
    scrubbed = re.sub(
        r"(?i)\b(password|passwd|secret|api_key|access_token|private_key)\s*[:=]\s*\S+",
        r"\1: [REDACTED]",
        scrubbed,
    )
    return scrubbed


def build_response_draft_context(ticket: Ticket) -> Dict[str, Any]:
    """Build sanitized, public-only ticket context for response drafting."""
    public_comments: List[Dict[str, str]] = []
    if ticket.comments:
        for comment in ticket.comments:
            # Strictly exclude internal notes and non-public comments
            if comment.comment_type == CommentType.PUBLIC:
                public_comments.append({
                    "author": comment.author.full_name if comment.author else "Support Staff",
                    "content": sanitize_context_text(comment.content),
                    "created_at": comment.created_at.isoformat() if comment.created_at else "",
                })

    return {
        "ticket_number": ticket.ticket_number or ticket.id,
        "title": sanitize_context_text(ticket.title),
        "description": sanitize_context_text(ticket.description),
        "status": ticket.status,
        "priority": ticket.priority,
        "category": ticket.category.name if ticket.category else "General",
        "customer_name": ticket.creator.full_name if ticket.creator else "Customer",
        "public_comments": public_comments,
    }


def generate_response_draft(ticket: Ticket, ai_service: AIService) -> ResponseDraft:
    """Generate an AI-assisted customer response draft without modifying the ticket."""
    context = build_response_draft_context(ticket)

    prompt = (
        "You are an IT helpdesk assistant drafting a professional customer-facing response on behalf of support staff. "
        "Draft a clear, empathetic, and concise response addressed directly to the customer based strictly on the ticket context. "
        "Rules: "
        "1. The response is a DRAFT and must be addressed directly to the customer. "
        "2. Do not claim that an action has been completed unless explicitly confirmed in the ticket description or public comments. "
        "3. Do not invent facts, troubleshooting steps not supported by context, policies, refunds, SLAs, or guarantees. "
        "4. If essential information is missing, politely ask the customer for the specific details needed. "
        "5. Return ONLY a JSON object with draft_response, tone, key_points, and confidence (a float from 0 to 1)."
    )

    request = AIRequest(
        capability="response_draft",
        prompt=prompt,
        context=context,
        max_output_tokens=800,
        response_format="json_object",
    )

    ai_response = ai_service.generate(request)
    if ai_response.status != "success" or not ai_response.content:
        raise ServiceUnavailableError("AI response drafting is currently unavailable. Please try again later.")

    try:
        provider_draft = ProviderResponseDraft.model_validate_json(ai_response.content)
    except (PydanticValidationError, ValueError):
        raise ValidationError("AI response drafting returned an invalid response.")

    return ResponseDraft(
        draft_response=provider_draft.draft_response,
        tone=provider_draft.tone,
        key_points=provider_draft.key_points,
        confidence=provider_draft.confidence,
    )
