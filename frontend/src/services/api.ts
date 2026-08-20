import axios from 'axios';
import type { AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Attach JWT Token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Handle global 401 Unauthorized
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      const url = error.config?.url || '';
      const isAuthEndpoint = url.includes('/auth/login') || url.includes('/auth/register');
      if (!isAuthEndpoint) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_info');
      }
    }
    return Promise.reject(error);
  }
);

/**
 * Extract user-friendly error message from backend error responses.
 */
export const getApiErrorMessage = (error: unknown, fallbackMessage = 'An unexpected error occurred'): string => {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as Record<string, any> | undefined;
    if (data && typeof data === 'object') {
      if (typeof data.message === 'string' && data.message.trim()) {
        return data.message;
      }
      if (typeof data.detail === 'string' && data.detail.trim()) {
        return data.detail;
      }
      if (data.detail && typeof data.detail === 'object') {
        if (typeof data.detail.message === 'string' && data.detail.message.trim()) {
          return data.detail.message;
        }
      }
    }
    if (error.response?.status === 404) {
      return 'Requested resource not found.';
    }
    if (error.response?.status === 403) {
      return 'You do not have permission to perform this action.';
    }
    if (error.response?.status === 401) {
      return 'Invalid credentials or session expired.';
    }
    if (error.code === 'ERR_NETWORK' || !error.response) {
      return 'Unable to connect to server. Please check your network connection or ensure the backend is running.';
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallbackMessage;
};

