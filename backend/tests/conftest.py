import os
import pytest
from typing import Generator

# Set test environment variables before application imports
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-execution-only-32bytes"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app

from app.core.database import Base, get_db
from app.core.security import get_password_hash, create_access_token
from app.models.user import User, UserRole
from app.models.ticket import Category

# In-memory test SQLite engine
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator:
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        # Seed standard test category
        cat = Category(name="Hardware", description="Test Category", default_sla_hours=12, is_active=True)
        session.add(cat)
        session.commit()
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session) -> Generator:
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session) -> User:
    user = User(
        email="testuser@company.com",
        hashed_password=get_password_hash("TestPass123!"),
        full_name="Test User",
        role=UserRole.USER,
        department="Finance",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_agent(db_session) -> User:
    agent = User(
        email="testagent@intellidesk.com",
        hashed_password=get_password_hash("AgentPass123!"),
        full_name="Test Agent",
        role=UserRole.AGENT,
        department="IT Operations",
        is_active=True
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


@pytest.fixture
def test_admin(db_session) -> User:
    admin = User(
        email="testadmin@intellidesk.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Test Admin",
        role=UserRole.ADMIN,
        department="IT Operations",
        is_active=True
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def user_auth_headers(test_user) -> dict:
    token = create_access_token({"sub": test_user.id, "email": test_user.email, "role": test_user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def agent_auth_headers(test_agent) -> dict:
    token = create_access_token({"sub": test_agent.id, "email": test_agent.email, "role": test_agent.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(test_admin) -> dict:
    token = create_access_token({"sub": test_admin.id, "email": test_admin.email, "role": test_admin.role})
    return {"Authorization": f"Bearer {token}"}
