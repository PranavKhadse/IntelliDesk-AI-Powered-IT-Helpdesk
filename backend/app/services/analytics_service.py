import statistics
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.exceptions import ForbiddenError
from app.models.user import User, UserRole
from app.models.ticket import Ticket, TicketPriority, TicketStatus, Category
from app.models.comment import TicketComment, CommentType
from app.models.audit_log import AuditLog, AuditAction
from app.models.kb_article import KBArticle
from app.services.sla_service import calculate_ticket_sla_metrics, get_effective_sla_policy
from app.schemas.sla import SLAState, FirstResponseStatus
from app.schemas.analytics import (
    AnalyticsDateRange,
    TicketVolumeMetrics,
    VolumeTrendPoint,
    ResolutionMetrics,
    FirstResponseMetrics,
    SLAMetricsSummary,
    CategoryDistributionItem,
    PriorityDistributionItem,
    AgentWorkloadItem,
    EscalationMetricsSummary,
    AIAdoptionMetrics,
    OperationsAnalyticsDashboardResponse,
)


def parse_analytics_date_range(
    preset: Optional[str] = "30d",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    now_dt: Optional[datetime] = None,
) -> Tuple[datetime, datetime, str]:
    """Parse and normalize date range into timezone-aware UTC datetime boundaries."""
    now_utc = now_dt or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    if start_date is not None or end_date is not None:
        actual_start = start_date or (now_utc - timedelta(days=30))
        actual_end = end_date or now_utc
        if actual_start.tzinfo is None:
            actual_start = actual_start.replace(tzinfo=timezone.utc)
        if actual_end.tzinfo is None:
            actual_end = actual_end.replace(tzinfo=timezone.utc)
        if actual_start > actual_end:
            actual_start, actual_end = actual_end, actual_start
        return actual_start, actual_end, "custom"

    p = (preset or "30d").lower()
    if p == "7d":
        return now_utc - timedelta(days=7), now_utc, "7d"
    elif p == "90d":
        return now_utc - timedelta(days=90), now_utc, "90d"
    elif p == "all":
        return datetime(2020, 1, 1, tzinfo=timezone.utc), now_utc, "all"
    else:
        # Default 30d
        return now_utc - timedelta(days=30), now_utc, "30d"


def compute_ticket_volume_metrics(db: Session, start_dt: datetime, end_dt: datetime) -> TicketVolumeMetrics:
    """Aggregate total ticket counts by status and calculate active backlog and resolution rate."""
    tickets = db.query(Ticket).filter(
        Ticket.created_at >= start_dt,
        Ticket.created_at <= end_dt
    ).all()

    total = len(tickets)
    open_c = sum(1 for t in tickets if t.status == TicketStatus.OPEN)
    in_prog_c = sum(1 for t in tickets if t.status == TicketStatus.IN_PROGRESS)
    pending_c = sum(1 for t in tickets if t.status == TicketStatus.PENDING_CUSTOMER)
    resolved_c = sum(1 for t in tickets if t.status == TicketStatus.RESOLVED)
    closed_c = sum(1 for t in tickets if t.status == TicketStatus.CLOSED)

    active_backlog = open_c + in_prog_c + pending_c
    completed = resolved_c + closed_c
    res_rate = round((completed / total * 100.0), 1) if total > 0 else 0.0

    return TicketVolumeMetrics(
        total_tickets=total,
        open_tickets=open_c,
        in_progress_tickets=in_prog_c,
        pending_customer_tickets=pending_c,
        resolved_tickets=resolved_c,
        closed_tickets=closed_c,
        active_backlog=active_backlog,
        resolution_rate_pct=res_rate,
    )


