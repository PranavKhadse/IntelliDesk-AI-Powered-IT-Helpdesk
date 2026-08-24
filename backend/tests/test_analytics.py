from datetime import datetime, timezone, timedelta
from app.models.user import User, UserRole
from app.models.ticket import Ticket, TicketPriority, TicketStatus, Category
from app.models.comment import TicketComment, CommentType
from app.models.audit_log import AuditLog, AuditAction
from app.models.kb_article import KBArticle
from app.services.analytics_service import parse_analytics_date_range


def test_parse_analytics_date_range():
    """Verify date range parsing for presets and custom boundaries."""
    base_now = datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc)

    # 7d preset
    s7, e7, p7 = parse_analytics_date_range("7d", now_dt=base_now)
    assert p7 == "7d"
    assert (e7 - s7).days == 7

    # 30d preset
    s30, e30, p30 = parse_analytics_date_range("30d", now_dt=base_now)
    assert p30 == "30d"
    assert (e30 - s30).days == 30

    # 90d preset
    s90, e90, p90 = parse_analytics_date_range("90d", now_dt=base_now)
    assert p90 == "90d"
    assert (e90 - s90).days == 90

    # all preset
    s_all, e_all, p_all = parse_analytics_date_range("all", now_dt=base_now)
    assert p_all == "all"
    assert s_all.year == 2020

    # custom bounds
    custom_s = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
    custom_e = datetime(2026, 8, 15, 0, 0, 0, tzinfo=timezone.utc)
    s_c, e_c, p_c = parse_analytics_date_range(start_date=custom_s, end_date=custom_e, now_dt=base_now)
    assert p_c == "custom"
    assert s_c == custom_s
    assert e_c == custom_e


def test_analytics_rbac(client, admin_auth_headers, agent_auth_headers, user_auth_headers):
    """Admin and Agent have access (200 OK); regular User is forbidden (403); Unauthenticated is 401."""
    # 1. Admin access -> 200 OK
    res_admin = client.get("/api/v1/analytics/dashboard", headers=admin_auth_headers)
    assert res_admin.status_code == 200
    assert res_admin.json()["role"] == "admin"

    # 2. Agent access -> 200 OK
    res_agent = client.get("/api/v1/analytics/dashboard", headers=agent_auth_headers)
    assert res_agent.status_code == 200
    assert res_agent.json()["role"] == "agent"

    # 3. User access -> 403 Forbidden
    res_user = client.get("/api/v1/analytics/dashboard", headers=user_auth_headers)
    assert res_user.status_code == 403

    # 4. Unauthenticated -> 401 Unauthorized
    res_unauth = client.get("/api/v1/analytics/dashboard")
    assert res_unauth.status_code == 401


