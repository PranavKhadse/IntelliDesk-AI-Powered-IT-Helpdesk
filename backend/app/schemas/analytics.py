from datetime import datetime
from typing import List, Optional, Dict, Literal
from pydantic import BaseModel, Field


AnalyticsPreset = Literal["7d", "30d", "90d", "all", "custom"]


class AnalyticsDateRange(BaseModel):
    preset: str = "30d"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class TicketVolumeMetrics(BaseModel):
    total_tickets: int = 0
    open_tickets: int = 0
    in_progress_tickets: int = 0
    pending_customer_tickets: int = 0
    resolved_tickets: int = 0
    closed_tickets: int = 0
    active_backlog: int = 0
    resolution_rate_pct: float = 0.0


class VolumeTrendPoint(BaseModel):
    date: str
    created_count: int = 0
    resolved_count: int = 0


class ResolutionMetrics(BaseModel):
    avg_resolution_hours: float = 0.0
    median_resolution_hours: float = 0.0
    min_resolution_hours: float = 0.0
    max_resolution_hours: float = 0.0
    total_resolved_evaluated: int = 0


class FirstResponseMetrics(BaseModel):
    avg_first_response_hours: float = 0.0
    median_first_response_hours: float = 0.0
    first_response_compliance_pct: float = 0.0
    total_responses_evaluated: int = 0


class SLAMetricsSummary(BaseModel):
    total_evaluated: int = 0
    on_track_count: int = 0
    at_risk_count: int = 0
    breached_count: int = 0
    paused_count: int = 0
    resolved_met_count: int = 0
    resolved_breached_count: int = 0
    compliance_rate_pct: float = 0.0
    breach_rate_pct: float = 0.0


class CategoryDistributionItem(BaseModel):
    category_id: Optional[int] = None
    category_name: str
    ticket_count: int = 0
    percentage: float = 0.0
    sla_compliance_pct: float = 0.0


class PriorityDistributionItem(BaseModel):
    priority: str
    ticket_count: int = 0
    percentage: float = 0.0
    breached_count: int = 0


class AgentWorkloadItem(BaseModel):
    agent_id: str
    agent_name: str
    agent_email: str
    department: str
    active_tickets_count: int = 0
    resolved_tickets_count: int = 0
    avg_resolution_hours: float = 0.0
    sla_compliance_pct: float = 0.0


class EscalationMetricsSummary(BaseModel):
    total_escalations_recommended: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    pending_count: int = 0
    acceptance_rate_pct: float = 0.0
    by_urgency: Dict[str, int] = Field(default_factory=dict)


class AIAdoptionMetrics(BaseModel):
    total_triage_generated: int = 0
    triage_accepted: int = 0
    triage_rejected: int = 0
    triage_acceptance_rate_pct: float = 0.0
    total_sla_risk_evaluations: int = 0
    total_escalation_decisions: int = 0
    total_kb_articles: int = 0
    total_kb_views: int = 0
    total_kb_helpful_votes: int = 0


class OperationsAnalyticsDashboardResponse(BaseModel):
    date_range: AnalyticsDateRange
    role: str
    volume_metrics: TicketVolumeMetrics
    volume_trend: List[VolumeTrendPoint]
    resolution_metrics: ResolutionMetrics
    first_response_metrics: FirstResponseMetrics
    sla_metrics: SLAMetricsSummary
    category_distribution: List[CategoryDistributionItem]
    priority_distribution: List[PriorityDistributionItem]
    agent_workload: List[AgentWorkloadItem]
    escalation_metrics: EscalationMetricsSummary
    ai_adoption: AIAdoptionMetrics
