import json

import pytest
from fastapi import status

from app.core.security import create_access_token, get_password_hash
from app.models.audit_log import AuditAction, AuditLog
from app.models.ticket import Category, Ticket
from app.models.user import User, UserRole
from app.schemas.ai import AIResponse


class MockAIService:
    def __init__(self, response: AIResponse):
        self.response = response
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return self.response


def triage_content(**overrides) -> str:
    payload = {
        "category": "Database",
        "priority": "critical",
        "urgency": "high",
        "impact": "organization_wide",
        "suggested_team": "IT Operations",
        "confidence": 0.94,
        "evidence": [
            "Production database is down",
            "Employees cannot access the application",
        ],
        "priority_evidence": [
            "Production database is down",
            "Employees cannot access the application",
        ],
        "category_evidence": [
            "Production database is down",
        ],
        "urgency_impact_evidence": [
            "Employees cannot access the application",
        ],
    }
    payload.update(overrides)
    return json.dumps(payload)


def create_ai_triage(client, user_auth_headers, monkeypatch, **payload_overrides):
    ai_mock = install_ai_mock(monkeypatch, AIResponse(content=triage_content(**payload_overrides), status="success", used_fallback=False))
    response = client.post("/api/v1/tickets/placeholder/ai-triage", headers=user_auth_headers)
    return response, ai_mock


def create_triage_ticket(client, user_auth_headers):
    response = client.post(
        "/api/v1/tickets/",
        headers=user_auth_headers,
        json={
            "title": "Production database is down",
            "description": "Employees cannot access the application.",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def install_ai_mock(monkeypatch, response: AIResponse) -> MockAIService:
    mock_service = MockAIService(response)
    monkeypatch.setattr("app.api.v1.tickets.get_ai_service", lambda: mock_service)
    return mock_service


def add_database_category(db_session):
    category = Category(name="Database", description="Database incidents", default_sla_hours=4, is_active=True)
    db_session.add(category)
    db_session.commit()


def test_ticket_triage_returns_valid_recommendation_without_modifying_ticket(
    client, user_auth_headers, db_session, test_agent, monkeypatch
):
    add_database_category(db_session)
    ticket_id = create_triage_ticket(client, user_auth_headers)
    ticket_before = db_session.query(Ticket).filter(Ticket.id == ticket_id).one()
    original_values = (ticket_before.status, ticket_before.priority, ticket_before.category_id, ticket_before.assignee_id)
    ai_mock = install_ai_mock(monkeypatch, AIResponse(content=triage_content(), status="success", used_fallback=False))

    response = client.post(f"/api/v1/tickets/{ticket_id}/ai-triage", headers=user_auth_headers)

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["category"] == "Database"
    assert payload["priority"] == "critical"
    assert payload["urgency"] == "high"
    assert payload["impact"] == "organization_wide"
    assert payload["suggested_team"] == "IT Operations"
    assert payload["confidence"] == 0.94
    assert payload["explanation"] == "Production database is down; Employees cannot access the application"
    assert payload["recommendation_id"]
    assert payload["priority_reason"] == "Production database is down; Employees cannot access the application"
    assert ai_mock.requests[0].context.keys() == {
        "title", "description", "available_categories", "valid_priorities", "available_teams"
    }
    assert ai_mock.requests[0].response_format == "json_object"
    db_session.refresh(ticket_before)
    assert (ticket_before.status, ticket_before.priority, ticket_before.category_id, ticket_before.assignee_id) == original_values


def test_ticket_triage_rejects_malformed_structured_response(client, user_auth_headers, monkeypatch):
    ticket_id = create_triage_ticket(client, user_auth_headers)
    install_ai_mock(monkeypatch, AIResponse(content="not-json", status="success", used_fallback=False))

    response = client.post(f"/api/v1/tickets/{ticket_id}/ai-triage", headers=user_auth_headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_agent_can_approve_valid_recommendation(client, user_auth_headers, agent_auth_headers, db_session, monkeypatch):
    add_database_category(db_session)
    ticket_id = create_triage_ticket(client, user_auth_headers)
    triage_response = client.post(f"/api/v1/tickets/{ticket_id}/ai-triage", headers=agent_auth_headers)
    recommendation_id = triage_response.json()["recommendation_id"]

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-triage/approve",
        headers=agent_auth_headers,
        json={"recommendation_id": recommendation_id},
    )

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["decision"] == "accepted"
    assert payload["recommendation_id"] == recommendation_id
    ticket = db_session.query(Ticket).filter(Ticket.id == ticket_id).one()
    assert ticket.priority == "critical"
    assert ticket.category_id is not None


def test_admin_can_approve_valid_recommendation(client, user_auth_headers, admin_auth_headers, db_session, monkeypatch):
    add_database_category(db_session)
    ticket_id = create_triage_ticket(client, user_auth_headers)
    triage_response = client.post(f"/api/v1/tickets/{ticket_id}/ai-triage", headers=admin_auth_headers)
    recommendation_id = triage_response.json()["recommendation_id"]

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-triage/approve",
        headers=admin_auth_headers,
        json={"recommendation_id": recommendation_id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["decision"] == "accepted"


def test_user_cannot_approve_or_reject(client, user_auth_headers, db_session, monkeypatch):
    add_database_category(db_session)
    ticket_id = create_triage_ticket(client, user_auth_headers)
    triage_response = client.post(f"/api/v1/tickets/{ticket_id}/ai-triage", headers=user_auth_headers)
    recommendation_id = triage_response.json()["recommendation_id"]

    approve_response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-triage/approve",
        headers=user_auth_headers,
        json={"recommendation_id": recommendation_id},
    )
    reject_response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-triage/reject",
        headers=user_auth_headers,
        json={"recommendation_id": recommendation_id},
    )

    assert approve_response.status_code == status.HTTP_403_FORBIDDEN
    assert reject_response.status_code == status.HTTP_403_FORBIDDEN


def test_agent_can_reject_recommendation(client, user_auth_headers, agent_auth_headers, db_session, monkeypatch):
    add_database_category(db_session)
    ticket_id = create_triage_ticket(client, user_auth_headers)
    triage_response = client.post(f"/api/v1/tickets/{ticket_id}/ai-triage", headers=agent_auth_headers)
    recommendation_id = triage_response.json()["recommendation_id"]

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-triage/reject",
        headers=agent_auth_headers,
        json={"recommendation_id": recommendation_id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["decision"] == "rejected"
    ticket = db_session.query(Ticket).filter(Ticket.id == ticket_id).one()
    assert ticket.priority == "medium"


def test_invalid_stale_recommendation_cannot_be_approved(client, user_auth_headers, agent_auth_headers, db_session, monkeypatch):
    add_database_category(db_session)
    ticket_id = create_triage_ticket(client, user_auth_headers)
    triage_response = client.post(f"/api/v1/tickets/{ticket_id}/ai-triage", headers=agent_auth_headers)
    recommendation_id = triage_response.json()["recommendation_id"]
    client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers=agent_auth_headers,
        json={"title": "Updated title after AI triage", "priority": "high"},
    )

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-triage/approve",
        headers=agent_auth_headers,
        json={"recommendation_id": recommendation_id},
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_duplicate_approval_is_prevented(client, user_auth_headers, agent_auth_headers, db_session, monkeypatch):
    add_database_category(db_session)
    ticket_id = create_triage_ticket(client, user_auth_headers)
    triage_response = client.post(f"/api/v1/tickets/{ticket_id}/ai-triage", headers=agent_auth_headers)
    recommendation_id = triage_response.json()["recommendation_id"]

    approved = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-triage/approve",
        headers=agent_auth_headers,
        json={"recommendation_id": recommendation_id},
    )
    duplicate = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-triage/approve",
        headers=agent_auth_headers,
        json={"recommendation_id": recommendation_id},
    )

    assert approved.status_code == status.HTTP_200_OK
    assert duplicate.status_code == status.HTTP_409_CONFLICT


