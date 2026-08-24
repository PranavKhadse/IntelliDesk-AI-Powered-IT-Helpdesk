"""Comprehensive tests for Knowledge Base CRUD, RBAC, search, and visibility."""

import pytest
from app.models.user import UserRole
from app.models.ticket import Category
from app.models.kb_article import KBArticle


def test_create_kb_article_by_agent(client, agent_auth_headers, db_session):
    """Staff agent can create a published KB article."""
    cat = db_session.query(Category).first()
    payload = {
        "title": "VPN Configuration and Troubleshooting",
        "summary": "How to configure OpenVPN on macOS and Windows.",
        "content": "Step 1: Download client. Step 2: Import config. Step 3: Connect with SSO.",
        "category_id": cat.id,
        "is_published": True,
        "tags": ["vpn", "network", "remote"],
    }
    response = client.post("/api/v1/kb/articles", json=payload, headers=agent_auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "VPN Configuration and Troubleshooting"
    assert data["slug"] == "vpn-configuration-and-troubleshooting"
    assert data["is_published"] is True
    assert "vpn" in data["tags"]
    assert data["author"]["role"] == UserRole.AGENT


def test_create_kb_article_by_admin(client, admin_auth_headers, db_session):
    """Admin can create a draft KB article."""
    payload = {
        "title": "Internal Firewall Policies",
        "summary": "Draft firewall guide.",
        "content": "Confidential firewall policies for corporate network.",
        "is_published": False,
        "tags": "security,firewall",
    }
    response = client.post("/api/v1/kb/articles", json=payload, headers=admin_auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["is_published"] is False
    assert data["slug"] == "internal-firewall-policies"


def test_create_kb_article_forbidden_for_user(client, user_auth_headers):
    """Regular end-user cannot create KB articles (RBAC 403)."""
    payload = {
        "title": "User Created Guide",
        "content": "This should not be allowed by RBAC.",
        "is_published": True,
    }
    response = client.post("/api/v1/kb/articles", json=payload, headers=user_auth_headers)
    assert response.status_code == 403


def test_get_kb_article_by_slug_and_id(client, user_auth_headers, agent_auth_headers, db_session):
    """Verify article can be fetched by ID or slug."""
    payload = {
        "title": "Email Setup in Outlook",
        "content": "Enter IMAP and SMTP server settings to configure Outlook.",
        "is_published": True,
    }
    create_res = client.post("/api/v1/kb/articles", json=payload, headers=agent_auth_headers)
    art_id = create_res.json()["id"]
    art_slug = create_res.json()["slug"]

    # By ID
    res_by_id = client.get(f"/api/v1/kb/articles/{art_id}", headers=user_auth_headers)
    assert res_by_id.status_code == 200
    assert res_by_id.json()["id"] == art_id

    # By Slug
    res_by_slug = client.get(f"/api/v1/kb/articles/{art_slug}", headers=user_auth_headers)
    assert res_by_slug.status_code == 200
    assert res_by_slug.json()["slug"] == art_slug


def test_draft_visibility_rbac(client, user_auth_headers, agent_auth_headers, admin_auth_headers):
    """Unpublished/draft articles are hidden from users but accessible to staff."""
    payload = {
        "title": "Upcoming WiFi Upgrades 2026",
        "content": "Draft plans for replacing enterprise access points.",
        "is_published": False,
    }
    create_res = client.post("/api/v1/kb/articles", json=payload, headers=agent_auth_headers)
    art_id = create_res.json()["id"]
    art_slug = create_res.json()["slug"]

    # Regular user cannot access draft detail
    res_user = client.get(f"/api/v1/kb/articles/{art_id}", headers=user_auth_headers)
    assert res_user.status_code == 404

    # Staff can access draft detail
    res_agent = client.get(f"/api/v1/kb/articles/{art_id}", headers=agent_auth_headers)
    assert res_agent.status_code == 200
    assert res_agent.json()["is_published"] is False

    # User listing only shows published articles
    list_user = client.get("/api/v1/kb/articles", headers=user_auth_headers)
    assert list_user.status_code == 200
    slugs = [item["slug"] for item in list_user.json()["items"]]
    assert art_slug not in slugs

    # Staff listing with is_published=False includes the draft
    list_agent = client.get("/api/v1/kb/articles?is_published=false", headers=agent_auth_headers)
    assert list_agent.status_code == 200
    agent_slugs = [item["slug"] for item in list_agent.json()["items"]]
    assert art_slug in agent_slugs


def test_update_kb_article(client, agent_auth_headers, user_auth_headers):
    """Staff can update articles; regular users are forbidden."""
    create_res = client.post(
        "/api/v1/kb/articles",
        json={"title": "Printer Troubleshooting", "content": "Initial printer troubleshooting steps.", "is_published": True},
        headers=agent_auth_headers,
    )
    art_id = create_res.json()["id"]

    # Update as agent
    update_res = client.patch(
        f"/api/v1/kb/articles/{art_id}",
        json={"title": "Printer Troubleshooting v2", "content": "Updated restart and spooler steps."},
        headers=agent_auth_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Printer Troubleshooting v2"

    # User update attempt
    user_update = client.patch(
        f"/api/v1/kb/articles/{art_id}",
        json={"title": "Hacked Title"},
        headers=user_auth_headers,
    )
    assert user_update.status_code == 403


def test_delete_kb_article_rbac(client, admin_auth_headers, agent_auth_headers, user_auth_headers):
    """Only Admin can delete articles; Agents and Users are forbidden."""
    create_res = client.post(
        "/api/v1/kb/articles",
        json={"title": "Temporary Article", "content": "Content to be deleted.", "is_published": True},
        headers=agent_auth_headers,
    )
    art_id = create_res.json()["id"]

    # User cannot delete
    res_user = client.delete(f"/api/v1/kb/articles/{art_id}", headers=user_auth_headers)
    assert res_user.status_code == 403

    # Agent cannot delete
    res_agent = client.delete(f"/api/v1/kb/articles/{art_id}", headers=agent_auth_headers)
    assert res_agent.status_code == 403

    # Admin can delete
    res_admin = client.delete(f"/api/v1/kb/articles/{art_id}", headers=admin_auth_headers)
    assert res_admin.status_code == 204

    # Verify gone
    res_check = client.get(f"/api/v1/kb/articles/{art_id}", headers=admin_auth_headers)
    assert res_check.status_code == 404


def test_slug_collision_resolution(client, agent_auth_headers):
    """Creating articles with duplicate titles generates unique auto-incremented slugs."""
    res1 = client.post(
        "/api/v1/kb/articles",
        json={"title": "Password Reset Guide", "content": "Instructions for reset.", "is_published": True},
        headers=agent_auth_headers,
    )
    res2 = client.post(
        "/api/v1/kb/articles",
        json={"title": "Password Reset Guide", "content": "Duplicate title article.", "is_published": True},
        headers=agent_auth_headers,
    )
    assert res1.status_code == 201
    assert res2.status_code == 201
    assert res1.json()["slug"] == "password-reset-guide"
    assert res2.json()["slug"] == "password-reset-guide-2"


def test_mark_article_helpful(client, user_auth_headers, agent_auth_headers):
    """Users and staff can upvote helpfulness count."""
    create_res = client.post(
        "/api/v1/kb/articles",
        json={"title": "Zoom Audio Setup", "content": "How to select correct audio input in Zoom.", "is_published": True},
        headers=agent_auth_headers,
    )
    art_id = create_res.json()["id"]

    vote_res = client.post(f"/api/v1/kb/articles/{art_id}/helpful", headers=user_auth_headers)
    assert vote_res.status_code == 200
    assert vote_res.json()["helpful_count"] == 1


def test_kb_search_endpoint(client, user_auth_headers, agent_auth_headers):
    """Search endpoint matches keywords, scores relevance, and returns snippets."""
    client.post(
        "/api/v1/kb/articles",
        json={
            "title": "MacOS Wi-Fi Connection Guide",
            "summary": "Fixing 802.1x enterprise network issues on Apple laptops.",
            "content": "If your MacBook cannot connect to corporate Wi-Fi, remove the 802.1x profile and reconnect.",
            "tags": "mac,wifi,network,apple",
            "is_published": True,
        },
        headers=agent_auth_headers,
    )

    search_res = client.get("/api/v1/kb/search?q=macbook+wifi", headers=user_auth_headers)
    assert search_res.status_code == 200
    data = search_res.json()
    assert data["total"] >= 1
    top_match = data["items"][0]
    assert "MacOS Wi-Fi" in top_match["title"]
    assert top_match["relevance_score"] > 0.3
    assert "snippet" in top_match
