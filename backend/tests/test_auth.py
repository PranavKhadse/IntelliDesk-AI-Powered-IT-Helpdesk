import pytest
from fastapi import status


def test_register_user_success(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@company.com",
            "password": "SecurePassword123!",
            "full_name": "New Employee",
            "department": "Sales"
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "newuser@company.com"
    assert data["full_name"] == "New Employee"
    assert data["role"] == "user"
    assert "id" in data


def test_register_duplicate_email_fails(client, test_user):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user.email,
            "password": "AnotherPassword123!",
            "full_name": "Duplicate User",
            "department": "Engineering"
        }
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["error_code"] == "CONFLICT"


def test_login_success(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "TestPass123!"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "WrongPassword!"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_me_authenticated(client, test_user, user_auth_headers):
    response = client.get("/api/v1/auth/me", headers=user_auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email
    assert data["role"] == "user"


def test_get_me_unauthenticated(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
