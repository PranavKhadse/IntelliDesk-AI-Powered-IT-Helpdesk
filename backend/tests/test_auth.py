from datetime import datetime, timedelta, timezone
from jose import jwt
import pytest
from fastapi import status
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token


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


def test_get_me_with_refresh_token_rejected(client, test_user):
    """Ensure refresh tokens cannot be used to authenticate access-token protected endpoints."""
    refresh_token = create_refresh_token({"sub": test_user.id, "email": test_user.email, "role": test_user.role})
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh_token}"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_me_with_invalid_token_type_rejected(client, test_user):
    """Ensure tokens with an invalid or unexpected type claim are rejected."""
    payload = {
        "sub": test_user.id,
        "email": test_user.email,
        "role": test_user.role,
        "type": "invalid_type",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15)
    }
    invalid_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {invalid_token}"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_refresh_endpoint_rejects_access_token(client, test_user):
    """Ensure access tokens cannot be exchanged at the refresh token endpoint."""
    access_token = create_access_token({"sub": test_user.id, "email": test_user.email, "role": test_user.role})
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_decode_token_type_validation(test_user):
    """Unit tests for decode_token verifying expected_type matching and backward compatibility."""
    access_token = create_access_token({"sub": test_user.id})
    refresh_token = create_refresh_token({"sub": test_user.id})

    # Valid matching types
    decoded_access = decode_token(access_token, expected_type="access")
    assert decoded_access["sub"] == test_user.id
    assert decoded_access["type"] == "access"

    decoded_refresh = decode_token(refresh_token, expected_type="refresh")
    assert decoded_refresh["sub"] == test_user.id
    assert decoded_refresh["type"] == "refresh"

    # Backward compatibility when expected_type is None
    assert decode_token(access_token)["sub"] == test_user.id
    assert decode_token(refresh_token)["sub"] == test_user.id

    # Mismatched types rejected with ValueError
    with pytest.raises(ValueError, match="Invalid token type"):
        decode_token(refresh_token, expected_type="access")

    with pytest.raises(ValueError, match="Invalid token type"):
        decode_token(access_token, expected_type="refresh")

