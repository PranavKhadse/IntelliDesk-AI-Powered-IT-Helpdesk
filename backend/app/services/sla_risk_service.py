import json
import re
import hashlib
from typing import Dict, Any, Tuple
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.comment import CommentType
from app.models.audit_log import AuditLog, AuditAction
from app.models.user import User, UserRole
from app.schemas.ai import AIRequest
from app.schemas.ticket import TicketUpdate
from app.schemas.sla import (
    TicketSLAMetrics,
    ProviderSLARiskResponse,
    AISLARiskAssessment,
    TicketAIRiskResponse,
    EscalationDecisionRequest,
    EscalationDecisionResponse,
)
from app.services.ai_service import AIService
from app.services.sla_service import calculate_ticket_sla_metrics
from app.services.audit_service import log_ticket_event
from app.services.ticket_service import update_ticket
from app.core.exceptions import (
    NotFoundError,
    ForbiddenError,
    ValidationError,
    ServiceUnavailableError,
    ConflictError,
)


def sanitize_context_text(text: str) -> str:
    """Mask bearer tokens, passwords, and API keys before sending to AI."""
    if not text:
        return ""
    sanitized = re.sub(r'(?i)bearer\s+[a-zA-Z0-9\-_.]+', 'Bearer [REDACTED]', text)
    sanitized = re.sub(r'(?i)(password|secret|apikey|api_key)\s*[:=]\s*[^\s,]+', r'\1: [REDACTED]', sanitized)
    sanitized = re.sub(r'(?i)aiza[0-9a-zA-Z\\-_]{35}', '[REDACTED_API_KEY]', sanitized)
    return sanitized


def ticket_sla_fingerprint(ticket: Ticket) -> str:
    """Identify the ticket state and priority the recommendation was generated against."""
    source = f"{ticket.title}\n{ticket.description}\n{ticket.priority}\n{ticket.status}\n{ticket.category_id}".encode("utf-8")
    return hashlib.sha256(source).hexdigest()


def get_confidence_level(confidence: float) -> str:
    """Convert a 0.0-1.0 confidence score into a human-readable label."""
    if confidence >= 0.8:
        return "High"
    if confidence >= 0.5:
        return "Medium"
    return "Low"


def build_sla_risk_context(ticket: Ticket, metrics: TicketSLAMetrics) -> Dict[str, Any]:
    """Assemble structured context including system-calculated SLA metrics and public comments."""
    category_name = ticket.category.name if ticket.category else "Uncategorized"
    assignee_name = ticket.assignee.full_name if ticket.assignee else "Unassigned"

    # Only include PUBLIC comments - internal notes are strictly excluded
    public_comments = []
    for c in (ticket.comments or []):
        if c.comment_type == CommentType.PUBLIC:
            author_role = c.author.role if c.author else "user"
            public_comments.append({
                "author_role": author_role,
                "created_at": c.created_at.isoformat() if c.created_at else "",
                "content": sanitize_context_text(c.content)
            })

    return {
        "ticket": {
            "ticket_number": ticket.ticket_number,
            "title": sanitize_context_text(ticket.title),
            "description": sanitize_context_text(ticket.description),
            "status": ticket.status,
            "priority": ticket.priority,
            "category": category_name,
            "assignee": assignee_name,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else "",
        },
        "sla_ground_truth": {
            "policy_name": metrics.policy_name,
            "target_first_response_hours": metrics.target_first_response_hours,
            "target_resolution_hours": metrics.target_resolution_hours,
            "first_response_status": metrics.first_response_status.value,
            "first_response_elapsed_seconds": metrics.first_response_elapsed_seconds,
            "resolution_elapsed_seconds": metrics.resolution_elapsed_seconds,
            "remaining_seconds": metrics.remaining_seconds,
            "percentage_consumed": metrics.percentage_consumed,
            "current_sla_state": metrics.sla_state.value,
            "is_breached": metrics.is_breached,
            "is_at_risk": metrics.is_at_risk,
        },
        "public_comments": public_comments
    }


