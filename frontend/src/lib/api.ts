import { supabase } from "./supabase";

const BASE = (import.meta.env.VITE_API_BASE_URL as string) ?? "http://localhost:8000";

export class ApiRequestError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...((init.headers as Record<string, string> | undefined) ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const d = body?.detail;
    const msg = typeof d === "string" ? d : d?.message ?? (Array.isArray(d) ? "Dữ liệu gửi lên không hợp lệ" : res.statusText);
    throw new ApiRequestError(res.status, d?.code ?? "HTTP_ERROR", msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const post = <T,>(path: string, body: unknown, idempotencyKey?: string) =>
  api<T>(path, {
    method: "POST",
    body: JSON.stringify(body),
    headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {},
  });

export const newKey = () => crypto.randomUUID();
