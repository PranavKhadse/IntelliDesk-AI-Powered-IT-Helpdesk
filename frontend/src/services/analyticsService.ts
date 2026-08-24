import { apiClient } from './api';
import type {
  OperationsAnalyticsDashboardResponse,
  SLAMetricsSummary,
  AgentWorkloadItem,
} from '../types';

export const analyticsService = {
  /**
   * Fetch consolidated operations & management analytics dashboard.
   */
  getDashboardAnalytics: async (
    preset: string = '30d',
    startDate?: string,
    endDate?: string
  ): Promise<OperationsAnalyticsDashboardResponse> => {
    const params: Record<string, string> = { preset };
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    const response = await apiClient.get<OperationsAnalyticsDashboardResponse>('/analytics/dashboard', { params });
    return response.data;
  },

  /**
   * Fetch dedicated SLA performance and breach metrics.
   */
  getSLAMetrics: async (
    preset: string = '30d',
    startDate?: string,
    endDate?: string
  ): Promise<SLAMetricsSummary> => {
    const params: Record<string, string> = { preset };
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    const response = await apiClient.get<SLAMetricsSummary>('/analytics/sla', { params });
    return response.data;
  },

  /**
   * Fetch agent and team workload distribution.
   */
  getAgentWorkload: async (
    preset: string = '30d',
    startDate?: string,
    endDate?: string
  ): Promise<AgentWorkloadItem[]> => {
    const params: Record<string, string> = { preset };
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    const response = await apiClient.get<AgentWorkloadItem[]>('/analytics/workload', { params });
    return response.data;
  },
};
