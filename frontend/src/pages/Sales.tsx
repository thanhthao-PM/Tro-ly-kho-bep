import { useState, type FormEvent } from "react";
import { api, newKey, post } from "../lib/api";
import { dmy, today, vnd } from "../lib/format";
import { Async, Card, Empty, ErrorBox, Estimate, Field, Tag, useLoad } from "../components/ui";

export default function Sales() {
  const dishes = useLoad(() => api<{ items: any[] }>("/api/v1/dishes"));
  const sales = useLoad(() => api<{ items: any[] }>("/api/v1/sales"));
  const shorts = useLoad(() => api<{ items: any[] }>("/api/v1/shortages?status=OPEN"));
  const [panel, setPanel] = useState<"" | "sale" | "dish">("");
  const refresh = () => { dishes.reload(); sales.reload(); shorts.reload(); };
  return (
    <>
      <h1>Bán hàng</h1>
      <div className="row">
        <button className="btn" onClick={() => setPanel(panel === "sale" ? "" : "sale")}>Ghi nhận bán hàng</button>
        <button className="btn outline" onClick={() => setPanel(panel === "dish" ? "" : "dish")}>Thêm món</button>
      </div>
      {panel === "sale" && <SaleForm dishes={dishes.data?.items ?? []} done={() => { setPanel(""); refresh(); }} />}
      {panel === "dish" && <DishForm done={() => { setPanel(""); refresh(); }} />}

      <Card title="Thiếu hụt chưa xử lý">
        <Async s={shorts}>{(d) => d.items.length === 0 ? <Empty>Không có thiếu hụt.</Empty> :
          <ul className="list">{d.items.map((x) => <Shortage key={x.id} x={x} done={refresh} />)}</ul>}</Async>
      </Card>

      <Card title="Thực đơn">
        <Async s={dishes}>{(d) => d.items.length === 0 ? <Empty>Chưa có món. Bấm "Thêm món".</Empty> :
          <ul className="list">{d.items.map((x) => (
            <li key={x.id}><div className="grow"><b>{x.name}</b>
              <small>Giá {vnd(x.price_vnd)} · vốn {vnd(x.cost_estimate_vnd.value)} <Estimate /> · làm được {x.max_portions} phần
                {x.missing_ingredients.length > 0 && ` · thiếu: ${x.missing_ingredients.join(", ")}`}</small></div>
              <Tag kind={x.gross_margin_estimate.amount_vnd >= 0 ? "ok" : "bad"}>{x.gross_margin_estimate.percent}%</Tag></li>))}</ul>}</Async>
      </Card>

      <Card title="Bán hàng gần đây">
        <Async s={sales}>{(d) => d.items.length === 0 ? <Empty>Chưa có đơn bán.</Empty> :
          <ul className="list">{d.items.map((x) => (
            <li key={x.id}><div className="grow"><b>{dmy(x.business_date)}</b><small>{x.line_count} món · {vnd(x.revenue_vnd)}</small></div>
              {x.has_open_shortage && <Tag kind="warn">Thiếu hụt</Tag>}</li>))}</ul>}</Async>
      </Card>
    </>
  );
}

function Shortage({ x, done }: { x: any; done: () => void }) {
  const [err, setErr] = useState("");
  const [note, setNote] = useState("");
  async function act(action: string) {
    try { await post(`/api/v1/shortages/${x.id}/resolve`, { action, note: note || undefined }, newKey()); done(); }
    catch (e) { setErr((e as Error).message); }
  }
  return (
    <li className="col">
      <div className="row"><div className="grow"><b>{x.ingredient.name}</b><small>thiếu {x.short_qty} {x.unit} · bán ngày {dmy(x.business_date)}</small></div></div>
      <input className="inp" placeholder="Ghi chú (bắt buộc khi bỏ qua)" value={note} onChange={(e) => setNote(e.target.value)} />
      <div className="row"><button className="mini p" onClick={() => act("CONSUME_FROM_STOCK")}>Trừ từ kho</button>
        <button className="mini" onClick={() => act("WAIVE")}>Bỏ qua (ghi chú)</button></div>
      <ErrorBox msg={err} />
    </li>
  );
}

