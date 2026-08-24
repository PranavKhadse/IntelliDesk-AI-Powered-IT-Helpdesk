from datetime import datetime, timezone, timedelta
from app.models.ticket import Ticket, TicketPriority, TicketStatus, Category
from app.models.comment import TicketComment, CommentType
from app.models.sla_policy import SLAPolicy
from app.models.user import UserRole
from app.schemas.sla import SLAState, FirstResponseStatus
from app.services.sla_service import calculate_ticket_sla_metrics, get_effective_sla_policy


def test_default_sla_policy_resolution_targets(db_session):
    """Verify default SLA policy fallbacks for all standard priority levels."""
    p_name, fr_h, res_h, warn_pct, esc_pct = get_effective_sla_policy(db_session, TicketPriority.CRITICAL, None)
    assert fr_h == 1.0
    assert res_h == 4.0
    assert warn_pct == 0.75
    assert esc_pct == 0.90

    p_name, fr_h, res_h, _, _ = get_effective_sla_policy(db_session, TicketPriority.HIGH, None)
    assert fr_h == 2.0
    assert res_h == 8.0

    p_name, fr_h, res_h, _, _ = get_effective_sla_policy(db_session, TicketPriority.MEDIUM, None)
    assert fr_h == 4.0
    assert res_h == 24.0

    p_name, fr_h, res_h, _, _ = get_effective_sla_policy(db_session, TicketPriority.LOW, None)
    assert fr_h == 8.0
    assert res_h == 48.0


def test_custom_category_sla_policy_override(db_session):
    """Custom SLAPolicy matching category and priority overrides defaults."""
    cat = Category(name="Security Incident", default_sla_hours=2)
    db_session.add(cat)
    db_session.commit()

    policy = SLAPolicy(
        name="Security Critical Policy",
        category_id=cat.id,
        priority=TicketPriority.CRITICAL,
        first_response_hours=0.25,
        resolution_hours=1.0,
        warning_threshold_pct=0.60,
        escalation_threshold_pct=0.80,
    )
    db_session.add(policy)
    db_session.commit()

    p_name, fr_h, res_h, warn_pct, esc_pct = get_effective_sla_policy(db_session, TicketPriority.CRITICAL, cat.id)
    assert p_name == "Security Critical Policy"
    assert fr_h == 0.25
    assert res_h == 1.0
    assert warn_pct == 0.60
    assert esc_pct == 0.80


def test_first_response_sla_calculation(db_session, test_user, test_agent):
    """Verify first response SLA status: pending, met, and breached."""
    base_time = datetime(2026, 8, 24, 10, 0, 0, tzinfo=timezone.utc)

    # 1. New ticket, no comments yet (after 30 min, 1h target -> PENDING)
    ticket = Ticket(
        ticket_number="IT-SLA-1",
        title="VPN issue",
        description="Cannot connect",
        priority=TicketPriority.CRITICAL,  # 1h first response target
        status=TicketStatus.OPEN,
        creator_id=test_user.id,
        created_at=base_time,
    )
    db_session.add(ticket)
    db_session.commit()

    metrics = calculate_ticket_sla_metrics(db_session, ticket, now_dt=base_time + timedelta(minutes=30))
    assert metrics.first_response_status == FirstResponseStatus.PENDING

    # 2. Past first response deadline (90 min later with no comment -> BREACHED_PENDING)
    metrics_breached = calculate_ticket_sla_metrics(db_session, ticket, now_dt=base_time + timedelta(minutes=90))
    assert metrics_breached.first_response_status == FirstResponseStatus.BREACHED_PENDING
    assert metrics_breached.is_breached == True

    # 3. User comment does NOT count as staff first response
    user_comment = TicketComment(
        ticket_id=ticket.id,
        author_id=test_user.id,
        comment_type=CommentType.PUBLIC,
        content="Any updates on this?",
        created_at=base_time + timedelta(minutes=20)
    )
    db_session.add(user_comment)
    db_session.commit()
    db_session.refresh(ticket)

    metrics_user_comment = calculate_ticket_sla_metrics(db_session, ticket, now_dt=base_time + timedelta(minutes=90))
    assert metrics_user_comment.first_response_status == FirstResponseStatus.BREACHED_PENDING

    # 4. Agent comments within 45 minutes -> MET
    agent_comment = TicketComment(
        ticket_id=ticket.id,
        author_id=test_agent.id,
        comment_type=CommentType.PUBLIC,
        content="We are investigating your VPN credentials.",
        created_at=base_time + timedelta(minutes=45)
    )
    db_session.add(agent_comment)
    db_session.commit()
    db_session.refresh(ticket)

    metrics_staff_met = calculate_ticket_sla_metrics(db_session, ticket, now_dt=base_time + timedelta(minutes=90))
    assert metrics_staff_met.first_response_status == FirstResponseStatus.MET
    assert metrics_staff_met.first_response_elapsed_seconds == 45 * 60.0


