from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.analytics import (
    OperationsAnalyticsDashboardResponse,
    TicketVolumeMetrics,
    SLAMetricsSummary,
    AgentWorkloadItem,
    EscalationMetricsSummary,
    AIAdoptionMetrics,
)
from app.services.analytics_service import (
    get_operations_dashboard_analytics,
    parse_analytics_date_range,
    compute_ticket_volume_metrics,
    compute_sla_analytics,
    compute_agent_workload_metrics,
    compute_escalation_and_ai_metrics,
)

analytics_router = APIRouter(prefix="/analytics", tags=["Operations Analytics"])


@analytics_router.get("/dashboard", response_model=OperationsAnalyticsDashboardResponse)
def get_operations_dashboard(
    preset: Optional[str] = Query("30d", description="Time preset: 7d, 30d, 90d, all, custom"),
    start_date: Optional[datetime] = Query(None, description="ISO Start date for custom range"),
    end_date: Optional[datetime] = Query(None, description="ISO End date for custom range"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.AGENT, UserRole.ADMIN])),
):
    """Retrieve consolidated operations & management analytics dashboard (Staff only)."""
    return get_operations_dashboard_analytics(
        db=db,
        actor=current_user,
        preset=preset,
        start_date=start_date,
        end_date=end_date,
    )


@analytics_router.get("/sla", response_model=SLAMetricsSummary)
def get_sla_analytics_report(
    preset: Optional[str] = Query("30d"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.AGENT, UserRole.ADMIN])),
):
    """Retrieve dedicated SLA compliance and breach metrics (Staff only)."""
    start_dt, end_dt, _ = parse_analytics_date_range(preset=preset, start_date=start_date, end_date=end_date)
    return compute_sla_analytics(db=db, start_dt=start_dt, end_dt=end_dt)


@analytics_router.get("/workload", response_model=list[AgentWorkloadItem])
def get_agent_workload_report(
    preset: Optional[str] = Query("30d"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.AGENT, UserRole.ADMIN])),
):
    """Retrieve agent and team workload performance metrics (Staff only)."""
    start_dt, end_dt, _ = parse_analytics_date_range(preset=preset, start_date=start_date, end_date=end_date)
    return compute_agent_workload_metrics(db=db, start_dt=start_dt, end_dt=end_dt)
