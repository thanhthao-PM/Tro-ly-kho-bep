/**
 * Kiểu dữ liệu dùng chung trên Frontend (TypeScript)
 * Ánh xạ 1:1 từ Pydantic common.py của FastAPI backend.
 */

export interface Labeled<T> {
  value: T;
  basis: 'ACTUAL' | 'ESTIMATE';
}

export interface CursorPage<T> {
  items: T[];
  next_cursor?: string | null;
  total_count?: number | null;
}

export interface ErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown> | null;
  request_id?: string | null;
}

export interface ErrorResponse {
  error: ErrorDetail;
}
