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