def test_approval_applies_only_valid_recommendation_fields(client, user_auth_headers, agent_auth_headers, db_session, monkeypatch):
    add_database_category(db_session)
    ticket_id = create_triage_ticket(client, user_auth_headers)
    triage_response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-triage",
        headers=agent_auth_headers,
    )
    recommendation_id = triage_response.json()["recommendation_id"]

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-triage/approve",
        headers=agent_auth_headers,
        json={"recommendation_id": recommendation_id},
    )

    assert response.status_code == status.HTTP_200_OK
    ticket = db_session.query(Ticket).filter(Ticket.id == ticket_id).one()
    assert ticket.status == "open"
    assert ticket.priority == "critical"
    assert ticket.category_id is not None


def test_rejection_does_not_modify_ticket(client, user_auth_headers, agent_auth_headers, db_session, monkeypatch):
    add_database_category(db_session)
    ticket_id = create_triage_ticket(client, user_auth_headers)
    triage_response = client.post(f"/api/v1/tickets/{ticket_id}/ai-triage", headers=agent_auth_headers)
    recommendation_id = triage_response.json()["recommendation_id"]
    ticket_before = db_session.query(Ticket).filter(Ticket.id == ticket_id).one()

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-triage/reject",
        headers=agent_auth_headers,
        json={"recommendation_id": recommendation_id},
    )

    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(ticket_before)
    assert ticket_before.status == "open"
    assert ticket_before.priority == "medium"
    assert ticket_before.category_id is None