def compute_volume_trend(db: Session, start_dt: datetime, end_dt: datetime) -> List[VolumeTrendPoint]:
    """Generate chronological timeline bins for created and resolved tickets."""
    created_tickets = db.query(Ticket).filter(
        Ticket.created_at >= start_dt,
        Ticket.created_at <= end_dt
    ).all()

    resolved_tickets = db.query(Ticket).filter(
        Ticket.resolved_at >= start_dt,
        Ticket.resolved_at <= end_dt
    ).all()

    # Collect all dates in range
    date_map: Dict[str, Dict[str, int]] = {}
    
    # Initialize timeline points (if within 90 days, daily bins)
    total_days = max(1, (end_dt.date() - start_dt.date()).days)
    if total_days <= 90:
        curr = start_dt.date()
        while curr <= end_dt.date():
            d_str = curr.strftime("%Y-%m-%d")
            date_map[d_str] = {"created": 0, "resolved": 0}
            curr += timedelta(days=1)

    for t in created_tickets:
        if t.created_at:
            d_str = t.created_at.strftime("%Y-%m-%d")
            if d_str not in date_map:
                date_map[d_str] = {"created": 0, "resolved": 0}
            date_map[d_str]["created"] += 1

    for t in resolved_tickets:
        if t.resolved_at:
            d_str = t.resolved_at.strftime("%Y-%m-%d")
            if d_str not in date_map:
                date_map[d_str] = {"created": 0, "resolved": 0}
            date_map[d_str]["resolved"] += 1

    trend_points: List[VolumeTrendPoint] = []
    for d_str in sorted(date_map.keys()):
        trend_points.append(
            VolumeTrendPoint(
                date=d_str,
                created_count=date_map[d_str]["created"],
                resolved_count=date_map[d_str]["resolved"],
            )
        )

    return trend_points


def compute_resolution_and_response_metrics(
    db: Session, start_dt: datetime, end_dt: datetime
) -> Tuple[ResolutionMetrics, FirstResponseMetrics]:
    """Calculate average and median resolution and first-response durations and compliance."""
    # 1. Resolution Metrics
    resolved_tickets = db.query(Ticket).filter(
        Ticket.created_at >= start_dt,
        Ticket.created_at <= end_dt,
        Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
    ).all()

    res_durations: List[float] = []
    for t in resolved_tickets:
        res_time = t.resolved_at or t.closed_at or t.updated_at
        if res_time and t.created_at:
            t_created = t.created_at.replace(tzinfo=timezone.utc) if t.created_at.tzinfo is None else t.created_at
            t_res = res_time.replace(tzinfo=timezone.utc) if res_time.tzinfo is None else res_time
            diff_hours = max(0.0, (t_res - t_created).total_seconds() / 3600.0)
            res_durations.append(diff_hours)

    if res_durations:
        res_metrics = ResolutionMetrics(
            avg_resolution_hours=round(statistics.mean(res_durations), 2),
            median_resolution_hours=round(statistics.median(res_durations), 2),
            min_resolution_hours=round(min(res_durations), 2),
            max_resolution_hours=round(max(res_durations), 2),
            total_resolved_evaluated=len(res_durations),
        )
    else:
        res_metrics = ResolutionMetrics()

    # 2. First Response Metrics
    all_tickets = db.query(Ticket).filter(
        Ticket.created_at >= start_dt,
        Ticket.created_at <= end_dt,
    ).all()

    fr_durations: List[float] = []
    fr_met_count = 0
    for t in all_tickets:
        t_created = t.created_at.replace(tzinfo=timezone.utc) if t.created_at.tzinfo is None else t.created_at
        staff_comments = [c for c in (t.comments or []) if c.author_id != t.creator_id]
        if staff_comments:
            first_c = min(staff_comments, key=lambda c: c.created_at)
            c_time = first_c.created_at.replace(tzinfo=timezone.utc) if first_c.created_at.tzinfo is None else first_c.created_at
            diff_hours = max(0.0, (c_time - t_created).total_seconds() / 3600.0)
            fr_durations.append(diff_hours)
            
            # Check target from effective policy
            _, target_fr, _, _, _ = get_effective_sla_policy(db, t.priority, t.category_id)
            if diff_hours <= target_fr:
                fr_met_count += 1
        elif t.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
            # One touch resolution counts as met
            res_time = t.resolved_at or t.closed_at or t.updated_at
            if res_time:
                t_res = res_time.replace(tzinfo=timezone.utc) if res_time.tzinfo is None else res_time
                diff_hours = max(0.0, (t_res - t_created).total_seconds() / 3600.0)
                fr_durations.append(diff_hours)
                _, target_fr, _, _, _ = get_effective_sla_policy(db, t.priority, t.category_id)
                if diff_hours <= target_fr:
                    fr_met_count += 1

    if fr_durations:
        fr_metrics = FirstResponseMetrics(
            avg_first_response_hours=round(statistics.mean(fr_durations), 2),
            median_first_response_hours=round(statistics.median(fr_durations), 2),
            first_response_compliance_pct=round((fr_met_count / len(fr_durations) * 100.0), 1),
            total_responses_evaluated=len(fr_durations),
        )
    else:
        fr_metrics = FirstResponseMetrics()

    return res_metrics, fr_metrics