def generate_ticket_sla_risk(
    db: Session,
    ticket: Ticket,
    actor: User,
    ai_service: AIService
) -> TicketAIRiskResponse:
    """
    Generate AI-assisted SLA risk assessment and escalation recommendation.
    Enforces staff RBAC, grounds in system-calculated SLA facts, and stores recommendation in AuditLog.
    """
    if actor.role not in [UserRole.AGENT, UserRole.ADMIN]:
        raise ForbiddenError("Only support staff can generate AI SLA risk assessments.")

    # 1. Calculate ground-truth SLA state
    metrics = calculate_ticket_sla_metrics(db, ticket)
    context = build_sla_risk_context(ticket, metrics)

    # 2. Query AI Provider
    prompt = (
        "You are an expert IT Service Desk SLA Risk and Escalation Intelligence analyzer. "
        "Analyze the provided ticket details, public comments, and system-calculated SLA ground-truth metrics. "
        "Return ONLY a valid JSON object containing all of the following fields: "
        "1. risk_level: string, strictly one of: 'low', 'medium', 'high', 'critical'. "
        "2. confidence: float number between 0.0 and 1.0. "
        "3. is_at_risk_of_breach: boolean (true or false). "
        "4. predicted_time_to_breach: short string (e.g. 'Estimated 2 hours remaining') or null. "
        "5. risk_factors: array of 1 to 5 concise string bullet points based strictly on the ticket context and SLA progress. "
        "6. recommended_action: string, concise actionable advice for the support team. "
        "7. escalation_recommended: boolean (true or false indicating if immediate staff escalation is advised). "
        "8. escalation_urgency: string, strictly one of: 'low', 'medium', 'high', 'immediate'. "
        "9. recommended_priority: string, strictly one of: 'low', 'medium', 'high', 'critical'. "
        "10. recommended_team: string indicating appropriate escalation tier or team (e.g. 'Tier 2 Support', 'Infrastructure Engineering', 'Security Team'). "
        "11. evidence: array of 1 to 5 short exact string excerpts from the ticket description, comments, or SLA facts. "
        "Do NOT invent unsupported facts. All 11 keys are mandatory."
    )

    request = AIRequest(
        capability="sla_risk_assessment",
        prompt=prompt,
        context=context,
        max_output_tokens=1500,
        response_format="json_object",
    )

    ai_response = ai_service.generate(request)
    if ai_response.status != "success" or not ai_response.content:
        raise ServiceUnavailableError("AI SLA risk analysis is currently unavailable. Please try again later.")

    # 3. Validate JSON output
    try:
        provider_data = ProviderSLARiskResponse.model_validate_json(ai_response.content)
    except (PydanticValidationError, ValueError) as e:
        raise ValidationError(f"AI service returned an invalid SLA risk format: {str(e)}")

    valid_risk_levels = ["low", "medium", "high", "critical"]
    normalized_risk = provider_data.risk_level.lower()
    if normalized_risk not in valid_risk_levels:
        normalized_risk = "medium"

    valid_urgencies = ["low", "medium", "high", "immediate"]
    normalized_urgency = provider_data.escalation_urgency.lower()
    if normalized_urgency not in valid_urgencies:
        normalized_urgency = "medium"

    normalized_priority = provider_data.recommended_priority.lower()
    if normalized_priority not in TicketPriority.ALL:
        normalized_priority = ticket.priority

    confidence_level = get_confidence_level(provider_data.confidence)

    # 4. Store recommendation in AuditLog
    audit_payload = {
        "assessment": {
            "risk_level": normalized_risk,
            "confidence": provider_data.confidence,
            "confidence_level": confidence_level,
            "is_at_risk_of_breach": provider_data.is_at_risk_of_breach,
            "predicted_time_to_breach": provider_data.predicted_time_to_breach,
            "risk_factors": provider_data.risk_factors,
            "recommended_action": provider_data.recommended_action,
            "escalation_recommended": provider_data.escalation_recommended,
            "escalation_urgency": normalized_urgency,
            "recommended_priority": normalized_priority,
            "recommended_team": provider_data.recommended_team,
            "evidence": provider_data.evidence,
        },
        "sla_metrics": metrics.model_dump(mode="json"),
        "ticket_fingerprint": ticket_sla_fingerprint(ticket),
    }

    audit_entry = log_ticket_event(
        db=db,
        ticket_id=ticket.id,
        actor_id=actor.id,
        action=AuditAction.AI_SLA_RISK_ASSESSED,
        new_state=audit_payload
    )
    db.commit()

    assessment = AISLARiskAssessment(
        recommendation_id=audit_entry.id,
        risk_level=normalized_risk,
        confidence=provider_data.confidence,
        confidence_level=confidence_level,
        is_at_risk_of_breach=provider_data.is_at_risk_of_breach,
        predicted_time_to_breach=provider_data.predicted_time_to_breach,
        risk_factors=provider_data.risk_factors,
        recommended_action=provider_data.recommended_action,
        escalation_recommended=provider_data.escalation_recommended,
        escalation_urgency=normalized_urgency,
        recommended_priority=normalized_priority,
        recommended_team=provider_data.recommended_team,
        evidence=provider_data.evidence,
    )

    return TicketAIRiskResponse(
        ticket_id=ticket.id,
        ticket_number=ticket.ticket_number,
        sla_metrics=metrics,
        ai_risk_assessment=assessment,
    )


