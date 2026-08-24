"""AI Knowledge Base Grounding service for verified, source-attributed IT recommendations."""

import re
from typing import Any, Dict, List
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.core.exceptions import ServiceUnavailableError, ValidationError
from app.models.comment import CommentType
from app.models.ticket import Ticket
from app.schemas.ai import AIRequest
from app.schemas.ai_grounding import (
    GroundingStatus,
    GroundedArticleReference,
    ProviderGroundingResult,
    TicketGroundingResponse,
)
from app.services.ai_service import AIService
from app.services.kb_service import get_relevant_articles_for_ticket


def sanitize_context_text(text: str) -> str:
    """Mask credentials, bearer tokens, API keys, or secrets before sending to AI."""
    if not text:
        return ""
    # Redact bearer tokens
    scrubbed = re.sub(
        r"(?i)\b(bearer\s+[a-zA-Z0-9_\-\.]+)",
        "Bearer [REDACTED]",
        text,
    )
    # Redact passwords, secrets, API keys
    scrubbed = re.sub(
        r"(?i)\b(password|passwd|secret|api_key|access_token|private_key)\s*[:=]\s*\S+",
        r"\1: [REDACTED]",
        scrubbed,
    )
    return scrubbed


def build_grounding_context(ticket: Ticket, matched_articles: List[GroundedArticleReference]) -> Dict[str, Any]:
    """Build sanitized, public-only ticket context and verified KB articles for AI grounding."""
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

    articles_context: List[Dict[str, Any]] = []
    for ref in matched_articles:
        articles_context.append({
            "article_id": ref.article_id,
            "slug": ref.slug,
            "title": sanitize_context_text(ref.title),
            "category": ref.category or "General",
            "relevance_score": ref.relevance_score,
            "content_snippet": sanitize_context_text(ref.snippet),
        })

    return {
        "ticket_number": ticket.ticket_number or ticket.id,
        "title": sanitize_context_text(ticket.title),
        "description": sanitize_context_text(ticket.description),
        "status": ticket.status,
        "priority": ticket.priority,
        "category": ticket.category.name if ticket.category else "General",
        "public_comments": public_comments,
        "verified_kb_articles": articles_context,
    }


def generate_grounded_ticket_recommendation(
    ticket: Ticket,
    db: Session,
    ai_service: AIService,
) -> TicketGroundingResponse:
    """
    Generate an AI recommendation strictly grounded in verified published KB articles.
    Does not modify ticket state.
    """
    matched_articles = get_relevant_articles_for_ticket(db, ticket, limit=3, min_score=0.25)

    # If no KB articles match the relevance threshold, return safe deterministic no-match
    if not matched_articles:
        return TicketGroundingResponse(
            ticket_id=ticket.id,
            ticket_number=ticket.ticket_number,
            grounding_status=GroundingStatus.NO_MATCH,
            recommendation=(
                "No reliable knowledge base articles match this ticket's issue. "
                "Support staff should proceed with standard manual investigation and troubleshooting."
            ),
            key_points=[
                "No matching published KB articles found for this issue",
                "Proceed with manual ticket diagnosis",
            ],
            sources=[],
            confidence=0.0,
            reasoning="No published KB articles met the minimum relevance threshold for the ticket description.",
            no_match_reason="No reliable knowledge base articles match this ticket's symptoms.",
        )

    context = build_grounding_context(ticket, matched_articles)

    prompt = (
        "You are an expert IT service desk AI assistant. Your job is to provide a grounded recommendation and troubleshooting steps "
        "for support staff based STRICTLY on the provided verified knowledge base articles. "
        "Rules: "
        "1. You must ground your recommendation ONLY in the provided verified_kb_articles and ticket context. "
        "2. Do NOT invent procedures, policies, tools, credentials, or URLs not found in the verified articles. "
        "3. grounding_status MUST be one of: "
        "   - 'grounded': The verified KB articles directly and fully address the ticket problem. "
        "   - 'partially_grounded': The verified KB articles partially address the issue but additional manual steps are needed. "
        "   - 'no_match': The verified articles do not actually solve the issue described. "
        "4. In cited_article_ids, list the exact article_id values of all articles from verified_kb_articles that you used. "
        "5. In grounded_response, write clear, actionable guidance or steps for support staff, referencing the knowledge base. "
        "6. In key_points, provide 2-5 concise bullet points summarizing the solution or findings. "
        "7. In confidence, provide a float between 0.0 and 1.0 reflecting your confidence in the KB match. "
        "8. In reasoning, briefly explain why this grounding status and articles were selected. "
        "Return ONLY a JSON object with: grounding_status, grounded_response, cited_article_ids, key_points, confidence, reasoning."
    )

    request = AIRequest(
        capability="ticket_grounding",
        prompt=prompt,
        context=context,
        max_output_tokens=1000,
        response_format="json_object",
    )

    ai_response = ai_service.generate(request)
    if ai_response.status != "success" or not ai_response.content:
        raise ServiceUnavailableError("AI knowledge base grounding is currently unavailable. Please try again later.")

    try:
        provider_result = ProviderGroundingResult.model_validate_json(ai_response.content)
    except (PydanticValidationError, ValueError):
        raise ValidationError("AI knowledge base grounding returned an invalid response.")

    # Match cited article IDs to our grounded article references
    cited_id_set = set(provider_result.cited_article_ids)
    cited_sources = [a for a in matched_articles if a.article_id in cited_id_set]

    # If the provider cited none but matched articles exist and grounding is positive, fallback to all matched
    if not cited_sources and provider_result.grounding_status != GroundingStatus.NO_MATCH:
        cited_sources = matched_articles

    # If grounding status is no_match, clear sources
    if provider_result.grounding_status == GroundingStatus.NO_MATCH:
        cited_sources = []

    return TicketGroundingResponse(
        ticket_id=ticket.id,
        ticket_number=ticket.ticket_number,
        grounding_status=provider_result.grounding_status,
        recommendation=provider_result.grounded_response,
        key_points=provider_result.key_points,
        sources=cited_sources,
        confidence=provider_result.confidence,
        reasoning=provider_result.reasoning,
        no_match_reason="No reliable knowledge base articles match this ticket's symptoms." if provider_result.grounding_status == GroundingStatus.NO_MATCH else None,
    )
