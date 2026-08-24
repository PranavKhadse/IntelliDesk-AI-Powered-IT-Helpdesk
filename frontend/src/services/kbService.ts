import { apiClient } from './api';
import type {
   KBArticle,
   KBArticleListResponse,
   KBArticleCreatePayload,
   KBArticleUpdatePayload,
   KBSearchResponse,
   Category,
   GroundedArticleReference,
   TicketGroundingResponse,
 } from '../types';

export interface KBListParams {
  page?: number;
  page_size?: number;
  category_id?: number;
  tag?: string;
  search?: string;
  is_published?: boolean;
}

export const kbService = {
  async getArticles(params?: KBListParams): Promise<KBArticleListResponse> {
    const res = await apiClient.get<KBArticleListResponse>('/kb/articles', { params });
    return res.data;
  },

  async getArticle(idOrSlug: string, incrementView: boolean = false): Promise<KBArticle> {
    const res = await apiClient.get<KBArticle>(`/kb/articles/${idOrSlug}`, {
      params: { increment_view: incrementView },
    });
    return res.data;
  },

  async createArticle(data: KBArticleCreatePayload): Promise<KBArticle> {
    const res = await apiClient.post<KBArticle>('/kb/articles', data);
    return res.data;
  },

  async updateArticle(id: string, data: KBArticleUpdatePayload): Promise<KBArticle> {
    const res = await apiClient.patch<KBArticle>(`/kb/articles/${id}`, data);
    return res.data;
  },

  async deleteArticle(id: string): Promise<void> {
    await apiClient.delete(`/kb/articles/${id}`);
  },

  async markHelpful(id: string): Promise<{ helpful_count: number }> {
    const res = await apiClient.post<{ helpful_count: number }>(`/kb/articles/${id}/helpful`);
    return res.data;
  },

  async searchKB(query: string, categoryId?: number, limit: number = 10): Promise<KBSearchResponse> {
    const res = await apiClient.get<KBSearchResponse>('/kb/search', {
      params: { q: query, category_id: categoryId, limit },
    });
    return res.data;
  },

  async getCategories(): Promise<Category[]> {
    const res = await apiClient.get<Category[]>('/kb/categories');
    return res.data;
  },

  async getTicketKBMatches(ticketId: string, limit: number = 5): Promise<GroundedArticleReference[]> {
    const res = await apiClient.get<GroundedArticleReference[]>(`/tickets/${ticketId}/kb-matches`, {
      params: { limit },
    });
    return res.data;
  },

  async getTicketGrounding(ticketId: string): Promise<TicketGroundingResponse> {
    const res = await apiClient.post<TicketGroundingResponse>(`/tickets/${ticketId}/ai-grounding`);
    return res.data;
  },
};