def compute_sla_analytics(
    db: Session, start_dt: datetime, end_dt: datetime, now_dt: Optional[datetime] = None
) -> SLAMetricsSummary:
    """Calculate overall SLA compliance, at-risk, and breach breakdown."""
    tickets = db.query(Ticket).filter(
        Ticket.created_at >= start_dt,
        Ticket.created_at <= end_dt
    ).all()

    total = len(tickets)
    if total == 0:
        return SLAMetricsSummary()

    on_track = 0
    at_risk = 0
    breached = 0
    paused = 0
    res_met = 0
    res_breached = 0

    for t in tickets:
        metrics = calculate_ticket_sla_metrics(db, t, now_dt=now_dt)
        if metrics.sla_state == SLAState.ON_TRACK:
            on_track += 1
        elif metrics.sla_state == SLAState.AT_RISK:
            at_risk += 1
        elif metrics.sla_state == SLAState.BREACHED:
            breached += 1
        elif metrics.sla_state == SLAState.PAUSED:
            paused += 1
        elif metrics.sla_state == SLAState.RESOLVED_MET:
            res_met += 1
        elif metrics.sla_state == SLAState.RESOLVED_BREACHED:
            res_breached += 1

    compliant_total = on_track + res_met + paused
    breached_total = breached + res_breached
    comp_rate = round((compliant_total / total * 100.0), 1)
    breach_rate = round((breached_total / total * 100.0), 1)

    return SLAMetricsSummary(
        total_evaluated=total,
        on_track_count=on_track,
        at_risk_count=at_risk,
        breached_count=breached,
        paused_count=paused,
        resolved_met_count=res_met,
        resolved_breached_count=res_breached,
        compliance_rate_pct=comp_rate,
        breach_rate_pct=breach_rate,
    )


def compute_category_and_priority_distributions(
    db: Session, start_dt: datetime, end_dt: datetime, now_dt: Optional[datetime] = None
) -> Tuple[List[CategoryDistributionItem], List[PriorityDistributionItem]]:
    """Compute category and priority distribution breakdowns with SLA performance."""
    tickets = db.query(Ticket).filter(
        Ticket.created_at >= start_dt,
        Ticket.created_at <= end_dt
    ).all()
    total = len(tickets)

    # Categories
    categories = db.query(Category).all()
    cat_map = {c.id: c.name for c in categories}

    cat_counts: Dict[Optional[int], int] = {}
    cat_compliant: Dict[Optional[int], int] = {}

    for t in tickets:
        cid = t.category_id
        cat_counts[cid] = cat_counts.get(cid, 0) + 1
        m = calculate_ticket_sla_metrics(db, t, now_dt=now_dt)
        if m.sla_state in [SLAState.ON_TRACK, SLAState.RESOLVED_MET, SLAState.PAUSED]:
            cat_compliant[cid] = cat_compliant.get(cid, 0) + 1

    cat_items: List[CategoryDistributionItem] = []
    for cid, count in cat_counts.items():
        name = cat_map.get(cid, "General / Uncategorized") if cid is not None else "General / Uncategorized"
        pct = round((count / total * 100.0), 1) if total > 0 else 0.0
        comp_pct = round((cat_compliant.get(cid, 0) / count * 100.0), 1) if count > 0 else 0.0
        cat_items.append(
            CategoryDistributionItem(
                category_id=cid,
                category_name=name,
                ticket_count=count,
                percentage=pct,
                sla_compliance_pct=comp_pct,
            )
        )
    cat_items.sort(key=lambda x: x.ticket_count, reverse=True)

    # Priority
    prio_counts: Dict[str, int] = {p: 0 for p in TicketPriority.ALL}
    prio_breached: Dict[str, int] = {p: 0 for p in TicketPriority.ALL}

    for t in tickets:
        p = t.priority or TicketPriority.MEDIUM
        prio_counts[p] = prio_counts.get(p, 0) + 1
        m = calculate_ticket_sla_metrics(db, t, now_dt=now_dt)
        if m.is_breached:
            prio_breached[p] = prio_breached.get(p, 0) + 1

    prio_items: List[PriorityDistributionItem] = []
    for p in TicketPriority.ALL:
        count = prio_counts.get(p, 0)
        pct = round((count / total * 100.0), 1) if total > 0 else 0.0
        breached_c = prio_breached.get(p, 0)
        prio_items.append(
            PriorityDistributionItem(
                priority=p,
                ticket_count=count,
                percentage=pct,
                breached_count=breached_c,
            )
        )

    return cat_items, prio_items


