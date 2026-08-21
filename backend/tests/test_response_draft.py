import json
import pytest
from fastapi import status

from app.core.security import create_access_token, get_password_hash
from app.models.comment import CommentType, TicketComment
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


def draft_content(**overrides) -> str:
    payload = {
        "draft_response": "Hello Alex, we are currently investigating the issue with the production database. Could you please confirm if other team members in your department are also affected?",
        "tone": "professional and empathetic",
        "key_points": [
            "Acknowledge the database outage",
            "Confirm active investigation",
            "Request impact scope verification",
        ],
        "confidence": 0.92,
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


def test_agent_can_generate_response_draft(client, user_auth_headers, agent_auth_headers, monkeypatch):
    ticket_id = create_sample_ticket(client, user_auth_headers)
    ai_mock = install_ai_mock(monkeypatch, AIResponse(content=draft_content(), status="success", used_fallback=False))

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-response-draft",
        headers=agent_auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "Hello Alex" in data["draft_response"]
    assert data["tone"] == "professional and empathetic"
    assert len(data["key_points"]) == 3
    assert data["confidence"] == 0.92
    assert len(ai_mock.requests) == 1
    assert ai_mock.requests[0].capability == "response_draft"
    assert ai_mock.requests[0].response_format == "json_object"


def test_admin_can_generate_response_draft(client, user_auth_headers, admin_auth_headers, monkeypatch):
    ticket_id = create_sample_ticket(client, user_auth_headers)
    install_ai_mock(monkeypatch, AIResponse(content=draft_content(), status="success", used_fallback=False))

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-response-draft",
        headers=admin_auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["confidence"] == 0.92


def test_user_forbidden_from_generating_response_draft(client, user_auth_headers, monkeypatch):
    ticket_id = create_sample_ticket(client, user_auth_headers)
    ai_mock = install_ai_mock(monkeypatch, AIResponse(content=draft_content(), status="success", used_fallback=False))

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-response-draft",
        headers=user_auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert len(ai_mock.requests) == 0


def test_unauthenticated_request_rejected(client):
    response = client.post("/api/v1/tickets/some-id/ai-response-draft")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_unauthorized_ticket_access_returns_not_found_for_missing(client, agent_auth_headers, monkeypatch):
    install_ai_mock(monkeypatch, AIResponse(content=draft_content(), status="success", used_fallback=False))
    response = client.post(
        "/api/v1/tickets/non-existent-ticket-id/ai-response-draft",
        headers=agent_auth_headers,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_provider_failure_returns_service_unavailable(client, user_auth_headers, agent_auth_headers, monkeypatch):
    ticket_id = create_sample_ticket(client, user_auth_headers)
    install_ai_mock(monkeypatch, AIResponse(status="fallback", used_fallback=True, error_code="AI_PROVIDER_ERROR"))

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-response-draft",
        headers=agent_auth_headers,
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["error_code"] == "SERVICE_UNAVAILABLE"


def test_timeout_returns_service_unavailable(client, user_auth_headers, agent_auth_headers, monkeypatch):
    ticket_id = create_sample_ticket(client, user_auth_headers)
    install_ai_mock(monkeypatch, AIResponse(status="fallback", used_fallback=True, error_code="AI_TIMEOUT"))

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-response-draft",
        headers=agent_auth_headers,
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["error_code"] == "SERVICE_UNAVAILABLE"


def test_malformed_ai_response_returns_validation_error(client, user_auth_headers, agent_auth_headers, monkeypatch):
    ticket_id = create_sample_ticket(client, user_auth_headers)
    install_ai_mock(monkeypatch, AIResponse(content="not valid json", status="success", used_fallback=False))

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-response-draft",
        headers=agent_auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_draft_does_not_modify_ticket_or_post_comments(client, user_auth_headers, agent_auth_headers, db_session, monkeypatch):
    ticket_id = create_sample_ticket(client, user_auth_headers)
    ticket_before = db_session.query(Ticket).filter(Ticket.id == ticket_id).one()
    initial_status = ticket_before.status
    initial_priority = ticket_before.priority
    initial_updated_at = ticket_before.updated_at
    initial_comment_count = len(ticket_before.comments)

    install_ai_mock(monkeypatch, AIResponse(content=draft_content(), status="success", used_fallback=False))

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-response-draft",
        headers=agent_auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK

    db_session.refresh(ticket_before)
    assert ticket_before.status == initial_status
    assert ticket_before.priority == initial_priority
    assert ticket_before.updated_at == initial_updated_at
    assert len(ticket_before.comments) == initial_comment_count


def test_secret_safe_behavior_masks_credentials_and_excludes_internal_notes(
    client, user_auth_headers, agent_auth_headers, db_session, test_agent, monkeypatch
):
    # Ticket with sensitive data in title/description
    ticket_id = create_sample_ticket(
        client,
        user_auth_headers,
        title="Failed API connection with Authorization: Bearer secret-token-xyz123",
        description="Login error with password: SuperSecretPassword! and api_key=secret-key-456",
    )

    # Add a public comment and an internal agent note
    public_comment = TicketComment(
        ticket_id=ticket_id,
        author_id=test_agent.id,
        comment_type=CommentType.PUBLIC,
        content="Public note: please send logs.",
    )
    internal_note = TicketComment(
        ticket_id=ticket_id,
        author_id=test_agent.id,
        comment_type=CommentType.INTERNAL_NOTE,
        content="Confidential internal note: customer account number 998877 is flagged for audit.",
    )
    db_session.add(public_comment)
    db_session.add(internal_note)
    db_session.commit()

    ai_mock = install_ai_mock(monkeypatch, AIResponse(content=draft_content(), status="success", used_fallback=False))

    response = client.post(
        f"/api/v1/tickets/{ticket_id}/ai-response-draft",
        headers=agent_auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(ai_mock.requests) == 1
    sent_context = ai_mock.requests[0].context

    # Verify secrets were redacted
    assert "secret-token-xyz123" not in json.dumps(sent_context)
    assert "SuperSecretPassword!" not in json.dumps(sent_context)
    assert "secret-key-456" not in json.dumps(sent_context)

    # Verify internal notes were NOT included in public comments
    context_comments = sent_context.get("public_comments", [])
    assert len(context_comments) == 1
    assert "Public note" in context_comments[0]["content"]
    assert "Confidential internal note" not in json.dumps(sent_context)
    assert "998877" not in json.dumps(sent_context)
