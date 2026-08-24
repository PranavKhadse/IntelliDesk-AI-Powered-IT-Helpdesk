export type UserRole = 'user' | 'agent' | 'admin';

export type TicketStatus = 'open' | 'in_progress' | 'pending_customer' | 'resolved' | 'closed';

export type TicketPriority = 'low' | 'medium' | 'high' | 'critical';

export type CommentType = 'public' | 'internal_note' | 'system_event' | 'ai_resolution_draft';

export type TriageUrgency = 'low' | 'medium' | 'high' | 'critical';

export type TriageImpact = 'individual' | 'team' | 'department' | 'organization_wide';

export interface User {
  id: string;
  email: string;
  full_name: string;
  department: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AgentSummary {
  id: string;
  full_name: string;
  email: string;
  department: string;
}

export interface Category {
  id: number;
  name: string;
  description?: string;
  default_sla_hours: number;
  is_active: boolean;
}

export interface TicketComment {
  id: string;
  ticket_id: string;
  author_id?: string;
  author?: AgentSummary;
  comment_type: CommentType;
  content: string;
  created_at: string;
}

export interface AuditLog {
  id: string;
  ticket_id: string;
  actor_id?: string;
  actor?: AgentSummary;
  action: string;
  previous_state?: string;
  new_state?: string;
  created_at: string;
}

export interface Ticket {
  id: string;
  ticket_number: string;
  title: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  category_id?: number;
  category?: Category;
  creator_id: string;
  creator?: User;
  assignee_id?: string;
  assignee?: AgentSummary;
  ai_suggested_category?: string;
  ai_suggested_priority?: string;
  ai_confidence_score?: number;
  sla_due_at?: string;
  resolved_at?: string;
  closed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface TicketDetail extends Ticket {
  comments: TicketComment[];
  audit_logs: AuditLog[];
}

export interface TicketTriageRecommendation {
  recommendation_id?: string;
  category: string;
  priority: TicketPriority;
  urgency: TriageUrgency;
  impact: TriageImpact;
  suggested_team: string;
  confidence: number;
  confidence_level?: string;
  evidence?: string[];
  priority_reason?: string;
  category_reason?: string;
  urgency_impact_reason?: string;
  explanation: string;
}

export interface AIResponseDraft {
  draft_response: string;
  tone: string;
  key_points: string[];
  confidence: number;
}

export interface TicketSummary {
  summary: string;
  customer_issue: string;
  important_facts: string[];
  actions_taken: string[];
  suggested_next_steps: string[];
  missing_information: string[];
  risk_flags: string[];
  confidence: number;
}

export interface TicketListResponse {
  items: Ticket[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}


export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface TicketCreatePayload {
  title: string;
  description: string;
  category_id?: number;
  priority?: TicketPriority;
}

export interface TicketUpdatePayload {
  title?: string;
  description?: string;
  status?: TicketStatus;
  priority?: TicketPriority;
  category_id?: number;
  assignee_id?: string | null;
}

export interface CommentCreatePayload {
  content: string;
  comment_type?: CommentType;
}

export interface TicketFilterParams {
  page?: number;
  page_size?: number;
  status?: TicketStatus | string;
  priority?: TicketPriority | string;
  category_id?: number;
  search?: string;
  assigned_to_me?: boolean;
}

export interface KBArticleAuthorSummary {
  id: string;
  full_name: string;
  email: string;
  role: UserRole;
}

export interface KBArticleCategorySummary {
  id: number;
  name: string;
}

export interface KBArticle {
  id: string;
  title: string;
  slug: string;
  summary?: string;
  content: string;
  category_id?: number;
  category?: KBArticleCategorySummary;
  author_id?: string;
  author?: KBArticleAuthorSummary;
  is_published: boolean;
  tags: string;
  view_count: number;
  helpful_count: number;
  created_at: string;
  updated_at: string;
}

export interface KBArticleListResponse {
  items: KBArticle[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface KBArticleCreatePayload {
  title: string;
  summary?: string;
  content: string;
  category_id?: number;
  is_published?: boolean;
  tags?: string;
  slug?: string;
}

export interface KBArticleUpdatePayload {
  title?: string;
  summary?: string;
  content?: string;
  category_id?: number;
  is_published?: boolean;
  tags?: string;
  slug?: string;
}

export interface KBSearchResultItem {
  id: string;
  title: string;
  slug: string;
  summary?: string;
  category?: string;
  tags: string;
  relevance_score: number;
  snippet: string;
}

export interface KBSearchResponse {
  query: string;
  items: KBSearchResultItem[];
  total: number;
}

export type GroundingStatus = 'grounded' | 'partially_grounded' | 'no_match';

export interface GroundedArticleReference {
  article_id: string;
  slug: string;
  title: string;
  category?: string;
  relevance_score: number;
  snippet: string;
}

export interface TicketGroundingResponse {
  ticket_id: string;
  ticket_number: string;
  grounding_status: GroundingStatus;
  recommendation: string;
  key_points: string[];
  sources: GroundedArticleReference[];
  confidence: number;
  reasoning?: string;
  no_match_reason?: string;
}

// ==============================================================================
// SLA & Escalation Intelligence Types
// ==============================================================================

export type SLAState = 'ON_TRACK' | 'AT_RISK' | 'BREACHED' | 'PAUSED' | 'RESOLVED_MET' | 'RESOLVED_BREACHED';

export type FirstResponseStatus = 'met' | 'pending' | 'breached' | 'breached_pending';

export interface SLAPolicy {
  id: number;
  name: string;
  description?: string;
  priority?: TicketPriority;
  category_id?: number;
  first_response_hours: number;
  resolution_hours: number;
  warning_threshold_pct: number;
  escalation_threshold_pct: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TicketSLAMetrics {
  policy_name: string;
  target_first_response_hours: number;
  target_resolution_hours: number;
  first_response_status: FirstResponseStatus;
  first_response_at?: string;
  first_response_elapsed_seconds?: number;
  resolution_at?: string;
  resolution_elapsed_seconds: number;
  remaining_seconds: number;
  percentage_consumed: number;
  sla_state: SLAState;
  sla_due_at?: string;
  is_breached: boolean;
  is_at_risk: boolean;
  warning_threshold_pct: number;
  escalation_threshold_pct: number;
}

export interface TicketSLAResponse {
  ticket_id: string;
  ticket_number: string;
  priority: string;
  category_id?: number;
  category_name?: string;
  status: string;
  created_at: string;
  sla_metrics: TicketSLAMetrics;
}

export interface AISLARiskAssessment {
  recommendation_id: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  confidence_level: 'Low' | 'Medium' | 'High';
  is_at_risk_of_breach: boolean;
  predicted_time_to_breach?: string;
  risk_factors: string[];
  recommended_action: string;
  escalation_recommended: boolean;
  escalation_urgency: 'low' | 'medium' | 'high' | 'immediate';
  recommended_priority: string;
  recommended_team: string;
  evidence: string[];
}

export interface TicketAIRiskResponse {
  ticket_id: string;
  ticket_number: string;
  sla_metrics: TicketSLAMetrics;
  ai_risk_assessment: AISLARiskAssessment;
}

export interface EscalationDecisionRequest {
  recommendation_id: string;
  apply_priority?: boolean;
  note?: string;
}

export interface EscalationDecisionResponse {
  recommendation_id: string;
  decision: 'accepted' | 'rejected';
  applied_priority?: string;
  message: string;
}

// ==============================================================================
// Operations / Management Analytics Types
// ==============================================================================

export type AnalyticsTimePreset = '7d' | '30d' | '90d' | 'all' | 'custom';

export interface AnalyticsDateRange {
  preset: string;
  start_date?: string;
  end_date?: string;
}

export interface TicketVolumeMetrics {
  total_tickets: number;
  open_tickets: number;
  in_progress_tickets: number;
  pending_customer_tickets: number;
  resolved_tickets: number;
  closed_tickets: number;
  active_backlog: number;
  resolution_rate_pct: number;
}

export interface VolumeTrendPoint {
  date: string;
  created_count: number;
  resolved_count: number;
}

export interface ResolutionMetrics {
  avg_resolution_hours: number;
  median_resolution_hours: number;
  min_resolution_hours: number;
  max_resolution_hours: number;
  total_resolved_evaluated: number;
}

export interface FirstResponseMetrics {
  avg_first_response_hours: number;
  median_first_response_hours: number;
  first_response_compliance_pct: number;
  total_responses_evaluated: number;
}

export interface SLAMetricsSummary {
  total_evaluated: number;
  on_track_count: number;
  at_risk_count: number;
  breached_count: number;
  paused_count: number;
  resolved_met_count: number;
  resolved_breached_count: number;
  compliance_rate_pct: number;
  breach_rate_pct: number;
}

export interface CategoryDistributionItem {
  category_id?: number;
  category_name: string;
  ticket_count: number;
  percentage: number;
  sla_compliance_pct: number;
}

export interface PriorityDistributionItem {
  priority: string;
  ticket_count: number;
  percentage: number;
  breached_count: number;
}

export interface AgentWorkloadItem {
  agent_id: string;
  agent_name: string;
  agent_email: string;
  department: string;
  active_tickets_count: number;
  resolved_tickets_count: number;
  avg_resolution_hours: number;
  sla_compliance_pct: number;
}

export interface EscalationMetricsSummary {
  total_escalations_recommended: number;
  accepted_count: number;
  rejected_count: number;
  pending_count: number;
  acceptance_rate_pct: number;
  by_urgency: Record<string, number>;
}

export interface AIAdoptionMetrics {
  total_triage_generated: number;
  triage_accepted: number;
  triage_rejected: number;
  triage_acceptance_rate_pct: number;
  total_sla_risk_evaluations: number;
  total_escalation_decisions: number;
  total_kb_articles: number;
  total_kb_views: number;
  total_kb_helpful_votes: number;
}

export interface OperationsAnalyticsDashboardResponse {
  date_range: AnalyticsDateRange;
  role: string;
  volume_metrics: TicketVolumeMetrics;
  volume_trend: VolumeTrendPoint[];
  resolution_metrics: ResolutionMetrics;
  first_response_metrics: FirstResponseMetrics;
  sla_metrics: SLAMetricsSummary;
  category_distribution: CategoryDistributionItem[];
  priority_distribution: PriorityDistributionItem[];
  agent_workload: AgentWorkloadItem[];
  escalation_metrics: EscalationMetricsSummary;
  ai_adoption: AIAdoptionMetrics;
}



