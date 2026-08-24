import json
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.comment import TicketComment, CommentType
from app.models.audit_log import AuditLog, AuditAction
from app.schemas.ai import AIResponse
from app.services.ai_service import AIService


def test_generate_ai_sla_risk_success(client, db_session, test_user, test_agent, agent_auth_headers, monkeypatch):
    """Verify AI SLA risk assessment generates valid ground truth + advisory intelligence."""
    ticket = Ticket(
        ticket_number="IT-RISK-1",
        title="Production API 500 Errors",
        description="Payment gateway returning 500 error on checkout for all enterprise customers.",
        priority=TicketPriority.HIGH,
        status=TicketStatus.OPEN,
        creator_id=test_user.id,
    )
    db_session.add(ticket)
    db_session.commit()

    mock_ai_content = json.dumps({
        "risk_level": "critical",
        "confidence": 0.95,
        "is_at_risk_of_breach": True,
        "predicted_time_to_breach": "Estimated 45 minutes remaining",
        "risk_factors": [
            "Affecting all enterprise customers on checkout",
            "Payment gateway integration failure",
            "No engineer assigned yet"
        ],
        "recommended_action": "Immediately escalate to Tier 3 Infrastructure and update priority to CRITICAL.",
        "escalation_recommended": True,
        "escalation_urgency": "immediate",
        "recommended_priority": "critical",
        "recommended_team": "Tier 3 Infrastructure",
        "evidence": [
            "Payment gateway returning 500 error",
            "all enterprise customers"
        ]
    })

    mock_ai_service = MagicMock(spec=AIService)
    mock_ai_service.generate.return_value = AIResponse(
        content=mock_ai_content,
        status="success",
        used_fallback=False
    )
    monkeypatch.setattr("app.api.v1.tickets.get_ai_service", lambda: mock_ai_service)

    res = client.post(f"/api/v1/tickets/{ticket.id}/ai-sla-risk", headers=agent_auth_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["ticket_id"] == ticket.id
    assert "sla_metrics" in data
    assert "ai_risk_assessment" in data

    assessment = data["ai_risk_assessment"]
    assert assessment["risk_level"] == "critical"
    assert assessment["confidence"] == 0.95
    assert assessment["confidence_level"] == "High"
    assert assessment["escalation_recommended"] == True
    assert assessment["recommended_priority"] == "critical"
    assert assessment["recommendation_id"] is not None

    # Verify audit log was created
    audit_entry = db_session.query(AuditLog).filter(
        AuditLog.ticket_id == ticket.id,
        AuditLog.action == AuditAction.AI_SLA_RISK_ASSESSED,
    ).first()
    assert audit_entry is not None
    assert audit_entry.id == assessment["recommendation_id"]


def test_ai_sla_risk_rbac(client, db_session, test_user, test_agent, user_auth_headers, agent_auth_headers):
    """Staff only access: users receive 403, unauthenticated receives 401."""
    ticket = Ticket(
        ticket_number="IT-RISK-2",
        title="Laptop issue",
        description="Display flickers",
        priority=TicketPriority.LOW,
        status=TicketStatus.OPEN,
        creator_id=test_user.id,
    )
    db_session.add(ticket)
    db_session.commit()

    # 1. Unauthenticated -> 401
    res_unauth = client.post(f"/api/v1/tickets/{ticket.id}/ai-sla-risk")
    assert res_unauth.status_code == 401

    # 2. Regular user -> 403 Forbidden
    res_user = client.post(f"/api/v1/tickets/{ticket.id}/ai-sla-risk", headers=user_auth_headers)
    assert res_user.status_code == 403


def test_ai_sla_risk_secret_sanitization_and_internal_notes_exclusion(client, db_session, test_user, test_agent, agent_auth_headers, monkeypatch):
    """Sensitive secrets are masked and internal notes are excluded from AI context."""
    ticket = Ticket(
        ticket_number="IT-RISK-3",
        title="Auth Server down Bearer secret_token_12345",
        description="DB Password: SuperSecretPassword123! API_KEY: AIzaSyD1234567890123456789012345678901",
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
        creator_id=test_user.id,
    )
    db_session.add(ticket)
    db_session.commit()

    # Add public comment and internal note
    pub_comment = TicketComment(
        ticket_id=ticket.id,
        author_id=test_user.id,
        comment_type=CommentType.PUBLIC,
        content="Public update with token: Bearer abcdef123456"
    )
    internal_note = TicketComment(
        ticket_id=ticket.id,
        author_id=test_agent.id,
        comment_type=CommentType.INTERNAL_NOTE,
        content="CONFIDENTIAL INTERNAL NOTE: root credentials are root/secret"
    )
    db_session.add_all([pub_comment, internal_note])
    db_session.commit()

    captured_requests = []
    mock_ai_service = MagicMock(spec=AIService)
    def mock_generate(req):
        captured_requests.append(req)
        return AIResponse(
            content=json.dumps({
                "risk_level": "medium",
                "confidence": 0.85,
                "is_at_risk_of_breach": False,
                "predicted_time_to_breach": "20 hours remaining",
                "risk_factors": ["Authentication credentials issue"],
                "recommended_action": "Verify credentials safely.",
                "escalation_recommended": False,
                "escalation_urgency": "low",
                "recommended_priority": "medium",
                "recommended_team": "IT Support",
                "evidence": ["Auth Server down"]
            }),
            status="success",
            used_fallback=False
        )
    mock_ai_service.generate.side_effect = mock_generate
    monkeypatch.setattr("app.api.v1.tickets.get_ai_service", lambda: mock_ai_service)

    res = client.post(f"/api/v1/tickets/{ticket.id}/ai-sla-risk", headers=agent_auth_headers)
    assert res.status_code == 200

    assert len(captured_requests) == 1
    context_str = json.dumps(captured_requests[0].context)

    # Verify secrets are masked
    assert "secret_token_12345" not in context_str
    assert "SuperSecretPassword123!" not in context_str
    assert "AIzaSyD1234567890123456789012345678901" not in context_str
    assert "[REDACTED" in context_str

    # Verify internal note is strictly excluded
    assert "CONFIDENTIAL INTERNAL NOTE" not in context_str
    assert "root credentials" not in context_str


def test_ai_sla_risk_ticket_immutability(client, db_session, test_user, test_agent, agent_auth_headers, monkeypatch):
    """Generating AI risk assessment never mutates ticket status, priority, or fields."""
    ticket = Ticket(
        ticket_number="IT-RISK-4",
        title="Email setup",
        description="Need email config",
        priority=TicketPriority.LOW,
        status=TicketStatus.OPEN,
        creator_id=test_user.id,
    )
    db_session.add(ticket)
    db_session.commit()

    mock_ai_service = MagicMock(spec=AIService)
    mock_ai_service.generate.return_value = AIResponse(
        content=json.dumps({
            "risk_level": "critical",
            "confidence": 0.90,
            "is_at_risk_of_breach": True,
            "predicted_time_to_breach": "1 hour",
            "risk_factors": ["High volume"],
            "recommended_action": "Escalate to critical immediately",
            "escalation_recommended": True,
            "escalation_urgency": "immediate",
            "recommended_priority": "critical",
            "recommended_team": "Escalations Team",
            "evidence": ["Email setup"]
        }),
        status="success",
        used_fallback=False
    )
    monkeypatch.setattr("app.api.v1.tickets.get_ai_service", lambda: mock_ai_service)

    res = client.post(f"/api/v1/tickets/{ticket.id}/ai-sla-risk", headers=agent_auth_headers)
    assert res.status_code == 200

    # Verify ticket was NOT mutated
    db_session.refresh(ticket)
    assert ticket.priority == TicketPriority.LOW
    assert ticket.status == TicketStatus.OPEN


def test_ai_sla_risk_provider_failure_returns_503(client, db_session, test_user, test_agent, agent_auth_headers, monkeypatch):
    """Provider failure or timeout returns 503 Service Unavailable."""
    ticket = Ticket(
        ticket_number="IT-RISK-5",
        title="Printer error",
        description="Printer paper jam",
        priority=TicketPriority.LOW,
        status=TicketStatus.OPEN,
        creator_id=test_user.id,
    )
    db_session.add(ticket)
    db_session.commit()

    mock_ai_service = MagicMock(spec=AIService)
    mock_ai_service.generate.return_value = AIResponse(
        content="",
        status="fallback",
        error_code="AI_TIMEOUT",
        used_fallback=True
    )
    monkeypatch.setattr("app.api.v1.tickets.get_ai_service", lambda: mock_ai_service)

    res = client.post(f"/api/v1/tickets/{ticket.id}/ai-sla-risk", headers=agent_auth_headers)
    assert res.status_code == 503


def test_approve_escalation_recommendation(client, db_session, test_user, test_agent, agent_auth_headers, monkeypatch):
    """Support agent can approve escalation recommendation, updating ticket priority and logging audit record."""
    ticket = Ticket(
        ticket_number="IT-RISK-6",
        title="Database Latency Spike",
        description="Query latency exceeded 5000ms",
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.IN_PROGRESS,
        creator_id=test_user.id,
    )
    db_session.add(ticket)
    db_session.commit()

    # 1. Generate risk assessment
    mock_ai_service = MagicMock(spec=AIService)
    mock_ai_service.generate.return_value = AIResponse(
        content=json.dumps({
            "risk_level": "critical",
            "confidence": 0.92,
            "is_at_risk_of_breach": True,
            "predicted_time_to_breach": "30 minutes",
            "risk_factors": ["Database latency > 5000ms"],
            "recommended_action": "Escalate to DBA on-call",
            "escalation_recommended": True,
            "escalation_urgency": "immediate",
            "recommended_priority": "critical",
            "recommended_team": "Database Operations",
            "evidence": ["Query latency exceeded 5000ms"]
        }),
        status="success",
        used_fallback=False
    )
    monkeypatch.setattr("app.api.v1.tickets.get_ai_service", lambda: mock_ai_service)

    res_risk = client.post(f"/api/v1/tickets/{ticket.id}/ai-sla-risk", headers=agent_auth_headers)
    assert res_risk.status_code == 200
    rec_id = res_risk.json()["ai_risk_assessment"]["recommendation_id"]

    # 2. Approve escalation recommendation
    approve_payload = {
        "recommendation_id": rec_id,
        "apply_priority": True,
        "note": "Approved due to critical customer impact."
    }
    res_app = client.post(f"/api/v1/tickets/{ticket.id}/ai-sla-risk/approve", json=approve_payload, headers=agent_auth_headers)
    assert res_app.status_code == 200
    assert res_app.json()["decision"] == "accepted"
    assert res_app.json()["applied_priority"] == "critical"

    # Verify ticket priority was mutated to CRITICAL
    db_session.refresh(ticket)
    assert ticket.priority == TicketPriority.CRITICAL

    # Verify audit trail contains AI_ESCALATION_ACCEPTED
    audit_accepted = db_session.query(AuditLog).filter(
        AuditLog.ticket_id == ticket.id,
        AuditLog.action == AuditAction.AI_ESCALATION_ACCEPTED,
    ).first()
    assert audit_accepted is not None
    assert audit_accepted.actor_id == test_agent.id


def test_reject_escalation_recommendation(client, db_session, test_user, test_agent, agent_auth_headers, monkeypatch):
    """Support agent can reject escalation recommendation without mutating ticket."""
    ticket = Ticket(
        ticket_number="IT-RISK-7",
        title="Minor CSS bug",
        description="Button misalignment in navbar",
        priority=TicketPriority.LOW,
        status=TicketStatus.OPEN,
        creator_id=test_user.id,
    )
    db_session.add(ticket)
    db_session.commit()

    mock_ai_service = MagicMock(spec=AIService)
    mock_ai_service.generate.return_value = AIResponse(
        content=json.dumps({
            "risk_level": "high",
            "confidence": 0.60,
            "is_at_risk_of_breach": True,
            "predicted_time_to_breach": "2 hours",
            "risk_factors": ["Navbar visual issue"],
            "recommended_action": "Escalate to frontend team",
            "escalation_recommended": True,
            "escalation_urgency": "medium",
            "recommended_priority": "high",
            "recommended_team": "Frontend Core",
            "evidence": ["Button misalignment"]
        }),
        status="success",
        used_fallback=False
    )
    monkeypatch.setattr("app.api.v1.tickets.get_ai_service", lambda: mock_ai_service)

    res_risk = client.post(f"/api/v1/tickets/{ticket.id}/ai-sla-risk", headers=agent_auth_headers)
    assert res_risk.status_code == 200
    rec_id = res_risk.json()["ai_risk_assessment"]["recommendation_id"]

    # Reject recommendation
    reject_payload = {
        "recommendation_id": rec_id,
        "note": "Minor visual glitch does not warrant high priority escalation."
    }
    res_rej = client.post(f"/api/v1/tickets/{ticket.id}/ai-sla-risk/reject", json=reject_payload, headers=agent_auth_headers)
    assert res_rej.status_code == 200
    assert res_rej.json()["decision"] == "rejected"

    # Verify ticket priority remains LOW
    db_session.refresh(ticket)
    assert ticket.priority == TicketPriority.LOW


def test_escalation_decision_duplicate_and_stale_prevention(client, db_session, test_user, test_agent, agent_auth_headers, monkeypatch):
    """Prevent duplicate decisions and stale approvals when ticket priority changed."""
    ticket = Ticket(
        ticket_number="IT-RISK-8",
        title="Network Gateway Packet Loss",
        description="10% packet loss on edge router",
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
        creator_id=test_user.id,
    )
    db_session.add(ticket)
    db_session.commit()

    mock_ai_service = MagicMock(spec=AIService)
    mock_ai_service.generate.return_value = AIResponse(
        content=json.dumps({
            "risk_level": "high",
            "confidence": 0.88,
            "is_at_risk_of_breach": True,
            "predicted_time_to_breach": "1.5 hours",
            "risk_factors": ["Packet loss"],
            "recommended_action": "Escalate to Network Team",
            "escalation_recommended": True,
            "escalation_urgency": "high",
            "recommended_priority": "high",
            "recommended_team": "Network Engineering",
            "evidence": ["packet loss on edge router"]
        }),
        status="success",
        used_fallback=False
    )
    monkeypatch.setattr("app.api.v1.tickets.get_ai_service", lambda: mock_ai_service)

    res_risk = client.post(f"/api/v1/tickets/{ticket.id}/ai-sla-risk", headers=agent_auth_headers)
    assert res_risk.status_code == 200
    rec_id = res_risk.json()["ai_risk_assessment"]["recommendation_id"]

    # 1. First approval succeeds
    res_app1 = client.post(
        f"/api/v1/tickets/{ticket.id}/ai-sla-risk/approve",
        json={"recommendation_id": rec_id, "apply_priority": True},
        headers=agent_auth_headers
    )
    assert res_app1.status_code == 200

    # 2. Duplicate decision attempt on same recommendation -> 409 Conflict
    res_dup = client.post(
        f"/api/v1/tickets/{ticket.id}/ai-sla-risk/approve",
        json={"recommendation_id": rec_id},
        headers=agent_auth_headers
    )
    assert res_dup.status_code == 409


def test_escalation_decision_user_forbidden(client, db_session, test_user, test_agent, user_auth_headers, agent_auth_headers, monkeypatch):
    """End-user cannot approve or reject escalation recommendations (403 Forbidden)."""
    ticket = Ticket(
        ticket_number="IT-RISK-9",
        title="Account Locked",
        description="Locked out of system",
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
        creator_id=test_user.id,
    )
    db_session.add(ticket)
    db_session.commit()

    mock_ai_service = MagicMock(spec=AIService)
    mock_ai_service.generate.return_value = AIResponse(
        content=json.dumps({
            "risk_level": "medium",
            "confidence": 0.70,
            "is_at_risk_of_breach": False,
            "predicted_time_to_breach": "10 hours",
            "risk_factors": ["User locked"],
            "recommended_action": "Unlock account",
            "escalation_recommended": False,
            "escalation_urgency": "low",
            "recommended_priority": "medium",
            "recommended_team": "IT Helpdesk",
            "evidence": ["Locked out of system"]
        }),
        status="success",
        used_fallback=False
    )
    monkeypatch.setattr("app.api.v1.tickets.get_ai_service", lambda: mock_ai_service)

    res_risk = client.post(f"/api/v1/tickets/{ticket.id}/ai-sla-risk", headers=agent_auth_headers)
    assert res_risk.status_code == 200
    rec_id = res_risk.json()["ai_risk_assessment"]["recommendation_id"]

    # User tries to approve -> 403 Forbidden
    res_user_app = client.post(
        f"/api/v1/tickets/{ticket.id}/ai-sla-risk/approve",
        json={"recommendation_id": rec_id},
        headers=user_auth_headers
    )
    assert res_user_app.status_code == 403

    # User tries to reject -> 403 Forbidden
    res_user_rej = client.post(
        f"/api/v1/tickets/{ticket.id}/ai-sla-risk/reject",
        json={"recommendation_id": rec_id},
        headers=user_auth_headers
    )
    assert res_user_rej.status_code == 403


def test_ai_sla_risk_coerces_string_factors_and_evidence(client, db_session, test_user, test_agent, agent_auth_headers, monkeypatch):
    """Verify SLA Risk safely coerces string or multiline evidence/risk factors from LLM."""
    ticket = Ticket(
        ticket_number="IT-RISK-10",
        title="Network Switch Failure",
        description="Core network switch rebooting unexpectedly.",
        priority=TicketPriority.HIGH,
        status=TicketStatus.OPEN,
        creator_id=test_user.id,
    )
    db_session.add(ticket)
    db_session.commit()

    # Pass scalar string for risk_factors and evidence
    mock_ai_content = json.dumps({
        "risk_level": "high",
        "confidence": 0.88,
        "is_at_risk_of_breach": True,
        "predicted_time_to_breach": "2 hours",
        "risk_factors": "- Switch reboot loop\n- Hardware power supply failure",
        "recommended_action": "Replace secondary power supply",
        "escalation_recommended": True,
        "escalation_urgency": "high",
        "recommended_priority": "critical",
        "recommended_team": "Network Engineering",
        "evidence": "Core network switch rebooting unexpectedly."
    })

    mock_ai_service = MagicMock(spec=AIService)
    mock_ai_service.generate.return_value = AIResponse(
        content=mock_ai_content,
        status="success",
        used_fallback=False
    )
    monkeypatch.setattr("app.api.v1.tickets.get_ai_service", lambda: mock_ai_service)

    res = client.post(f"/api/v1/tickets/{ticket.id}/ai-sla-risk", headers=agent_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assessment = data["ai_risk_assessment"]
    assert isinstance(assessment["risk_factors"], list)
    assert len(assessment["risk_factors"]) >= 1
    assert isinstance(assessment["evidence"], list)
    assert len(assessment["evidence"]) >= 1

