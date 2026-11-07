import { useState, type FormEvent } from "react";
import { api, newKey, post } from "../lib/api";
import { dmy, STATUS_LABEL, tone, today } from "../lib/format";
import { Async, Card, Empty, ErrorBox, Field, Tag, useLoad } from "../components/ui";

type Row = { ingredient: { id: string; name: string }; unit: string; total_remaining: string; batch_count: number;
  nearest_expiry: string | null; expiry_status: string | null; location: string };

export default function Inventory() {
  const ov = useLoad(() => api<{ items: Row[] }>("/api/v1/inventory/ingredients"));
  const units = useLoad(() => api<{ items: { code: string; label_vi: string }[] }>("/api/v1/units"));
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const [panel, setPanel] = useState<"" | "receive" | "ingredient">("");
  return (
    <>
      <h1>Kho</h1>
      <div className="row">
        <button className="btn" onClick={() => setPanel(panel === "receive" ? "" : "receive")}>Nhập kho</button>
        <button className="btn outline" onClick={() => setPanel(panel === "ingredient" ? "" : "ingredient")}>Thêm nguyên liệu</button>
      </div>
      {panel === "receive" && <ReceiveForm rows={ov.data?.items ?? []} units={units.data?.items ?? []} done={() => { setPanel(""); ov.reload(); }} />}
      {panel === "ingredient" && <IngredientForm units={units.data?.items ?? []} done={() => { setPanel(""); ov.reload(); }} />}
      <input className="inp" placeholder="Tìm nguyên liệu" aria-label="Tìm nguyên liệu" value={q} onChange={(e) => setQ(e.target.value)} />
      <Async s={ov}>{(d) => {
        const rows = d.items.filter((r) => r.ingredient.name.toLowerCase().includes(q.trim().toLowerCase()));
        return rows.length === 0 ? <Empty>Chưa có nguyên liệu nào. Bấm "Thêm nguyên liệu".</Empty> : (
          <ul className="list">{rows.map((r) => (
            <li key={r.ingredient.id} className="col">
              <button className="rowbtn" onClick={() => setOpen(open === r.ingredient.id ? null : r.ingredient.id)}>
                <div className="grow"><b>{r.ingredient.name}</b>
                  <small>{r.total_remaining} {r.unit} · {r.batch_count} lô</small></div>
                {r.expiry_status && <Tag kind={tone(r.expiry_status)}>{STATUS_LABEL[r.expiry_status]}</Tag>}
              </button>
              {open === r.ingredient.id && <Batches id={r.ingredient.id} changed={ov.reload} />}
            </li>))}</ul>);
      }}</Async>
    </>
  );
}

function Batches({ id, changed }: { id: string; changed: () => void }) {
  const b = useLoad(() => api<any>(`/api/v1/inventory/ingredients/${id}/batches`), [id]);
  const [sel, setSel] = useState<any>(null);
  return (
    <Async s={b}>{(d) => d.batches.length === 0 ? <Empty>Không còn lô nào.</Empty> : (
      <div className="sub">{d.batches.map((x: any) => (
        <div key={x.id} className="row">
          <div className="grow"><b>Nhập {dmy(x.received_on)}</b>
            <small>{x.remaining_qty} {x.unit} · hạn {dmy(x.expiry_date)} · {x.stock_value_vnd.toLocaleString("vi-VN")} đ</small></div>
          <Tag kind={tone(x.expiry_status)}>{STATUS_LABEL[x.expiry_status]}</Tag>
          <button className="mini" onClick={() => setSel(sel?.id === x.id ? null : x)}>Xử lý</button>
        </div>))}
        {sel && <DisposeForm batch={sel} done={() => { setSel(null); b.reload(); changed(); }} />}
      </div>)}</Async>
  );
}