def _load_approvable_escalation_recommendation(
    db: Session,
    ticket: Ticket,
    actor: User,
    recommendation_id: str
) -> Tuple[Dict[str, Any], AuditLog]:
    """Verify recommendation exists, matches ticket state, is pending decision, and caller is staff."""
    if actor.role not in [UserRole.AGENT, UserRole.ADMIN]:
        raise ForbiddenError("Only support staff can approve or reject escalation recommendations.")

    log_entry = db.query(AuditLog).filter(
        AuditLog.id == recommendation_id,
        AuditLog.ticket_id == ticket.id,
        AuditLog.action == AuditAction.AI_SLA_RISK_ASSESSED,
    ).first()

    if not log_entry:
        raise NotFoundError("Escalation recommendation", recommendation_id)

    try:
        snapshot = json.loads(log_entry.new_state or "{}")
        assessment_data = snapshot["assessment"]
    except (KeyError, TypeError, ValueError):
        raise ConflictError("The stored escalation recommendation payload is invalid.")

    # Prevent stale approval if ticket details or priority changed
    if snapshot.get("ticket_fingerprint") != ticket_sla_fingerprint(ticket):
        raise ConflictError("The ticket priority or content changed after this escalation recommendation was generated.")

    # Prevent duplicate decisions
    prior_decisions = db.query(AuditLog).filter(
        AuditLog.ticket_id == ticket.id,
        AuditLog.action.in_([AuditAction.AI_ESCALATION_ACCEPTED, AuditAction.AI_ESCALATION_REJECTED]),
    ).all()

    for decision in prior_decisions:
        try:
            dec_prev = json.loads(decision.previous_state or "{}")
            if dec_prev.get("recommendation_id") == recommendation_id:
                raise ConflictError("This escalation recommendation has already been decided.")
        except (TypeError, ValueError):
            continue

    return assessment_data, log_entry


def approve_ticket_escalation(
    db: Session,
    ticket: Ticket,
    actor: User,
    req: EscalationDecisionRequest
) -> EscalationDecisionResponse:
    """Approve an AI escalation recommendation, apply supported priority updates, and record audit entry."""
    assessment_data, _ = _load_approvable_escalation_recommendation(db, ticket, actor, req.recommendation_id)

    applied_priority = None
    if req.apply_priority:
        rec_priority = assessment_data.get("recommended_priority")
        if rec_priority and rec_priority in TicketPriority.ALL and rec_priority != ticket.priority:
            update_ticket(
                db=db,
                ticket_id=ticket.id,
                req=TicketUpdate(priority=rec_priority),
                actor=actor
            )
            applied_priority = rec_priority

    log_ticket_event(
        db=db,
        ticket_id=ticket.id,
        actor_id=actor.id,
        action=AuditAction.AI_ESCALATION_ACCEPTED,
        previous_state={"recommendation_id": req.recommendation_id},
        new_state={
            "decision": "accepted",
            "applied_priority": applied_priority,
            "assessment": assessment_data,
            "note": req.note,
        }
    )
    db.commit()

    msg = f"Escalation recommendation accepted by {actor.full_name}."
    if applied_priority:
        msg += f" Ticket priority updated to {applied_priority.upper()}."

    return EscalationDecisionResponse(
        recommendation_id=req.recommendation_id,
        decision="accepted",
        applied_priority=applied_priority,
        message=msg
    )


def reject_ticket_escalation(
    db: Session,
    ticket: Ticket,
    actor: User,
    req: EscalationDecisionRequest
) -> EscalationDecisionResponse:
    """Reject an AI escalation recommendation without mutating the ticket and record audit entry."""
    assessment_data, _ = _load_approvable_escalation_recommendation(db, ticket, actor, req.recommendation_id)

    log_ticket_event(
        db=db,
        ticket_id=ticket.id,
        actor_id=actor.id,
        action=AuditAction.AI_ESCALATION_REJECTED,
        previous_state={"recommendation_id": req.recommendation_id},
        new_state={
            "decision": "rejected",
            "assessment": assessment_data,
            "note": req.note,
        }
    )
    db.commit()

    return EscalationDecisionResponse(
        recommendation_id=req.recommendation_id,
        decision="rejected",
        applied_priority=None,
        message=f"Escalation recommendation rejected by {actor.full_name}."
    )
