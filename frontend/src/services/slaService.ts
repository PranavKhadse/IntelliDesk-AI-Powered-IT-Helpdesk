import { apiClient } from './api';
import type {
  TicketSLAResponse,
  TicketAIRiskResponse,
  EscalationDecisionRequest,
  EscalationDecisionResponse,
  SLAPolicy,
} from '../types';

export const slaService = {
  /**
   * Retrieve calculated SLA state, targets, elapsed time, and first response metrics for a ticket.
   */
  getTicketSLA: async (ticketId: string): Promise<TicketSLAResponse> => {
    const response = await apiClient.get<TicketSLAResponse>(`/tickets/${ticketId}/sla`);
    return response.data;
  },

  /**
   * Generate AI SLA risk assessment and escalation recommendations (Staff only).
   */
  analyzeTicketSLARisk: async (ticketId: string): Promise<TicketAIRiskResponse> => {
    const response = await apiClient.post<TicketAIRiskResponse>(`/tickets/${ticketId}/ai-sla-risk`);
    return response.data;
  },

  /**
   * Approve an AI escalation recommendation and apply recommended priority (Staff only).
   */
  approveTicketEscalation: async (
    ticketId: string,
    req: EscalationDecisionRequest
  ): Promise<EscalationDecisionResponse> => {
    const response = await apiClient.post<EscalationDecisionResponse>(`/tickets/${ticketId}/ai-sla-risk/approve`, req);
    return response.data;
  },

  /**
   * Reject an AI escalation recommendation without mutating the ticket (Staff only).
   */
  rejectTicketEscalation: async (
    ticketId: string,
    req: EscalationDecisionRequest
  ): Promise<EscalationDecisionResponse> => {
    const response = await apiClient.post<EscalationDecisionResponse>(`/tickets/${ticketId}/ai-sla-risk/reject`, req);
    return response.data;
  },

  /**
   * List all configured SLA policies (Staff only).
   */
  listSLAPolicies: async (isActive?: boolean): Promise<{ items: SLAPolicy[]; total: number }> => {
    const params = isActive !== undefined ? { is_active: isActive } : {};
    const response = await apiClient.get<{ items: SLAPolicy[]; total: number }>('/sla/policies', { params });
    return response.data;
  },
};
