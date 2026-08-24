import json
import pytest
from fastapi import status

from app.models.comment import CommentType, TicketComment
from app.models.ticket import Ticket
from app.schemas.ai import AIResponse


class MockAIService:
    def __init__(self, response: AIResponse):
        self.response = response
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return self.response


def sample_summary_content(**overrides) -> str:
    payload = {
        "summary": "Customer cannot connect to the primary PostgreSQL database after network maintenance.",
        "customer_issue": "Database connection timeouts occurring across the application cluster.",
        "important_facts": [
            "Issue started post 02:00 UTC maintenance window",
            "Error code PG-CON-TIMEOUT reported by backend nodes",
            "Affects production environment",
        ],
        "actions_taken": [
            "Network routing verified by tier-1 support",
            "Firewall rule check initiated",
        ],
        "suggested_next_steps": [
            "Verify database listener port 5432 availability",
            "Inspect database connection pool logs",
            "Notify customer of progress",
        ],
        "missing_information": [
            "Specific client IP addresses experiencing drops",
        ],
        "risk_flags": [
            "High impact on production services",
            "Potential SLA breach if unresolved within 2 hours",
        ],
        "confidence": 0.94,
    }
    payload.update(overrides)
    return json.dumps(payload)


def install_ai_mock(monkeypatch, response: AIResponse) -> MockAIService:
    mock_service = MockAIService(response)
    monkeypatch.setattr("app.api.v1.tickets.get_ai_service", lambda: mock_service)
    return mock_service