def test_sla_state_transitions_on_track_at_risk_breached(db_session, test_user, test_agent):
    """Test resolution SLA state progression: ON_TRACK -> AT_RISK -> BREACHED."""
    base_time = datetime(2026, 8, 24, 8, 0, 0, tzinfo=timezone.utc)

    # 4h resolution target (Critical)
    ticket = Ticket(
        ticket_number="IT-SLA-2",
        title="Server Down",
        description="Production DB down",
        priority=TicketPriority.CRITICAL,
        status=TicketStatus.IN_PROGRESS,
        creator_id=test_user.id,
        created_at=base_time,
    )
    # Add staff comment so first response is met
    staff_comm = TicketComment(
        ticket_id=ticket.id,
        author_id=test_agent.id,
        comment_type=CommentType.PUBLIC,
        content="Looking into it now.",
        created_at=base_time + timedelta(minutes=10)
    )
    ticket.comments = [staff_comm]
    db_session.add(ticket)
    db_session.commit()

    # 1. 1 hour in (25% consumed) -> ON_TRACK
    m1 = calculate_ticket_sla_metrics(db_session, ticket, now_dt=base_time + timedelta(hours=1))
    assert m1.sla_state == SLAState.ON_TRACK
    assert m1.percentage_consumed == 25.0
    assert not m1.is_at_risk
    assert not m1.is_breached

    # 2. 3 hours 10 mins in (3.16 / 4h = 79.2% consumed >= 75% warning) -> AT_RISK
    m2 = calculate_ticket_sla_metrics(db_session, ticket, now_dt=base_time + timedelta(hours=3, minutes=10))
    assert m2.sla_state == SLAState.AT_RISK
    assert m2.is_at_risk == True
    assert not m2.is_breached

    # 3. 4 hours 15 mins in (> 100% consumed) -> BREACHED
    m3 = calculate_ticket_sla_metrics(db_session, ticket, now_dt=base_time + timedelta(hours=4, minutes=15))
    assert m3.sla_state == SLAState.BREACHED
    assert m3.is_breached == True
    assert m3.remaining_seconds == 0.0


def test_ticket_pending_customer_is_paused(db_session, test_user):
    """Tickets in pending_customer status show PAUSED SLA state."""
    base_time = datetime(2026, 8, 24, 8, 0, 0, tzinfo=timezone.utc)
    ticket = Ticket(
        ticket_number="IT-SLA-3",
        title="Laptop Setup",
        description="Awaiting customer details",
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.PENDING_CUSTOMER,
        creator_id=test_user.id,
        created_at=base_time,
    )
    db_session.add(ticket)
    db_session.commit()

    metrics = calculate_ticket_sla_metrics(db_session, ticket, now_dt=base_time + timedelta(hours=2))
    assert metrics.sla_state == SLAState.PAUSED


def test_resolved_ticket_sla_states(db_session, test_user, test_agent):
    """Resolved tickets correctly classify as RESOLVED_MET or RESOLVED_BREACHED."""
    base_time = datetime(2026, 8, 24, 8, 0, 0, tzinfo=timezone.utc)

    # 1. Resolved within 2 hours of a 4h SLA -> RESOLVED_MET
    ticket_met = Ticket(
        ticket_number="IT-SLA-4",
        title="Password Reset",
        description="Reset needed",
        priority=TicketPriority.CRITICAL,  # 4h target
        status=TicketStatus.RESOLVED,
        creator_id=test_user.id,
        created_at=base_time,
        resolved_at=base_time + timedelta(hours=2),
    )
    db_session.add(ticket_met)
    db_session.commit()

    staff_comm1 = TicketComment(
        ticket_id=ticket_met.id,
        author_id=test_agent.id,
        comment_type=CommentType.PUBLIC,
        content="Reset complete.",
        created_at=base_time + timedelta(minutes=15)
    )
    db_session.add(staff_comm1)

    # 2. Resolved in 6 hours of a 4h SLA -> RESOLVED_BREACHED
    ticket_breached = Ticket(
        ticket_number="IT-SLA-5",
        title="Hard Drive Replacement",
        description="Drive crashed",
        priority=TicketPriority.CRITICAL,  # 4h target
        status=TicketStatus.RESOLVED,
        creator_id=test_user.id,
        created_at=base_time,
        resolved_at=base_time + timedelta(hours=6),
    )
    db_session.add(ticket_breached)
    db_session.commit()

    staff_comm2 = TicketComment(
        ticket_id=ticket_breached.id,
        author_id=test_agent.id,
        comment_type=CommentType.PUBLIC,
        content="Drive replacement started.",
        created_at=base_time + timedelta(minutes=15)
    )
    db_session.add(staff_comm2)
    db_session.commit()
    db_session.refresh(ticket_met)
    db_session.refresh(ticket_breached)

    m_met = calculate_ticket_sla_metrics(db_session, ticket_met, now_dt=base_time + timedelta(hours=10))
    assert m_met.sla_state == SLAState.RESOLVED_MET
    assert not m_met.is_breached

    m_breached = calculate_ticket_sla_metrics(db_session, ticket_breached, now_dt=base_time + timedelta(hours=10))
    assert m_breached.sla_state == SLAState.RESOLVED_BREACHED
    assert m_breached.is_breached == True


