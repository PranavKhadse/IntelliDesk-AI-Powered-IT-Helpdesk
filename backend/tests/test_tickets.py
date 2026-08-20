import pytest
from fastapi import status
from app.models.user import User, UserRole
from app.core.security import get_password_hash, create_access_token


def test_create_ticket(client, user_auth_headers):
    response = client.post(
        "/api/v1/tickets/",
        headers=user_auth_headers,
        json={
            "title": "Broken HDMI Port in Conference Room B",
            "description": "The cable seems fine but HDMI display remains blank.",
            "priority": "high",
            "category_id": 1
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["ticket_number"].startswith("IT-")
    assert data["title"] == "Broken HDMI Port in Conference Room B"
    assert data["status"] == "open"
    assert data["priority"] == "high"
    assert data["sla_due_at"] is not None


def test_user_ticket_scoping(client, user_auth_headers, db_session):
    # Create another user
    other_user = User(
        email="other@company.com",
        hashed_password=get_password_hash("Pass123!"),
        full_name="Other User",
        role=UserRole.USER
    )
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)
    other_headers = {"Authorization": f"Bearer {create_access_token({'sub': other_user.id, 'email': other_user.email, 'role': other_user.role})}"}

    # Other user creates a ticket
    res = client.post(
        "/api/v1/tickets/",
        headers=other_headers,
        json={"title": "Private Ticket", "description": "Confidential matter"}
    )
    assert res.status_code == status.HTTP_201_CREATED
    other_ticket_id = res.json()["id"]

    # First user should NOT see other user's ticket in their list
    res_list = client.get("/api/v1/tickets/", headers=user_auth_headers)
    assert res_list.status_code == status.HTTP_200_OK
    assert all(item["id"] != other_ticket_id for item in res_list.json()["items"])

    # First user attempting direct access should receive 403 Forbidden
    res_detail = client.get(f"/api/v1/tickets/{other_ticket_id}", headers=user_auth_headers)
    assert res_detail.status_code == status.HTTP_403_FORBIDDEN


def test_agent_update_ticket_status(client, user_auth_headers, agent_auth_headers):
    # User creates ticket
    create_res = client.post(
        "/api/v1/tickets/",
        headers=user_auth_headers,
        json={"title": "Keyboard Key Stuck", "description": "The spacebar is jammed."}
    )
    ticket_id = create_res.json()["id"]

    # Agent updates status to in_progress
    patch_res = client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers=agent_auth_headers,
        json={"status": "in_progress"}
    )
    assert patch_res.status_code == status.HTTP_200_OK
    assert patch_res.json()["status"] == "in_progress"

    # Agent resolves ticket
    resolve_res = client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers=agent_auth_headers,
        json={"status": "resolved"}
    )
    assert resolve_res.status_code == status.HTTP_200_OK
    assert resolve_res.json()["status"] == "resolved"
    assert resolve_res.json()["resolved_at"] is not None


def test_ticket_comments_and_internal_notes(client, user_auth_headers, agent_auth_headers):
    # User creates ticket
    create_res = client.post(
        "/api/v1/tickets/",
        headers=user_auth_headers,
        json={"title": "Monitor Stand Missing", "description": "Need stand for dual setup."}
    )
    ticket_id = create_res.json()["id"]

    # User adds public comment
    user_comment = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        headers=user_auth_headers,
        json={"content": "Also need an extra DP cable if available.", "comment_type": "public"}
    )
    assert user_comment.status_code == status.HTTP_201_CREATED

    # User attempts internal note -> should fail with 403
    forbidden_comment = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        headers=user_auth_headers,
        json={"content": "Secret note", "comment_type": "internal_note"}
    )
    assert forbidden_comment.status_code == status.HTTP_403_FORBIDDEN

    # Agent adds internal note -> succeeds
    agent_note = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        headers=agent_auth_headers,
        json={"content": "Checked storage room B, stand ordered from vendor.", "comment_type": "internal_note"}
    )
    assert agent_note.status_code == status.HTTP_201_CREATED

    # Verify user detail view hides internal note
    user_view = client.get(f"/api/v1/tickets/{ticket_id}", headers=user_auth_headers)
    assert user_view.status_code == status.HTTP_200_OK
    assert len(user_view.json()["comments"]) == 1
    assert user_view.json()["comments"][0]["comment_type"] == "public"

    # Agent detail view shows both comments
    agent_view = client.get(f"/api/v1/tickets/{ticket_id}", headers=agent_auth_headers)
    assert agent_view.status_code == status.HTTP_200_OK
    assert len(agent_view.json()["comments"]) == 2