function DisposeForm({ batch, done }: { batch: any; done: () => void }) {
  const [key] = useState(newKey());
  const [err, setErr] = useState("");
  const expired = batch.expiry_status === "EXPIRED";
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const type = String(f.get("type"));
    const body: any = { type, quantity: String(f.get("quantity")), note: String(f.get("note") || "") || undefined };
    if (type === "WASTE") body.reason_code = String(f.get("reason"));
    if (type === "SELLOFF") body.revenue_vnd = Number(f.get("revenue") || 0);
    if (type === "DONATION" || type === "SELLOFF") body.counterparty_name = String(f.get("who") || "") || undefined;
    try { await post(`/api/v1/batches/${batch.id}/disposals`, body, key); done(); } catch (x) { setErr((x as Error).message); }
  }
  return (
    <form className="card" onSubmit={submit}>
      <h3>Xử lý lô {batch.ingredient_name}</h3>
      <Field label="Cách xử lý"><select className="inp" name="type" defaultValue="WASTE">
        <option value="WASTE">Bỏ đi</option>{!expired && <><option value="DONATION">Quyên góp</option><option value="SELLOFF">Bán thu mua</option></>}
      </select></Field>
      <Field label={`Số lượng (${batch.unit}), tối đa ${batch.remaining_qty}`}><input className="inp" name="quantity" type="number" step="any" min="0" defaultValue={batch.remaining_qty} required /></Field>
      <Field label="Lý do bỏ (khi bỏ đi)"><select className="inp" name="reason"><option value="EXPIRED">Hết hạn</option><option value="SPOILED">Hỏng/ôi thiu</option><option value="OVERSTOCK">Nhập dư</option><option value="OTHER">Khác (cần ghi chú)</option></select></Field>
      <Field label="Giá thu mua (đ, khi bán)"><input className="inp" name="revenue" type="number" min="0" /></Field>
      <Field label="Đối tác (khi quyên góp/bán)"><input className="inp" name="who" /></Field>
      <Field label="Ghi chú"><input className="inp" name="note" /></Field>
      <button className="btn" type="submit">Xác nhận</button>
      <ErrorBox msg={err} />
    </form>
  );
}

function ReceiveForm({ rows, units, done }: { rows: Row[]; units: { code: string }[]; done: () => void }) {
  const [key, setKey] = useState(newKey());
  const [err, setErr] = useState("");
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    try {
      await post("/api/v1/batches", {
        ingredient_id: f.get("ing"), quantity: String(f.get("qty")), unit: String(f.get("unit") || "") || undefined,
        unit_price_vnd: String(f.get("price")), received_on: String(f.get("rec")) || undefined,
        expiry_date: String(f.get("exp") || "") || undefined,
      }, key);
      setKey(newKey());
      done();
    } catch (x) { setErr((x as Error).message); }
  }
  return (
    <form className="card" onSubmit={submit}>
      <h3>Nhập kho</h3>
      <Field label="Nguyên liệu"><select className="inp" name="ing" required>{rows.map((r) => <option key={r.ingredient.id} value={r.ingredient.id}>{r.ingredient.name} ({r.unit})</option>)}</select></Field>
      <Field label="Số lượng"><input className="inp" name="qty" type="number" step="any" min="0" required /></Field>
      <Field label="Đơn vị (để trống = đơn vị gốc)"><input className="inp" name="unit" list="unit-list" /></Field>
      <datalist id="unit-list">{units.map((u) => <option key={u.code} value={u.code} />)}</datalist>
      <Field label="Giá nhập (đ mỗi đơn vị đã nhập)"><input className="inp" name="price" type="number" min="0" step="any" required /></Field>
      <Field label="Ngày nhập"><input className="inp" name="rec" type="date" max={today()} defaultValue={today()} /></Field>
      <Field label="Hạn dùng (bắt buộc nếu nguyên liệu có hạn)"><input className="inp" name="exp" type="date" /></Field>
      <button className="btn" type="submit">Thêm lô</button>
      <ErrorBox msg={err} />
    </form>
  );
}

function IngredientForm({ units, done }: { units: { code: string; label_vi: string }[]; done: () => void }) {
  const [err, setErr] = useState("");
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    try {
      await post("/api/v1/ingredients", {
        name: String(f.get("name")), base_unit: String(f.get("unit")), default_location: String(f.get("loc")),
        tracks_expiry: f.get("track") === "on", min_stock_qty: String(f.get("min") || "0"),
      });
      done();
    } catch (x) { setErr((x as Error).message); }
  }
  return (
    <form className="card" onSubmit={submit}>
      <h3>Thêm nguyên liệu</h3>
      <Field label="Tên"><input className="inp" name="name" required maxLength={80} /></Field>
      <Field label="Đơn vị gốc (không đổi được sau khi có dữ liệu)"><select className="inp" name="unit">{units.map((u) => <option key={u.code} value={u.code}>{u.label_vi}</option>)}</select></Field>
      <Field label="Nơi cất"><select className="inp" name="loc"><option value="FRIDGE">Tủ lạnh</option><option value="FREEZER">Ngăn đông</option><option value="PANTRY">Tủ bếp</option></select></Field>
      <Field label="Tồn tối thiểu"><input className="inp" name="min" type="number" min="0" step="any" /></Field>
      <label className="check"><input type="checkbox" name="track" defaultChecked /> Có theo dõi hạn dùng</label>
      <button className="btn" type="submit">Lưu</button>
      <ErrorBox msg={err} />
    </form>
  );
}
