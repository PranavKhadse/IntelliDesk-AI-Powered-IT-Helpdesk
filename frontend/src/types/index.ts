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