def test_analytics_empty_dataset_handling(client, admin_auth_headers):
    """Empty database returns zeroed metrics safely without runtime errors."""
    res = client.get("/api/v1/analytics/dashboard?preset=30d", headers=admin_auth_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["volume_metrics"]["total_tickets"] == 0
    assert data["volume_metrics"]["resolution_rate_pct"] == 0.0
    assert data["resolution_metrics"]["avg_resolution_hours"] == 0.0
    assert data["first_response_metrics"]["first_response_compliance_pct"] == 0.0
    assert data["sla_metrics"]["compliance_rate_pct"] == 0.0


def test_analytics_ticket_volume_and_trend(client, db_session, test_user, test_agent, admin_auth_headers):
    """Verify ticket volume aggregations, backlog calculation, and trend data."""
    base_time = datetime.now(timezone.utc) - timedelta(days=5)

    # 1 Open ticket
    t1 = Ticket(
        ticket_number="IT-ANA-1",
        title="Open Ticket",
        description="Issue 1",
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
        creator_id=test_user.id,
        created_at=base_time,
    )
    # 1 In Progress ticket
    t2 = Ticket(
        ticket_number="IT-ANA-2",
        title="In Prog Ticket",
        description="Issue 2",
        status=TicketStatus.IN_PROGRESS,
        priority=TicketPriority.HIGH,
        creator_id=test_user.id,
        created_at=base_time + timedelta(days=1),
    )
    # 1 Resolved ticket
    t3 = Ticket(
        ticket_number="IT-ANA-3",
        title="Resolved Ticket",
        description="Issue 3",
        status=TicketStatus.RESOLVED,
        priority=TicketPriority.LOW,
        creator_id=test_user.id,
        created_at=base_time + timedelta(days=2),
        resolved_at=base_time + timedelta(days=2, hours=3),
    )
    db_session.add_all([t1, t2, t3])
    db_session.commit()

    res = client.get("/api/v1/analytics/dashboard?preset=7d", headers=admin_auth_headers)
    assert res.status_code == 200
    data = res.json()

    vol = data["volume_metrics"]
    assert vol["total_tickets"] >= 3
    assert vol["open_tickets"] >= 1
    assert vol["in_progress_tickets"] >= 1
    assert vol["resolved_tickets"] >= 1
    assert vol["active_backlog"] >= 2
    assert vol["resolution_rate_pct"] > 0.0

    # Trend points should be populated
    assert len(data["volume_trend"]) > 0


def test_analytics_resolution_and_response_metrics(client, db_session, test_user, test_agent, admin_auth_headers):
    """Verify resolution times and first-response metric calculations."""
    base_time = datetime.now(timezone.utc) - timedelta(days=3)

    # Ticket resolved in 4 hours
    t1 = Ticket(
        ticket_number="IT-ANA-4",
        title="Resolved Fast",
        description="Quick fix",
        status=TicketStatus.RESOLVED,
        priority=TicketPriority.MEDIUM,
        creator_id=test_user.id,
        created_at=base_time,
        resolved_at=base_time + timedelta(hours=4),
    )
    db_session.add(t1)
    db_session.commit()

    # Add staff response at 1 hour
    comm = TicketComment(
        ticket_id=t1.id,
        author_id=test_agent.id,
        comment_type=CommentType.PUBLIC,
        content="Looking at it now",
        created_at=base_time + timedelta(hours=1),
    )
    db_session.add(comm)
    db_session.commit()

    res = client.get("/api/v1/analytics/dashboard?preset=7d", headers=admin_auth_headers)
    assert res.status_code == 200
    data = res.json()

    res_metrics = data["resolution_metrics"]
    assert res_metrics["total_resolved_evaluated"] >= 1
    assert res_metrics["avg_resolution_hours"] > 0.0

    fr_metrics = data["first_response_metrics"]
    assert fr_metrics["total_responses_evaluated"] >= 1
    assert fr_metrics["first_response_compliance_pct"] == 100.0


def test_analytics_sla_metrics_summary(client, db_session, test_user, admin_auth_headers):
    """Verify SLA compliance summary and breach metrics."""
    base_time = datetime.now(timezone.utc) - timedelta(days=2)

    # Breached ticket (created 2 days ago with Critical 4h SLA)
    t_breached = Ticket(
        ticket_number="IT-ANA-5",
        title="Production Outage",
        description="Critical outage",
        status=TicketStatus.OPEN,
        priority=TicketPriority.CRITICAL,  # 4h resolution target
        creator_id=test_user.id,
        created_at=base_time,
    )
    db_session.add(t_breached)
    db_session.commit()

    res = client.get("/api/v1/analytics/sla?preset=7d", headers=admin_auth_headers)
    assert res.status_code == 200
    sla_data = res.json()

    assert sla_data["total_evaluated"] >= 1
    assert sla_data["breached_count"] >= 1
    assert sla_data["breach_rate_pct"] > 0.0


def test_analytics_category_and_priority_distributions(client, db_session, test_user, admin_auth_headers):
    """Verify category and priority distribution breakdown."""
    cat = Category(name="DevOps Infrastructure", default_sla_hours=12)
    db_session.add(cat)
    db_session.commit()

    t = Ticket(
        ticket_number="IT-ANA-6",
        title="CI Pipeline failed",
        description="Jenkins runner error",
        status=TicketStatus.OPEN,
        priority=TicketPriority.HIGH,
        category_id=cat.id,
        creator_id=test_user.id,
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    db_session.add(t)
    db_session.commit()

    res = client.get("/api/v1/analytics/dashboard?preset=7d", headers=admin_auth_headers)
    assert res.status_code == 200
    data = res.json()

    cat_list = data["category_distribution"]
    devops_item = next((c for c in cat_list if c["category_name"] == "DevOps Infrastructure"), None)
    assert devops_item is not None
    assert devops_item["ticket_count"] >= 1

    prio_list = data["priority_distribution"]
    high_item = next((p for p in prio_list if p["priority"] == "high"), None)
    assert high_item is not None
    assert high_item["ticket_count"] >= 1


def test_analytics_agent_workload(client, db_session, test_user, test_agent, admin_auth_headers):
    """Verify agent workload metrics and active assignments."""
    t = Ticket(
        ticket_number="IT-ANA-7",
        title="Assigned Task",
        description="Assigned to agent",
        status=TicketStatus.IN_PROGRESS,
        priority=TicketPriority.MEDIUM,
        creator_id=test_user.id,
        assignee_id=test_agent.id,
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db_session.add(t)
    db_session.commit()

    res = client.get("/api/v1/analytics/workload?preset=7d", headers=admin_auth_headers)
    assert res.status_code == 200
    workload = res.json()

    agent_entry = next((w for w in workload if w["agent_id"] == test_agent.id), None)
    assert agent_entry is not None
    assert agent_entry["active_tickets_count"] >= 1


def test_analytics_escalation_and_ai_metrics(client, db_session, test_user, test_agent, admin_auth_headers):
    """Verify AI adoption metrics and escalation acceptance stats from AuditLog."""
    t = Ticket(
        ticket_number="IT-ANA-8",
        title="AI Triaged Ticket",
        description="Testing triage log",
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
        creator_id=test_user.id,
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    db_session.add(t)
    db_session.commit()

    # Log AI Triage and Acceptance
    log_triage = AuditLog(
        ticket_id=t.id,
        actor_id=test_agent.id,
        action=AuditAction.AI_TRIAGED,
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    log_accepted = AuditLog(
        ticket_id=t.id,
        actor_id=test_agent.id,
        action=AuditAction.AI_RECOMMENDATION_ACCEPTED,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=45),
    )
    # Log SLA Risk and Escalation Rejected
    log_sla_risk = AuditLog(
        ticket_id=t.id,
        actor_id=test_agent.id,
        action=AuditAction.AI_SLA_RISK_ASSESSED,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=30),
    )
    log_esc_rej = AuditLog(
        ticket_id=t.id,
        actor_id=test_agent.id,
        action=AuditAction.AI_ESCALATION_REJECTED,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=15),
    )
    db_session.add_all([log_triage, log_accepted, log_sla_risk, log_esc_rej])
    db_session.commit()

    res = client.get("/api/v1/analytics/dashboard?preset=7d", headers=admin_auth_headers)
    assert res.status_code == 200
    data = res.json()

    ai_data = data["ai_adoption"]
    assert ai_data["total_triage_generated"] >= 1
    assert ai_data["triage_accepted"] >= 1
    assert ai_data["triage_acceptance_rate_pct"] == 100.0
    assert ai_data["total_sla_risk_evaluations"] >= 1

    esc_data = data["escalation_metrics"]
    assert esc_data["rejected_count"] >= 1


def test_analytics_read_only_immutability(client, db_session, test_user, test_agent, admin_auth_headers):
    """Querying operations analytics does NOT mutate tickets, comments, or audit records."""
    t = Ticket(
        ticket_number="IT-ANA-9",
        title="Immutability Ticket",
        description="Should remain untouched",
        status=TicketStatus.OPEN,
        priority=TicketPriority.LOW,
        creator_id=test_user.id,
        assignee_id=test_agent.id,
    )
    db_session.add(t)
    db_session.commit()

    initial_tickets_count = db_session.query(Ticket).count()
    initial_audit_count = db_session.query(AuditLog).count()

    # Call dashboard
    res = client.get("/api/v1/analytics/dashboard", headers=admin_auth_headers)
    assert res.status_code == 200

    # Ensure no records added or changed
    assert db_session.query(Ticket).count() == initial_tickets_count
    assert db_session.query(AuditLog).count() == initial_audit_count
    db_session.refresh(t)
    assert t.status == TicketStatus.OPEN
    assert t.priority == TicketPriority.LOW