function SaleForm({ dishes, done }: { dishes: any[]; done: () => void }) {
  const [lines, setLines] = useState<{ dish: string; qty: string }[]>([{ dish: dishes[0]?.id ?? "", qty: "1" }]);
  const [date, setDate] = useState(today());
  const [err, setErr] = useState("");
  const [key, setKey] = useState(newKey());
  async function submit(e: FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      const doc = await post<any>("/api/v1/documents", { kind: "SALES_REPORT", source_format: "MANUAL", business_date: date });
      for (const l of lines) await post(`/api/v1/documents/${doc.id}/lines`, { dish_id: l.dish, quantity: Number(l.qty) });
      await post(`/api/v1/documents/${doc.id}/confirm`, {}, key);
      setKey(newKey());
      done();
    } catch (x) { setErr((x as Error).message); }
  }
  if (dishes.length === 0) return <Empty>Hãy thêm món trước khi ghi nhận bán hàng.</Empty>;
  return (
    <form className="card" onSubmit={submit}>
      <h3>Ghi nhận bán hàng</h3>
      <Field label="Ngày bán"><input className="inp" type="date" value={date} max={today()} onChange={(e) => setDate(e.target.value)} /></Field>
      {lines.map((l, i) => (
        <div className="row" key={i}>
          <select className="inp grow" value={l.dish} onChange={(e) => setLines(lines.map((x, j) => (j === i ? { ...x, dish: e.target.value } : x)))}>
            {dishes.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select>
          <input className="inp num" type="number" min="1" value={l.qty} aria-label="Số phần"
            onChange={(e) => setLines(lines.map((x, j) => (j === i ? { ...x, qty: e.target.value } : x)))} />
        </div>))}
      <button type="button" className="mini" onClick={() => setLines([...lines, { dish: dishes[0].id, qty: "1" }])}>+ Thêm dòng</button>
      <button className="btn" type="submit">Xác nhận và trừ kho (FEFO)</button>
      <p className="note">Kho trừ theo nguyên tắc hết hạn trước dùng trước. Nếu thiếu nguyên liệu, hệ thống ghi nhận thiếu hụt để bạn xử lý.</p>
      <ErrorBox msg={err} />
    </form>
  );
}

function DishForm({ done }: { done: () => void }) {
  const ings = useLoad(() => api<{ items: any[] }>("/api/v1/ingredients?limit=100"));
  const [rows, setRows] = useState<{ ing: string; qty: string }[]>([{ ing: "", qty: "" }]);
  const [err, setErr] = useState("");
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    try {
      await post("/api/v1/dishes", {
        name: String(f.get("name")), price_vnd: Number(f.get("price")),
        recipe: rows.filter((r) => r.ing && r.qty).map((r) => ({ ingredient_id: r.ing, quantity: r.qty })),
      });
      done();
    } catch (x) { setErr((x as Error).message); }
  }
  return (
    <form className="card" onSubmit={submit}>
      <h3>Thêm món</h3>
      <Field label="Tên món"><input className="inp" name="name" required maxLength={80} /></Field>
      <Field label="Giá bán (đ)"><input className="inp" name="price" type="number" min="0" required /></Field>
      <p className="note">Định lượng nguyên liệu cho 1 phần (theo đơn vị gốc của nguyên liệu):</p>
      {rows.map((r, i) => (
        <div className="row" key={i}>
          <select className="inp grow" value={r.ing} onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, ing: e.target.value } : x)))}>
            <option value="">Chọn nguyên liệu</option>
            {(ings.data?.items ?? []).map((g) => <option key={g.id} value={g.id}>{g.name} ({g.base_unit.code})</option>)}</select>
          <input className="inp num" type="number" step="any" min="0" placeholder="SL" value={r.qty}
            onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, qty: e.target.value } : x)))} />
        </div>))}
      <button type="button" className="mini" onClick={() => setRows([...rows, { ing: "", qty: "" }])}>+ Thêm nguyên liệu</button>
      <button className="btn" type="submit">Lưu món</button>
      <ErrorBox msg={err} />
    </form>
  );
}
