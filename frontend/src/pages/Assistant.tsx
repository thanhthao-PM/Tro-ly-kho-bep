import { useRef, useState, type FormEvent } from "react";
import { post } from "../lib/api";
import { ErrorBox, Tag } from "../components/ui";

type Reply = { answer_text: string; facts: any[]; recommendations: { text: string; assumptions: string[]; basis: string }[];
  data_gaps: string[]; proposed_actions: { label: string }[]; provider: string };
type Msg = { role: "user" | "assistant"; text: string; reply?: Reply };

const SUGGEST = ["Hôm nay nên xử lý gì trước?", "Kho còn đủ nấu gì?", "Đồ nào bỏ nhiều nhất?", "Tuần này cần nhập thêm gì?", "Doanh thu tuần này thế nào?", "Món nào lãi nhất?"];

export default function Assistant() {
  const [msgs, setMsgs] = useState<Msg[]>([{ role: "assistant", text: "Mình trả lời dựa trên dữ liệu kho thật. Con số nào cũng lấy từ hệ thống, không phải do AI tự nghĩ ra." }]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const input = useRef<HTMLInputElement>(null);
  async function ask(text: string) {
    if (!text.trim() || busy) return;
    setErr(""); setBusy(true);
    const history = msgs.filter((m) => m.role).slice(-6).map((m) => ({ role: m.role, text: m.text.slice(0, 500) }));
    setMsgs((m) => [...m, { role: "user", text }]);
    try {
      const reply = await post<Reply>("/api/v1/assistant/messages", { message: text, history });
      setMsgs((m) => [...m, { role: "assistant", text: reply.answer_text, reply }]);
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  const submit = (e: FormEvent) => { e.preventDefault(); const v = input.current?.value ?? ""; if (input.current) input.current.value = ""; ask(v); };
  return (
    <>
      <h1>Trợ lý AI</h1>
      <div className="chips">{SUGGEST.map((s) => <button key={s} className="chip" onClick={() => ask(s)}>{s}</button>)}</div>
      <div className="chat" aria-live="polite">
        {msgs.map((m, i) => (
          <div key={i} className={`msg ${m.role === "user" ? "me" : "ai"}`}>
            <div style={{ whiteSpace: "pre-line" }}>{m.text}</div>
            {m.reply?.recommendations.map((r, j) => (
              <div key={j} className="rec"><Tag kind={r.basis === "ESTIMATE" ? "est" : "ok"}>{r.basis === "ESTIMATE" ? "ƯỚC TÍNH" : "SỐ LIỆU THẬT"}</Tag> {r.text}
                <small>Giả định: {r.assumptions.join("; ")}</small></div>))}
            {m.reply?.data_gaps.map((g, j) => <small key={j} className="gap">⚠ {g}</small>)}
            {m.reply && <small className="gap">Nguồn: {m.reply.facts.length} số liệu từ hệ thống · bộ máy {m.reply.provider === "rule_based" ? "theo quy tắc" : m.reply.provider}</small>}
          </div>))}
        {busy && <div className="msg ai">Đang tra dữ liệu…</div>}
      </div>
      <ErrorBox msg={err} />
      <form className="row" onSubmit={submit}>
        <input ref={input} className="inp grow" placeholder="Hỏi về kho, hạn dùng, lãi lỗ…" aria-label="Câu hỏi" maxLength={500} />
        <button className="btn send" type="submit" disabled={busy}>Gửi</button>
      </form>
      <p className="note">Trợ lý chỉ đọc dữ liệu, không tự thay đổi kho. Bản này dùng bộ quy tắc, chưa kết nối mô hình ngôn ngữ ngoài.</p>
    </>
  );
}
