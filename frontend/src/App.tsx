import { useEffect, useState, type FormEvent } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "./lib/supabase";
import { api } from "./lib/api";
import Dashboard from "./pages/Dashboard";
import Inventory from "./pages/Inventory";
import Sales from "./pages/Sales";
import Reports from "./pages/Reports";
import Assistant from "./pages/Assistant";

type Me = { user_id: string; email: string | null };
const TABS: [string, string][] = [["home", "Tổng quan"], ["kho", "Kho"], ["ban", "Bán hàng"], ["bc", "Báo cáo"], ["ai", "Trợ lý AI"]];

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("home");

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => { setSession(data.session); setReady(true); });
    const { data } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => data.subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!session) { setMe(null); return; }
    api<Me>("/api/v1/me").then(setMe).catch((e) => setError(e.message));
  }, [session]);

  async function login(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    const f = new FormData(e.currentTarget);
    const { error } = await supabase.auth.signInWithPassword({ email: String(f.get("email")), password: String(f.get("password")) });
    if (error) setError(error.message);
  }

  if (!ready) return <div className="wrap">Đang tải…</div>;
  if (!session)
    return (
      <form className="wrap" onSubmit={login}>
        <h1>Trợ lý kho bếp</h1>
        <input className="inp" name="email" type="email" placeholder="Email" required />
        <input className="inp" name="password" type="password" placeholder="Mật khẩu" required />
        <button className="btn" type="submit">Đăng nhập</button>
        {error && <div className="errbox" role="alert">{error}</div>}
      </form>
    );
  return (
    <div className="shell">
      <header className="top"><b>Trợ lý kho bếp</b>
        <span className="grow" />
        <small>{me?.email}</small>
        <button className="mini" onClick={() => supabase.auth.signOut()}>Đăng xuất</button></header>
      <main className="wrap">
        {error && <div className="errbox" role="alert">{error}</div>}
        {tab === "home" && <Dashboard go={setTab} />}
        {tab === "kho" && <Inventory />}
        {tab === "ban" && <Sales />}
        {tab === "bc" && <Reports />}
        {tab === "ai" && <Assistant />}
      </main>
      <nav className="nav">{TABS.map(([k, label]) => (
        <button key={k} className={tab === k ? "on" : ""} aria-current={tab === k ? "page" : undefined} onClick={() => setTab(k)}>{label}</button>))}</nav>
    </div>
  );
}
