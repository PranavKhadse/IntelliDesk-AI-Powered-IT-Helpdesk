"""AI-assisted ticket summarization and action insights service."""

import re
from typing import Any, Dict, List
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import ServiceUnavailableError, ValidationError
from app.models.comment import CommentType
from app.models.ticket import Ticket
from app.schemas.ai import AIRequest
from app.schemas.ai_summary import ProviderTicketSummary, TicketSummaryResponse
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


def build_ticket_summary_context(ticket: Ticket) -> Dict[str, Any]:
    """Build sanitized, public-only ticket context for ticket summarization."""
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

    history: List[Dict[str, str]] = []
    if ticket.audit_logs:
        for log in ticket.audit_logs:
            history.append({
                "action": log.action,
                "actor": log.actor.full_name if log.actor else "System",
                "timestamp": log.created_at.isoformat() if log.created_at else "",
            })

    return {
        "ticket_number": ticket.ticket_number or ticket.id,
        "title": sanitize_context_text(ticket.title),
        "description": sanitize_context_text(ticket.description),
        "status": ticket.status,
        "priority": ticket.priority,
        "category": ticket.category.name if ticket.category else "General",
        "customer_name": ticket.creator.full_name if ticket.creator else "Customer",
        "assigned_agent": ticket.assignee.full_name if ticket.assignee else "Unassigned",
        "public_comments": public_comments,
        "history": history,
    }


def generate_ticket_summary(ticket: Ticket, ai_service: AIService) -> TicketSummaryResponse:
    """Generate an AI ticket summary and action insights without modifying the ticket."""
    context = build_ticket_summary_context(ticket)

    prompt = (
        "You are an expert IT service desk analyst creating a comprehensive ticket summary and action insights for support staff (agents and admins). "
        "Analyze the provided ticket context strictly based on the supplied information. "
        "Rules: "
        "1. Ground all findings strictly in the provided ticket details, public comments, and history. Do not assume or invent facts, actions, policies, SLAs, refunds, resolutions, or guarantees. "
        "2. summary: A concise high-level overview of the ticket situation. "
        "3. customer_issue: The core problem or request reported by the customer. "
        "4. important_facts: Key factual points established from the ticket context (system versions, error messages, user environment, timelines). "
        "5. actions_taken: Specific troubleshooting actions, updates, or interventions already completed according to public comments or history. "
        "6. suggested_next_steps: Recommended actionable next steps for support agents to resolve or advance the ticket. "
        "7. missing_information: Explicitly list any critical details, logs, reproduction steps, or context not yet provided. If nothing is missing, return an empty list or clear note. "
        "8. risk_flags: Meaningful risks such as urgency, repeated customer contact, unresolved blocking issue, SLA breach danger, or missing critical information. "
        "9. confidence: A float score between 0.0 and 1.0 reflecting confidence in the assessment based on available data. "
        "Return ONLY a JSON object with: summary, customer_issue, important_facts, actions_taken, suggested_next_steps, missing_information, risk_flags, and confidence."
    )

    request = AIRequest(
        capability="ticket_summary",
        prompt=prompt,
        context=context,
        max_output_tokens=1200,
        response_format="json_object",
    )

    ai_response = ai_service.generate(request)
    if ai_response.status != "success" or not ai_response.content:
        raise ServiceUnavailableError("AI ticket summarization is currently unavailable. Please try again later.")

    try:
        provider_summary = ProviderTicketSummary.model_validate_json(ai_response.content)
    except (PydanticValidationError, ValueError):
        raise ValidationError("AI ticket summarization returned an invalid response.")

    return TicketSummaryResponse(
        summary=provider_summary.summary,
        customer_issue=provider_summary.customer_issue,
        important_facts=provider_summary.important_facts,
        actions_taken=provider_summary.actions_taken,
        suggested_next_steps=provider_summary.suggested_next_steps,
        missing_information=provider_summary.missing_information,
        risk_flags=provider_summary.risk_flags,
        confidence=provider_summary.confidence,
    )
