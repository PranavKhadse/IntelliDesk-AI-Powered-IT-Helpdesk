"""Comprehensive tests for AI Grounding, KB retrieval, source attribution, and security."""

import json
import pytest
from fastapi import status

from app.models.comment import CommentType, TicketComment
from app.models.ticket import Ticket, Category
from app.models.kb_article import KBArticle
from app.models.user import UserRole
from app.schemas.ai import AIResponse


class MockAIService:
    def __init__(self, response: AIResponse):
        self.response = response
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return self.response


def grounding_content(**overrides) -> str:
    payload = {
        "grounding_status": "grounded",
        "grounded_response": (
            "Based on the Verified VPN Troubleshooting Guide (KB-101), ensure OpenVPN Client 3.4+ is installed. "
            "Re-import the corporate ovpn profile and verify Multi-Factor Authentication token in Okta."
        ),
        "cited_article_ids": ["test-article-vpn-id"],
        "key_points": [
            "Verify OpenVPN Client version 3.4+",
            "Re-import the corporate ovpn profile",
            "Authenticate via Okta MFA",
        ],
        "confidence": 0.94,
        "reasoning": "The ticket symptoms match the VPN connection failure procedure in KB-101.",
    }
    payload.update(overrides)
    return json.dumps(payload)


def install_ai_mock(monkeypatch, response: AIResponse) -> MockAIService:
    mock_service = MockAIService(response)
    monkeypatch.setattr("app.api.v1.tickets.get_ai_service", lambda: mock_service)
    return mock_service


def create_sample_ticket(client, user_auth_headers, title="VPN connection error on macOS", description="I cannot connect to the corporate VPN when working remotely."):
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


