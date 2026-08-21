"""Recommendation-only ticket triage built on the shared AI service."""

import json
import hashlib
from typing import Iterable

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ServiceUnavailableError, ValidationError
from app.models.audit_log import AuditAction, AuditLog
from app.models.ticket import Category, Ticket, TicketPriority
from app.models.user import User, UserRole
from app.schemas.ai import AIRequest
from app.schemas.ticket import TicketUpdate
from app.schemas.triage import (
    ProviderTriageRecommendation,
    TicketTriageRecommendation,
    TicketTriageInput,
    TicketTriageRecommendationBase,
)
from app.services.ai_service import AIService
from app.services.audit_service import log_ticket_event
from app.services.ticket_service import update_ticket


def build_ticket_triage_input(
    ticket: Ticket,
    categories: Iterable[str],
    teams: Iterable[str],
) -> TicketTriageInput:
    return TicketTriageInput(
        title=ticket.title,
        description=ticket.description,
        available_categories=sorted(set(categories)),
        valid_priorities=TicketPriority.ALL,
        available_teams=sorted(set(teams)) or ["Unassigned"],
    )


def ticket_triage_fingerprint(ticket: Ticket) -> str:
    """Identify the ticket content a recommendation was generated from."""
    source = f"{ticket.title}\n{ticket.description}".encode("utf-8")
    return hashlib.sha256(source).hexdigest()


def get_confidence_level(confidence: float) -> str:
    """Convert a 0-1 AI confidence score into a consistent human-readable level."""
    if confidence >= 0.75:
        return "High"
    if confidence >= 0.4:
        return "Medium"
    return "Low"


def generate_ticket_triage(
    triage_input: TicketTriageInput,
    ai_service: AIService,
) -> TicketTriageRecommendationBase:
    request = AIRequest(
        capability="ticket_triage",
        prompt=(
            "Return only a JSON object with category, priority, urgency, impact, suggested_team, "
            "confidence, evidence, priority_evidence, category_evidence, and urgency_impact_evidence. "
            "confidence must be a number from 0 to 1. Each evidence field must contain one to three exact, "
            "short excerpts from the ticket title or description. Do not infer facts not stated in the ticket."
        ),
        context=triage_input.model_dump(),
        max_output_tokens=500,
        response_format="json_object",
    )
    ai_response = ai_service.generate(request)
    if ai_response.status != "success" or not ai_response.content:
        raise ServiceUnavailableError("AI triage is currently unavailable. Please try again later.")

    try:
        provider_recommendation = ProviderTriageRecommendation.model_validate_json(ai_response.content)
    except (PydanticValidationError, ValueError):
        raise ValidationError("AI triage returned an invalid recommendation.")

    if provider_recommendation.category not in triage_input.available_categories:
        raise ValidationError("AI triage returned an unavailable category.")
    if provider_recommendation.priority not in triage_input.valid_priorities:
        raise ValidationError("AI triage returned an invalid priority.")
    if provider_recommendation.suggested_team not in triage_input.available_teams:
        raise ValidationError("AI triage returned an unavailable team.")

    source_text = f"{triage_input.title}\n{triage_input.description}".casefold()
    evidence_groups = {
        "evidence": provider_recommendation.evidence,
        "priority_evidence": provider_recommendation.priority_evidence,
        "category_evidence": provider_recommendation.category_evidence,
        "urgency_impact_evidence": provider_recommendation.urgency_impact_evidence,
    }
    normalized_evidence = {
        name: [excerpt.strip() for excerpt in excerpts]
        for name, excerpts in evidence_groups.items()
    }
    if any(
        not excerpt or excerpt.casefold() not in source_text
        for excerpts in normalized_evidence.values()
        for excerpt in excerpts
    ):
        raise ValidationError("AI triage explanation must be grounded in the ticket content.")

    evidence = normalized_evidence["evidence"]
    confidence_level = get_confidence_level(provider_recommendation.confidence)
    return TicketTriageRecommendationBase(
        category=provider_recommendation.category,
        priority=provider_recommendation.priority,
        urgency=provider_recommendation.urgency,
        impact=provider_recommendation.impact,
        suggested_team=provider_recommendation.suggested_team,
        confidence=provider_recommendation.confidence,
        confidence_level=confidence_level,
        evidence=evidence,
        priority_reason="; ".join(normalized_evidence["priority_evidence"]),
        category_reason="; ".join(normalized_evidence["category_evidence"]),
        urgency_impact_reason="; ".join(normalized_evidence["urgency_impact_evidence"]),
        explanation="; ".join(evidence),
    )


