import { useCallback, useEffect, useState, type ReactNode } from "react";

export function useLoad<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const reload = useCallback(() => {
    setLoading(true);
    setError("");
    fn().then(setData).catch((e: Error) => setError(e.message)).finally(() => setLoading(false));
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(reload, [reload]);
  return { data, error, loading, reload };
}

export const Card = ({ title, children, right }: { title?: string; children: ReactNode; right?: ReactNode }) => (
  <section className="card">
    {(title || right) && <div className="row"><h3 className="grow">{title}</h3>{right}</div>}
    {children}
  </section>
);

export const Tag = ({ kind, children }: { kind: string; children: ReactNode }) => <span className={`tag ${kind}`}>{children}</span>;
export const Empty = ({ children }: { children: ReactNode }) => <p className="empty">{children}</p>;
export const ErrorBox = ({ msg }: { msg: string }) => (msg ? <div className="errbox" role="alert">{msg}</div> : null);
export const Loading = () => <p className="empty" aria-busy="true">Đang tải…</p>;
export const Estimate = () => <span className="tag est" title="Số ước tính, không phải số thực tế">ESTIMATE</span>;

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="fl">{label}{children}</label>;
}

export function Async<T>({ s, children }: { s: { data: T | null; error: string; loading: boolean }; children: (d: T) => ReactNode }) {
  if (s.loading && !s.data) return <Loading />;
  if (s.error) return <ErrorBox msg={s.error} />;
  return s.data ? <>{children(s.data)}</> : null;
}