def seed_kb_article(client, agent_auth_headers, title="VPN Troubleshooting Guide", content="Steps to fix VPN connection issues. Re-import .ovpn profile and verify Okta MFA.", is_published=True):
    response = client.post(
        "/api/v1/kb/articles",
        headers=agent_auth_headers,
        json={
            "title": title,
            "summary": "VPN connection troubleshooting steps.",
            "content": content,
            "tags": "vpn,network,remote,okta",
            "is_published": is_published,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_get_ticket_kb_matches(client, user_auth_headers, agent_auth_headers):
    """Retrieve published KB articles matching ticket keywords."""
    article_id = seed_kb_article(client, agent_auth_headers)
    ticket_id = create_sample_ticket(client, user_auth_headers, title="VPN connection timeout", description="VPN fails to connect.")

    response = client.get(f"/api/v1/tickets/{ticket_id}/kb-matches", headers=user_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["article_id"] == article_id
    assert data[0]["relevance_score"] > 0.25


def test_ai_grounding_success_with_sources(client, user_auth_headers, agent_auth_headers, monkeypatch):
    """AI grounding produces grounded recommendation with verified source citations."""
    article_id = seed_kb_article(client, agent_auth_headers)
    ticket_id = create_sample_ticket(client, user_auth_headers)

    ai_content = grounding_content(cited_article_ids=[article_id])
    ai_mock = install_ai_mock(monkeypatch, AIResponse(content=ai_content, status="success", used_fallback=False))

    response = client.post(f"/api/v1/tickets/{ticket_id}/ai-grounding", headers=user_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["grounding_status"] == "grounded"
    assert "OpenVPN" in data["recommendation"]
    assert len(data["sources"]) >= 1
    assert data["sources"][0]["article_id"] == article_id
    assert data["confidence"] == 0.94
    assert len(ai_mock.requests) == 1
    assert ai_mock.requests[0].capability == "ticket_grounding"


def test_ai_grounding_partially_grounded(client, user_auth_headers, agent_auth_headers, monkeypatch):
    """AI grounding returns partially_grounded status when KB only covers partial steps."""
    article_id = seed_kb_article(client, agent_auth_headers)
    ticket_id = create_sample_ticket(client, user_auth_headers)

    ai_content = grounding_content(
        grounding_status="partially_grounded",
        grounded_response="The KB covers basic VPN reset, but hardware router diagnosis is also needed.",
        cited_article_ids=[article_id],
        confidence=0.68,
    )
    install_ai_mock(monkeypatch, AIResponse(content=ai_content, status="success", used_fallback=False))

    response = client.post(f"/api/v1/tickets/{ticket_id}/ai-grounding", headers=user_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["grounding_status"] == "partially_grounded"
    assert data["confidence"] == 0.68


def test_ai_grounding_no_match_behavior(client, user_auth_headers, monkeypatch):
    """When no KB articles match ticket description, returns clean no-match state."""
    # Create ticket with completely unrelated query where no KB exists
    ticket_id = create_sample_ticket(
        client,
        user_auth_headers,
        title="Unusual quantum physics simulation glitch",
        description="Complex particle dynamics calculation crashed on custom FPGA board.",
    )

    ai_mock = install_ai_mock(monkeypatch, AIResponse(content=grounding_content(), status="success", used_fallback=False))

    response = client.post(f"/api/v1/tickets/{ticket_id}/ai-grounding", headers=user_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["grounding_status"] == "no_match"
    assert "No reliable knowledge base articles match" in data["recommendation"]
    assert len(data["sources"]) == 0
    assert data["confidence"] == 0.0
    assert data["no_match_reason"] is not None
    # Verify AI generation was not called or cleanly skipped for empty matches
    assert len(ai_mock.requests) == 0


def test_secret_sanitization_and_internal_note_exclusion(
    client, user_auth_headers, agent_auth_headers, db_session, test_agent, monkeypatch
):
    """Secrets in ticket and comments are masked; internal notes are excluded from grounding context."""
    article_id = seed_kb_article(client, agent_auth_headers)
    ticket_id = create_sample_ticket(
        client,
        user_auth_headers,
        title="VPN failure with Authorization: Bearer super-secret-jwt-token-999",
        description="Trouble connecting with password: SuperSecretDBPassword! and api_key=ak-12345678",
    )

    # Add public comment and internal note
    public_comment = TicketComment(
        ticket_id=ticket_id,
        author_id=test_agent.id,
        comment_type=CommentType.PUBLIC,
        content="Public note: please send your OS version.",
    )
    internal_note = TicketComment(
        ticket_id=ticket_id,
        author_id=test_agent.id,
        comment_type=CommentType.INTERNAL_NOTE,
        content="Internal note: user secret account PIN is 998877.",
    )
    db_session.add(public_comment)
    db_session.add(internal_note)
    db_session.commit()

    ai_content = grounding_content(cited_article_ids=[article_id])
    ai_mock = install_ai_mock(monkeypatch, AIResponse(content=ai_content, status="success", used_fallback=False))

    response = client.post(f"/api/v1/tickets/{ticket_id}/ai-grounding", headers=user_auth_headers)
    assert response.status_code == 200
    assert len(ai_mock.requests) == 1

    sent_context = ai_mock.requests[0].context
    context_str = json.dumps(sent_context)

    # Verify secrets were scrubbed
    assert "super-secret-jwt-token-999" not in context_str
    assert "SuperSecretDBPassword!" not in context_str
    assert "ak-12345678" not in context_str

    # Verify internal note is strictly excluded
    assert "998877" not in context_str
    assert "Internal note" not in context_str
    # Verify public comment is present
    assert "Public note: please send your OS version" in context_str


def test_ai_grounding_provider_failure_returns_503(client, user_auth_headers, agent_auth_headers, monkeypatch):
    """Provider failure gracefully returns 503 Service Unavailable."""
    seed_kb_article(client, agent_auth_headers)
    ticket_id = create_sample_ticket(client, user_auth_headers)
    install_ai_mock(monkeypatch, AIResponse(status="fallback", used_fallback=True, error_code="AI_PROVIDER_ERROR"))

    response = client.post(f"/api/v1/tickets/{ticket_id}/ai-grounding", headers=user_auth_headers)
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["error_code"] == "SERVICE_UNAVAILABLE"


def test_ai_grounding_malformed_json_returns_validation_error(client, user_auth_headers, agent_auth_headers, monkeypatch):
    """Malformed provider output triggers validation error."""
    seed_kb_article(client, agent_auth_headers)
    ticket_id = create_sample_ticket(client, user_auth_headers)
    install_ai_mock(monkeypatch, AIResponse(content="invalid-json-output", status="success", used_fallback=False))

    response = client.post(f"/api/v1/tickets/{ticket_id}/ai-grounding", headers=user_auth_headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_ticket_immutability_during_grounding(client, user_auth_headers, agent_auth_headers, db_session, monkeypatch):
    """Ticket status, priority, and metadata are unchanged by grounding."""
    article_id = seed_kb_article(client, agent_auth_headers)
    ticket_id = create_sample_ticket(client, user_auth_headers)

    ticket_before = db_session.query(Ticket).filter(Ticket.id == ticket_id).one()
    initial_status = ticket_before.status
    initial_priority = ticket_before.priority
    initial_updated_at = ticket_before.updated_at
    initial_title = ticket_before.title
    initial_description = ticket_before.description

    ai_content = grounding_content(cited_article_ids=[article_id])
    install_ai_mock(monkeypatch, AIResponse(content=ai_content, status="success", used_fallback=False))

    response = client.post(f"/api/v1/tickets/{ticket_id}/ai-grounding", headers=user_auth_headers)
    assert response.status_code == 200

    db_session.refresh(ticket_before)
    assert ticket_before.status == initial_status
    assert ticket_before.priority == initial_priority
    assert ticket_before.updated_at == initial_updated_at
    assert ticket_before.title == initial_title
    assert ticket_before.description == initial_description
