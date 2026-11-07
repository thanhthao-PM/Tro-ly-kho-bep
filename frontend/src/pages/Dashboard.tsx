import { api } from "../lib/api";
import { addDays, dmy, STATUS_LABEL, tone, today, vnd } from "../lib/format";
import { Async, Card, Empty, Estimate, Tag, useLoad } from "../components/ui";

type Summary = { ingredient_count: number; batch_count: number; stock_value_vnd: number; by_status: Record<string, number> };
type Expiring = { items: { batch: any; status: string; available_actions: string[]; suggested_dishes: any[] }[] };

export default function Dashboard({ go }: { go: (t: string) => void }) {
  const sum = useLoad(() => api<Summary>("/api/v1/inventory/summary"));
  const exp = useLoad(() => api<Expiring>("/api/v1/expiring-batches"));
  const sh = useLoad(() => api<{ items: any[] }>("/api/v1/shortages?status=OPEN"));
  const rep = useLoad(() => api<any>(`/api/v1/reports/summary?from=${addDays(today(), -6)}&to=${today()}`));
  return (
    <>
      <h1>Tổng quan</h1>
      <Async s={sum}>{(s) => (
        <div className="metrics">
          <div><span>Mặt hàng</span><b>{s.ingredient_count}</b></div>
          <div><span>Số lô còn</span><b>{s.batch_count}</b></div>
          <div><span>Giá trị tồn</span><b>{vnd(s.stock_value_vnd)}</b></div>
        </div>)}</Async>
      <Card title="Cần xử lý" right={<button className="mini" onClick={() => go("kho")}>Mở kho</button>}>
        <Async s={exp}>{(e) => e.items.length === 0 ? <Empty>Không có lô nào sắp hết hạn.</Empty> : (
          <ul className="list">{e.items.slice(0, 6).map((x) => (
            <li key={x.batch.id}>
              <div className="grow"><b>{x.batch.ingredient_name}</b>
                <small>{x.batch.remaining_qty} {x.batch.unit} · hạn {dmy(x.batch.expiry_date)}</small></div>
              <Tag kind={tone(x.status)}>{STATUS_LABEL[x.status]}</Tag>
            </li>))}</ul>)}</Async>
      </Card>
      <Card title="Thiếu hụt chưa xử lý" right={<button className="mini" onClick={() => go("ban")}>Xử lý</button>}>
        <Async s={sh}>{(d) => d.items.length === 0 ? <Empty>Không có thiếu hụt.</Empty> :
          <p>{d.items.length} thiếu hụt nguyên liệu khi trừ kho. Giá vốn kỳ này đang thấp hơn thực tế cho đến khi xử lý.</p>}</Async>
      </Card>
      <Card title="7 ngày gần nhất">
        <Async s={rep}>{(r) => (<>
          <div className="kv"><span>Doanh thu</span><b>{vnd(r.totals.revenue_vnd.value)}</b></div>
          <div className="kv"><span>Lãi gộp (chưa tính ước tính)</span><b>{vnd(r.totals.gross_profit.excluding_estimates_vnd)}</b></div>
          <div className="kv"><span>Lãi gộp gồm ước tính <Estimate /></span><b>{vnd(r.totals.gross_profit.including_estimates_vnd.value)}</b></div>
          {r.cogs_status.has_open_shortages && <p className="warnbox">Chi phí chưa đầy đủ: còn thiếu hụt chưa xử lý.</p>}
        </>)}</Async>
      </Card>
      <button className="btn" onClick={() => go("ai")}>Hỏi trợ lý AI</button>
    </>
  );
}