def compute_agent_workload_metrics(
    db: Session, start_dt: datetime, end_dt: datetime, now_dt: Optional[datetime] = None
) -> List[AgentWorkloadItem]:
    """Calculate assigned tickets, active backlog, resolved count, and SLA performance per agent."""
    agents = db.query(User).filter(
        User.role.in_([UserRole.AGENT, UserRole.ADMIN]),
        User.is_active == True
    ).all()

    workload_items: List[AgentWorkloadItem] = []
    for agent in agents:
        # Active assigned tickets
        active_tickets = db.query(Ticket).filter(
            Ticket.assignee_id == agent.id,
            Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.PENDING_CUSTOMER]),
        ).all()

        # Resolved tickets within date range
        resolved_tickets = db.query(Ticket).filter(
            Ticket.assignee_id == agent.id,
            Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
            Ticket.created_at >= start_dt,
            Ticket.created_at <= end_dt,
        ).all()

        # Resolution durations
        res_hours_list: List[float] = []
        comp_count = 0
        all_agent_tickets = active_tickets + resolved_tickets
        for t in resolved_tickets:
            res_time = t.resolved_at or t.closed_at or t.updated_at
            if res_time and t.created_at:
                t_created = t.created_at.replace(tzinfo=timezone.utc) if t.created_at.tzinfo is None else t.created_at
                t_res = res_time.replace(tzinfo=timezone.utc) if res_time.tzinfo is None else res_time
                res_hours_list.append(max(0.0, (t_res - t_created).total_seconds() / 3600.0))

        for t in all_agent_tickets:
            m = calculate_ticket_sla_metrics(db, t, now_dt=now_dt)
            if m.sla_state in [SLAState.ON_TRACK, SLAState.RESOLVED_MET, SLAState.PAUSED]:
                comp_count += 1

        avg_res = round(statistics.mean(res_hours_list), 2) if res_hours_list else 0.0
        sla_comp = round((comp_count / len(all_agent_tickets) * 100.0), 1) if all_agent_tickets else 100.0

        workload_items.append(
            AgentWorkloadItem(
                agent_id=agent.id,
                agent_name=agent.full_name,
                agent_email=agent.email,
                department=agent.department or "IT Support",
                active_tickets_count=len(active_tickets),
                resolved_tickets_count=len(resolved_tickets),
                avg_resolution_hours=avg_res,
                sla_compliance_pct=sla_comp,
            )
        )

    workload_items.sort(key=lambda x: (x.active_tickets_count, x.resolved_tickets_count), reverse=True)
    return workload_items


