/**
 * HTTP REST Client chuẩn cho Frontend gọi tới FastAPI Backend.
 * Hỗ trợ JWT Bearer, Idempotency-Key header, xử lý lỗi chuẩn ErrorResponse.
 */
import { ErrorResponse } from '../../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export interface RequestOptions extends RequestInit {
  idempotencyKey?: string;
  params?: Record<string, string | number | boolean | undefined>;
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { idempotencyKey, params, headers: customHeaders, ...fetchOptions } = options;

    let url = `${BASE_URL}${endpoint}`;
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, val]) => {
        if (val !== undefined && val !== null) {
          searchParams.append(key, String(val));
        }
      });
      const queryString = searchParams.toString();
      if (queryString) {
        url += (url.includes('?') ? '&' : '?') + queryString;
      }
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((customHeaders as Record<string, string>) || {}),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    if (idempotencyKey) {
      headers['Idempotency-Key'] = idempotencyKey;
    }

    const response = await fetch(url, {
      ...fetchOptions,
      headers,
    });

    if (!response.ok) {
      let errorBody: ErrorResponse | null = null;
      try {
        errorBody = await response.json();
      } catch {
        // Response không phải JSON
      }

      const errorMessage = errorBody?.error?.message || `HTTP ${response.status}: ${response.statusText}`;
      const error = new Error(errorMessage) as Error & {
        status: number;
        code?: string;
        details?: unknown;
        requestId?: string | null;
      };
      error.status = response.status;
      error.code = errorBody?.error?.code || 'HTTP_ERROR';
      error.details = errorBody?.error?.details;
      error.requestId = errorBody?.error?.request_id;
      throw error;
    }

    if (response.status === 204) {
      return null as T;
    }

    return (await response.json()) as T;
  }

  get<T>(endpoint: string, params?: RequestOptions['params']): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET', params });
  }

  post<T>(endpoint: string, body?: unknown, idempotencyKey?: string): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
      idempotencyKey,
    });
  }

  patch<T>(endpoint: string, body?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  put<T>(endpoint: string, body?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();