def test_get_ticket_sla_endpoint(client, db_session, test_user, test_agent, test_admin, user_auth_headers, agent_auth_headers):
    """Verify GET /api/v1/tickets/{id}/sla RBAC and response format."""
    ticket = Ticket(
        ticket_number="IT-SLA-6",
        title="Email sync issue",
        description="Sync failing on Outlook",
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
        creator_id=test_user.id,
    )
    db_session.add(ticket)
    db_session.commit()

    # 1. Unauthenticated request -> 401
    res_unauth = client.get(f"/api/v1/tickets/{ticket.id}/sla")
    assert res_unauth.status_code == 401

    # 2. Ticket owner -> 200 OK with SLA metrics
    res_owner = client.get(f"/api/v1/tickets/{ticket.id}/sla", headers=user_auth_headers)
    assert res_owner.status_code == 200
    data = res_owner.json()
    assert data["ticket_id"] == ticket.id
    assert "sla_metrics" in data
    assert data["sla_metrics"]["sla_state"] in [SLAState.ON_TRACK.value, SLAState.AT_RISK.value, SLAState.BREACHED.value]

    # 3. Support Agent -> 200 OK
    res_agent = client.get(f"/api/v1/tickets/{ticket.id}/sla", headers=agent_auth_headers)
    assert res_agent.status_code == 200

    # 4. Another user -> 403 Forbidden
    other_user = UserRole.USER
    other_user_headers = {"Authorization": user_auth_headers["Authorization"]}  # owner
    # Create another user
    from app.models.user import User
    from app.core.security import create_access_token
    user2 = User(
        email="other@user.com",
        hashed_password="pw",
        full_name="Other User",
        role=UserRole.USER,
        department="HR",
        is_active=True,
    )
    db_session.add(user2)
    db_session.commit()
    user2_token = create_access_token({"sub": user2.id, "email": user2.email, "role": user2.role})
    res_forbidden = client.get(f"/api/v1/tickets/{ticket.id}/sla", headers={"Authorization": f"Bearer {user2_token}"})
    assert res_forbidden.status_code == 403


def test_sla_policy_crud_endpoints(client, db_session, admin_auth_headers, agent_auth_headers, user_auth_headers):
    """Verify SLA policy CRUD endpoints with Admin RBAC enforcement."""
    # 1. Admin creates policy -> 201 Created
    create_payload = {
        "name": "Executive VIP SLA",
        "description": "High-priority executive support",
        "priority": "critical",
        "first_response_hours": 0.5,
        "resolution_hours": 2.0,
        "warning_threshold_pct": 0.50,
        "escalation_threshold_pct": 0.80,
        "is_active": True
    }
    res_create = client.post("/api/v1/sla/policies", json=create_payload, headers=admin_auth_headers)
    assert res_create.status_code == 201
    policy_id = res_create.json()["id"]
    assert res_create.json()["name"] == "Executive VIP SLA"

    # 2. Non-admin user cannot create policy -> 403 Forbidden
    res_user_create = client.post("/api/v1/sla/policies", json=create_payload, headers=user_auth_headers)
    assert res_user_create.status_code == 403

    # 3. Agent can list policies -> 200 OK
    res_list = client.get("/api/v1/sla/policies", headers=agent_auth_headers)
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1

    # 4. Admin updates policy -> 200 OK
    res_update = client.put(f"/api/v1/sla/policies/{policy_id}", json={"resolution_hours": 3.0}, headers=admin_auth_headers)
    assert res_update.status_code == 200
    assert res_update.json()["resolution_hours"] == 3.0

    # 5. Admin deletes policy -> 204 No Content
    res_del = client.delete(f"/api/v1/sla/policies/{policy_id}", headers=admin_auth_headers)
    assert res_del.status_code == 204
