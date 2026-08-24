import { apiClient } from './api';
import type {
  Category,
  Ticket,
  TicketDetail,
  TicketListResponse,
  TicketCreatePayload,
  TicketUpdatePayload,
  CommentCreatePayload,
  TicketComment,
  AgentSummary,
  TicketFilterParams,
  TicketTriageRecommendation,
  AIResponseDraft,
  TicketSummary,
} from '../types';

export const ticketService = {
  /**
   * Fetch all active categories with SLA targets.
   */
  async getCategories(): Promise<Category[]> {
    const res = await apiClient.get<Category[]>('/tickets/categories');
    return res.data;
  },

  /**
   * List tickets with pagination, status/priority filtering, and search.
   */
  async getTickets(params: TicketFilterParams = {}): Promise<TicketListResponse> {
    const res = await apiClient.get<TicketListResponse>('/tickets', { params });
    return res.data;
  },

  /**
   * Get single ticket by ID or ticket number with comments and audit logs.
   */
  async getTicketDetail(ticketId: string): Promise<TicketDetail> {
    const res = await apiClient.get<TicketDetail>(`/tickets/${ticketId}`);
    return res.data;
  },

  /**
   * Create a new ticket.
   */
  async createTicket(payload: TicketCreatePayload): Promise<Ticket> {
    const res = await apiClient.post<Ticket>('/tickets', payload);
    return res.data;
  },

  /**
   * Update ticket status, priority, assignment, or details.
   */
  async updateTicket(ticketId: string, payload: TicketUpdatePayload): Promise<Ticket> {
    const res = await apiClient.patch<Ticket>(`/tickets/${ticketId}`, payload);
    return res.data;
  },

  /**
   * Request a recommendation-only AI triage assessment for an accessible ticket.
   */
  async getTicketTriage(ticketId: string): Promise<TicketTriageRecommendation> {
    const res = await apiClient.post<TicketTriageRecommendation>(`/tickets/${ticketId}/ai-triage`);
    return res.data;
  },

  /**
   * Accept a previously generated AI recommendation for a ticket.
   */
  async approveTicketTriage(ticketId: string, recommendationId: string): Promise<{ recommendation_id: string; decision: 'accepted' | 'rejected' }> {
    const res = await apiClient.post<{ recommendation_id: string; decision: 'accepted' | 'rejected' }>(`/tickets/${ticketId}/ai-triage/approve`, { recommendation_id: recommendationId });
    return res.data;
  },

  /**
   * Reject a previously generated AI recommendation for a ticket.
   */
  async rejectTicketTriage(ticketId: string, recommendationId: string): Promise<{ recommendation_id: string; decision: 'accepted' | 'rejected' }> {
    const res = await apiClient.post<{ recommendation_id: string; decision: 'accepted' | 'rejected' }>(`/tickets/${ticketId}/ai-triage/reject`, { recommendation_id: recommendationId });
    return res.data;
  },

  /**
   * Request an AI-assisted customer response draft for support staff (Agent/Admin only).
   */
  async getResponseDraft(ticketId: string): Promise<AIResponseDraft> {
    const res = await apiClient.post<AIResponseDraft>(`/tickets/${ticketId}/ai-response-draft`);
    return res.data;
  },

  /**
   * Request an AI ticket summary and action insights for support staff (Agent/Admin only).
   */
  async getTicketSummary(ticketId: string): Promise<TicketSummary> {
    const res = await apiClient.post<TicketSummary>(`/tickets/${ticketId}/ai-summary`);
    return res.data;
  },

  /**
   * Add a public comment or internal note to a ticket.
   */
  async addComment(ticketId: string, payload: CommentCreatePayload): Promise<TicketComment> {
    const res = await apiClient.post<TicketComment>(`/tickets/${ticketId}/comments`, payload);
    return res.data;
  },

  /**
   * List support agents and admins for assignment (Agent/Admin only).
   */
  async getAgents(): Promise<AgentSummary[]> {
    const res = await apiClient.get<AgentSummary[]>('/users/agents');
    return res.data;
  },
};