def store_ticket_triage(
    db: Session,
    ticket: Ticket,
    actor: User,
    recommendation: TicketTriageRecommendationBase,
) -> TicketTriageRecommendation:
    audit_log = log_ticket_event(
        db=db,
        ticket_id=ticket.id,
        actor_id=actor.id,
        action=AuditAction.AI_TRIAGED,
        new_state={
            "recommendation": recommendation.model_dump(mode="json"),
            "ticket_fingerprint": ticket_triage_fingerprint(ticket),
        },
    )
    db.commit()
    return TicketTriageRecommendation(
        recommendation_id=audit_log.id,
        **recommendation.model_dump(),
    )


def approve_ticket_triage(
    db: Session,
    ticket: Ticket,
    actor: User,
    recommendation_id: str,
) -> None:
    recommendation, _ = _load_approvable_recommendation(db, ticket, actor, recommendation_id)
    category = db.query(Category).filter(
        Category.name == recommendation.category,
        Category.is_active == True,
    ).first()
    if not category or recommendation.priority not in TicketPriority.ALL:
        raise ConflictError("The AI recommendation is no longer valid.")

    # Suggested team is informational: assignment requires a specific valid agent selected by staff.
    update_ticket(
        db=db,
        ticket_id=ticket.id,
        req=TicketUpdate(category_id=category.id, priority=recommendation.priority),
        actor=actor,
    )
    log_ticket_event(
        db=db,
        ticket_id=ticket.id,
        actor_id=actor.id,
        action=AuditAction.AI_RECOMMENDATION_ACCEPTED,
        previous_state={"recommendation_id": recommendation_id},
        new_state={
            "decision": "accepted",
            "recommendation": recommendation.model_dump(mode="json"),
            "applied_fields": ["category", "priority"],
        },
    )
    db.commit()


def reject_ticket_triage(
    db: Session,
    ticket: Ticket,
    actor: User,
    recommendation_id: str,
) -> None:
    recommendation, _ = _load_approvable_recommendation(db, ticket, actor, recommendation_id)
    log_ticket_event(
        db=db,
        ticket_id=ticket.id,
        actor_id=actor.id,
        action=AuditAction.AI_RECOMMENDATION_REJECTED,
        previous_state={"recommendation_id": recommendation_id},
        new_state={
            "decision": "rejected",
            "recommendation": recommendation.model_dump(mode="json"),
        },
    )
    db.commit()


def _load_approvable_recommendation(
    db: Session,
    ticket: Ticket,
    actor: User,
    recommendation_id: str,
) -> tuple[TicketTriageRecommendation, AuditLog]:
    if actor.role not in [UserRole.AGENT, UserRole.ADMIN]:
        raise ForbiddenError("Only support staff can decide on AI recommendations.")

    recommendation_log = db.query(AuditLog).filter(
        AuditLog.id == recommendation_id,
        AuditLog.ticket_id == ticket.id,
        AuditLog.action == AuditAction.AI_TRIAGED,
    ).first()
    if not recommendation_log:
        raise NotFoundError("AI recommendation", recommendation_id)

    try:
        snapshot = json.loads(recommendation_log.new_state or "{}")
        recommendation = TicketTriageRecommendation(
            recommendation_id=recommendation_id,
            **snapshot["recommendation"],
        )
    except (KeyError, TypeError, ValueError, PydanticValidationError):
        raise ConflictError("The stored AI recommendation is invalid.")

    if snapshot.get("ticket_fingerprint") != ticket_triage_fingerprint(ticket):
        raise ConflictError("The ticket content changed after this AI recommendation was generated.")

    prior_decisions = db.query(AuditLog).filter(
        AuditLog.ticket_id == ticket.id,
        AuditLog.action.in_([AuditAction.AI_RECOMMENDATION_ACCEPTED, AuditAction.AI_RECOMMENDATION_REJECTED]),
    ).all()
    for decision in prior_decisions:
        try:
            if json.loads(decision.previous_state or "{}").get("recommendation_id") == recommendation_id:
                raise ConflictError("This AI recommendation has already been decided.")
        except (TypeError, ValueError):
            continue

    return recommendation, recommendation_log