def test_ai_recommendation_decision_creates_audit_record(client, user_auth_headers, agent_auth_headers, db_session, monkeypatch):
    add_database_category(db_session)
    ticket_id = create_triage_ticket(client, user_auth_headers)
    triage_response = client.post(f"/api/v1/tickets/{ticket_id}/ai-triage", headers=agent_auth_headers)
    recommendation_id = triage_response.json()["recommendation_id"]

    client.post(
        f"/api/v1/tickets/{ticket_id}/ai-triage/approve",
        headers=agent_auth_headers,
        json={"recommendation_id": recommendation_id},
    )

    audit_logs = db_session.query(AuditLog).filter(AuditLog.ticket_id == ticket_id).all()
    actions = {item.action for item in audit_logs}
    assert AuditAction.AI_TRIAGED in actions
    assert AuditAction.AI_RECOMMENDATION_ACCEPTED in actions
    accepted_log = db_session.query(AuditLog).filter(
        AuditLog.ticket_id == ticket_id,
        AuditLog.action == AuditAction.AI_RECOMMENDATION_ACCEPTED,
    ).one()
    assert accepted_log.actor_id is not None


def test_admin_can_reject_recommendation(client, user_auth_headers, admin_auth_headers, db_session, monkeypatch):
    add_database_category(db_session)
    ticket_id = create_triage_ticket(client, user_auth_headers)
    triage_response = client.post(f"/api/v1/tickets/{ticket_id}/ai-triage", headers=admin_auth_headers)
    recommendation_id = triage_response.json()["recommendation_id"]

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-triage/reject",
        headers=admin_auth_headers,
        json={"recommendation_id": recommendation_id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["decision"] == "rejected"


@pytest.mark.parametrize("field, value", [("category", "Unknown"), ("priority", "immediate")])
def test_ticket_triage_rejects_invalid_category_or_priority(client, user_auth_headers, db_session, monkeypatch, field, value):
    add_database_category(db_session)
    ticket_id = create_triage_ticket(client, user_auth_headers)
    install_ai_mock(monkeypatch, AIResponse(content=triage_content(**{field: value}), status="success", used_fallback=False))

    response = client.post(f"/api/v1/tickets/{ticket_id}/ai-triage", headers=user_auth_headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_ticket_triage_rejects_invalid_confidence(client, user_auth_headers, monkeypatch):
    ticket_id = create_triage_ticket(client, user_auth_headers)
    install_ai_mock(monkeypatch, AIResponse(content=triage_content(confidence=1.2), status="success", used_fallback=False))

    response = client.post(f"/api/v1/tickets/{ticket_id}/ai-triage", headers=user_auth_headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["error_code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("error_code", ["AI_PROVIDER_ERROR", "AI_TIMEOUT"])
def test_ticket_triage_handles_ai_failures(client, user_auth_headers, monkeypatch, error_code):
    ticket_id = create_triage_ticket(client, user_auth_headers)
    install_ai_mock(monkeypatch, AIResponse(status="fallback", used_fallback=True, error_code=error_code))

    response = client.post(f"/api/v1/tickets/{ticket_id}/ai-triage", headers=user_auth_headers)

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["error_code"] == "SERVICE_UNAVAILABLE"


def test_ticket_triage_requires_authentication(client):
    response = client.post("/api/v1/tickets/not-a-ticket/ai-triage")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_ticket_triage_returns_not_found_for_unknown_ticket(client, user_auth_headers, monkeypatch):
    ai_mock = install_ai_mock(monkeypatch, AIResponse(content=triage_content(), status="success", used_fallback=False))

    response = client.post("/api/v1/tickets/unknown-ticket/ai-triage", headers=user_auth_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert ai_mock.requests == []


def test_user_cannot_triage_another_users_ticket(client, user_auth_headers, db_session, monkeypatch):
    other_user = User(
        email="triage-owner@example.com",
        hashed_password=get_password_hash("Pass123!"),
        full_name="Triage Owner",
        role=UserRole.USER,
    )
    db_session.add(other_user)
    db_session.commit()
    other_headers = {
        "Authorization": f"Bearer {create_access_token({'sub': other_user.id, 'email': other_user.email, 'role': other_user.role})}"
    }
    ticket_id = create_triage_ticket(client, other_headers)
    ai_mock = install_ai_mock(monkeypatch, AIResponse(content=triage_content(), status="success", used_fallback=False))

    response = client.post(f"/api/v1/tickets/{ticket_id}/ai-triage", headers=user_auth_headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert ai_mock.requests == []


def test_agent_can_triage_accessible_ticket(client, user_auth_headers, agent_auth_headers, db_session, monkeypatch):
    add_database_category(db_session)
    ticket_id = create_triage_ticket(client, user_auth_headers)
    install_ai_mock(monkeypatch, AIResponse(content=triage_content(), status="success", used_fallback=False))

    response = client.post(f"/api/v1/tickets/{ticket_id}/ai-triage", headers=agent_auth_headers)

    assert response.status_code == status.HTTP_200_OK


def test_admin_can_triage_accessible_ticket(client, user_auth_headers, admin_auth_headers, db_session, monkeypatch):
    add_database_category(db_session)
    ticket_id = create_triage_ticket(client, user_auth_headers)
    install_ai_mock(monkeypatch, AIResponse(content=triage_content(), status="success", used_fallback=False))

    response = client.post(f"/api/v1/tickets/{ticket_id}/ai-triage", headers=admin_auth_headers)

    assert response.status_code == status.HTTP_200_OK