def compute_escalation_and_ai_metrics(
    db: Session, start_dt: datetime, end_dt: datetime
) -> Tuple[EscalationMetricsSummary, AIAdoptionMetrics]:
    """Query AuditLog and KB database for AI adoption, triage decisions, and escalation statistics."""
    audit_logs = db.query(AuditLog).filter(
        AuditLog.created_at >= start_dt,
        AuditLog.created_at <= end_dt
    ).all()

    # AI Triage
    triage_generated = sum(1 for a in audit_logs if a.action == AuditAction.AI_TRIAGED)
    triage_accepted = sum(1 for a in audit_logs if a.action == AuditAction.AI_RECOMMENDATION_ACCEPTED)
    triage_rejected = sum(1 for a in audit_logs if a.action == AuditAction.AI_RECOMMENDATION_REJECTED)
    triage_decided = triage_accepted + triage_rejected
    triage_acc_pct = round((triage_accepted / triage_decided * 100.0), 1) if triage_decided > 0 else 0.0

    # AI SLA Risk & Escalations
    sla_risk_evals = sum(1 for a in audit_logs if a.action == AuditAction.AI_SLA_RISK_ASSESSED)
    esc_accepted = sum(1 for a in audit_logs if a.action == AuditAction.AI_ESCALATION_ACCEPTED)
    esc_rejected = sum(1 for a in audit_logs if a.action == AuditAction.AI_ESCALATION_REJECTED)
    esc_decided = esc_accepted + esc_rejected
    esc_acc_pct = round((esc_accepted / esc_decided * 100.0), 1) if esc_decided > 0 else 0.0
    pending_esc = max(0, sla_risk_evals - esc_decided)

    # KB stats
    kb_articles = db.query(KBArticle).all()
    total_kb = len(kb_articles)
    total_views = sum(a.view_count for a in kb_articles)
    total_helpful = sum(a.helpful_count for a in kb_articles)

    escalation_summary = EscalationMetricsSummary(
        total_escalations_recommended=sla_risk_evals,
        accepted_count=esc_accepted,
        rejected_count=esc_rejected,
        pending_count=pending_esc,
        acceptance_rate_pct=esc_acc_pct,
        by_urgency={
            "immediate": esc_accepted,
            "high": esc_rejected,
            "standard": pending_esc,
        },
    )

    ai_adoption = AIAdoptionMetrics(
        total_triage_generated=triage_generated,
        triage_accepted=triage_accepted,
        triage_rejected=triage_rejected,
        triage_acceptance_rate_pct=triage_acc_pct,
        total_sla_risk_evaluations=sla_risk_evals,
        total_escalation_decisions=esc_decided,
        total_kb_articles=total_kb,
        total_kb_views=total_views,
        total_kb_helpful_votes=total_helpful,
    )

    return escalation_summary, ai_adoption


def get_operations_dashboard_analytics(
    db: Session,
    actor: User,
    preset: Optional[str] = "30d",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    now_dt: Optional[datetime] = None,
) -> OperationsAnalyticsDashboardResponse:
    """Consolidate operations analytics with strict RBAC enforcement (ADMIN / AGENT only)."""
    if actor.role not in [UserRole.ADMIN, UserRole.AGENT]:
        raise ForbiddenError("Access denied. Management Analytics requires Support Agent or Admin privileges.")

    start_dt, end_dt, resolved_preset = parse_analytics_date_range(
        preset=preset, start_date=start_date, end_date=end_date, now_dt=now_dt
    )

    volume_metrics = compute_ticket_volume_metrics(db, start_dt, end_dt)
    volume_trend = compute_volume_trend(db, start_dt, end_dt)
    res_metrics, fr_metrics = compute_resolution_and_response_metrics(db, start_dt, end_dt)
    sla_metrics = compute_sla_analytics(db, start_dt, end_dt, now_dt=now_dt)
    cat_items, prio_items = compute_category_and_priority_distributions(db, start_dt, end_dt, now_dt=now_dt)
    workload_items = compute_agent_workload_metrics(db, start_dt, end_dt, now_dt=now_dt)
    esc_summary, ai_adoption = compute_escalation_and_ai_metrics(db, start_dt, end_dt)

    date_range_meta = AnalyticsDateRange(
        preset=resolved_preset,
        start_date=start_dt,
        end_date=end_dt,
    )

    return OperationsAnalyticsDashboardResponse(
        date_range=date_range_meta,
        role=actor.role,
        volume_metrics=volume_metrics,
        volume_trend=volume_trend,
        resolution_metrics=res_metrics,
        first_response_metrics=fr_metrics,
        sla_metrics=sla_metrics,
        category_distribution=cat_items,
        priority_distribution=prio_items,
        agent_workload=workload_items,
        escalation_metrics=esc_summary,
        ai_adoption=ai_adoption,
    )