def create_sample_ticket(client, user_auth_headers, title="Database connection issue", description="Cannot connect to primary PostgreSQL instance."):
    response = client.post(
        "/api/v1/tickets/",
        headers=user_auth_headers,
        json={
            "title": title,
            "description": description,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def test_agent_can_generate_ticket_summary(client, user_auth_headers, agent_auth_headers, monkeypatch):
    ticket_id = create_sample_ticket(client, user_auth_headers)
    ai_mock = install_ai_mock(
        monkeypatch,
        AIResponse(content=sample_summary_content(), status="success", used_fallback=False),
    )

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-summary",
        headers=agent_auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "PostgreSQL" in data["summary"]
    assert "Database connection timeouts" in data["customer_issue"]
    assert len(data["important_facts"]) == 3
    assert len(data["actions_taken"]) == 2
    assert len(data["suggested_next_steps"]) == 3
    assert len(data["missing_information"]) == 1
    assert len(data["risk_flags"]) == 2
    assert data["confidence"] == 0.94

    assert len(ai_mock.requests) == 1
    assert ai_mock.requests[0].capability == "ticket_summary"
    assert ai_mock.requests[0].response_format == "json_object"


def test_admin_can_generate_ticket_summary(client, user_auth_headers, admin_auth_headers, monkeypatch):
    ticket_id = create_sample_ticket(client, user_auth_headers)
    install_ai_mock(
        monkeypatch,
        AIResponse(content=sample_summary_content(), status="success", used_fallback=False),
    )

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-summary",
        headers=admin_auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["confidence"] == 0.94


def test_user_forbidden_from_generating_ticket_summary(client, user_auth_headers, monkeypatch):
    ticket_id = create_sample_ticket(client, user_auth_headers)
    ai_mock = install_ai_mock(
        monkeypatch,
        AIResponse(content=sample_summary_content(), status="success", used_fallback=False),
    )

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-summary",
        headers=user_auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["error_code"] == "FORBIDDEN"
    assert len(ai_mock.requests) == 0


def test_unauthenticated_request_rejected(client):
    response = client.post("/api/v1/tickets/some-ticket-id/ai-summary")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_nonexistent_ticket_returns_not_found(client, agent_auth_headers, monkeypatch):
    install_ai_mock(
        monkeypatch,
        AIResponse(content=sample_summary_content(), status="success", used_fallback=False),
    )
    response = client.post(
        "/api/v1/tickets/non-existent-ticket-id/ai-summary",
        headers=agent_auth_headers,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_provider_failure_returns_service_unavailable(client, user_auth_headers, agent_auth_headers, monkeypatch):
    ticket_id = create_sample_ticket(client, user_auth_headers)
    install_ai_mock(
        monkeypatch,
        AIResponse(status="fallback", used_fallback=True, error_code="AI_PROVIDER_ERROR"),
    )

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-summary",
        headers=agent_auth_headers,
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["error_code"] == "SERVICE_UNAVAILABLE"


def test_provider_timeout_returns_service_unavailable(client, user_auth_headers, agent_auth_headers, monkeypatch):
    ticket_id = create_sample_ticket(client, user_auth_headers)
    install_ai_mock(
        monkeypatch,
        AIResponse(status="fallback", used_fallback=True, error_code="AI_TIMEOUT"),
    )

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-summary",
        headers=agent_auth_headers,
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["error_code"] == "SERVICE_UNAVAILABLE"


def test_malformed_ai_response_returns_validation_error(client, user_auth_headers, agent_auth_headers, monkeypatch):
    ticket_id = create_sample_ticket(client, user_auth_headers)
    install_ai_mock(
        monkeypatch,
        AIResponse(content="not valid json", status="success", used_fallback=False),
    )

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-summary",
        headers=agent_auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_confidence_validation_out_of_bounds(client, user_auth_headers, agent_auth_headers, monkeypatch):
    ticket_id = create_sample_ticket(client, user_auth_headers)
    # Confidence 1.5 is > 1.0, should fail validation
    install_ai_mock(
        monkeypatch,
        AIResponse(content=sample_summary_content(confidence=1.5), status="success", used_fallback=False),
    )

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-summary",
        headers=agent_auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_secret_sanitization_and_internal_note_exclusion(
    client, user_auth_headers, agent_auth_headers, db_session, test_agent, monkeypatch
):
    ticket_id = create_sample_ticket(
        client,
        user_auth_headers,
        title="Database failed Authorization: Bearer db-secret-token-999",
        description="Login error with password: VerySecretDbPassword! and api_key=production-api-key-888",
    )

    public_comment = TicketComment(
        ticket_id=ticket_id,
        author_id=test_agent.id,
        comment_type=CommentType.PUBLIC,
        content="Public update: Restarted gateway proxy.",
    )
    internal_note = TicketComment(
        ticket_id=ticket_id,
        author_id=test_agent.id,
        comment_type=CommentType.INTERNAL_NOTE,
        content="Top secret internal note: Infrastructure key infra-key-777 must not be exposed.",
    )
    db_session.add(public_comment)
    db_session.add(internal_note)
    db_session.commit()

    ai_mock = install_ai_mock(
        monkeypatch,
        AIResponse(content=sample_summary_content(), status="success", used_fallback=False),
    )

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-summary",
        headers=agent_auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(ai_mock.requests) == 1
    sent_context = ai_mock.requests[0].context

    # Verify secrets were scrubbed
    serialized_context = json.dumps(sent_context)
    assert "db-secret-token-999" not in serialized_context
    assert "VerySecretDbPassword!" not in serialized_context
    assert "production-api-key-888" not in serialized_context

    # Verify internal note was NOT included
    assert "infra-key-777" not in serialized_context
    assert "Top secret internal note" not in serialized_context

    # Verify public comment was included
    public_comments = sent_context.get("public_comments", [])
    assert len(public_comments) == 1
    assert "Restarted gateway proxy" in public_comments[0]["content"]


def test_summary_does_not_modify_ticket_or_database(
    client, user_auth_headers, agent_auth_headers, db_session, monkeypatch
):
    ticket_id = create_sample_ticket(client, user_auth_headers)
    ticket_before = db_session.query(Ticket).filter(Ticket.id == ticket_id).one()
    initial_status = ticket_before.status
    initial_priority = ticket_before.priority
    initial_updated_at = ticket_before.updated_at
    initial_comment_count = len(ticket_before.comments)
    initial_audit_count = len(ticket_before.audit_logs)

    install_ai_mock(
        monkeypatch,
        AIResponse(content=sample_summary_content(), status="success", used_fallback=False),
    )

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-summary",
        headers=agent_auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK

    db_session.refresh(ticket_before)
    assert ticket_before.status == initial_status
    assert ticket_before.priority == initial_priority
    assert ticket_before.updated_at == initial_updated_at
    assert len(ticket_before.comments) == initial_comment_count
    assert len(ticket_before.audit_logs) == initial_audit_count
