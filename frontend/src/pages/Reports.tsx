import { useState } from "react";
import { api } from "../lib/api";
import { addDays, today, vnd } from "../lib/format";
import { Async, Card, Empty, Estimate, useLoad } from "../components/ui";

export default function Reports() {
  const [from, setFrom] = useState(addDays(today(), -6));
  const [to, setTo] = useState(today());
  const rep = useLoad(() => api<any>(`/api/v1/reports/summary?from=${from}&to=${to}`), [from, to]);
  const repl = useLoad(() => api<any>("/api/v1/replenishment-suggestions"));
  const st = useLoad(() => api<any>("/api/v1/settings"));
  return (
    <>
      <h1>Báo cáo</h1>
      <div className="row">
        <label className="fl grow">Từ<input className="inp" type="date" value={from} max={to} onChange={(e) => setFrom(e.target.value)} /></label>
        <label className="fl grow">Đến<input className="inp" type="date" value={to} max={today()} onChange={(e) => setTo(e.target.value)} /></label>
      </div>
      <Async s={rep}>{(r) => (<>
        {r.cogs_status.has_open_shortages && <p className="warnbox">Chi phí chưa đầy đủ: còn thiếu hụt chưa xử lý.</p>}
        <Card title="Bán hàng">
          <div className="kv"><span>Doanh thu</span><b>{vnd(r.sales.revenue_vnd.value)}</b></div>
          <div className="kv"><span>Giá vốn thực tế</span><b>−{vnd(r.sales.cogs.actual_vnd.value)}</b></div>
          <div className="kv"><span>Giá vốn ước tính <Estimate /></span><b>−{vnd(r.sales.cogs.estimated_vnd.value)}</b></div>
          <div className="kv"><span>Lãi gộp (không gồm ước tính)</span><b>{vnd(r.sales.gross_profit.excluding_estimates_vnd)}</b></div>
          <div className="kv"><span>Lãi gộp (gồm ước tính) <Estimate /></span><b>{vnd(r.sales.gross_profit.including_estimates_vnd.value)}</b></div>
          <div className="kv"><span>Số phần bán</span><b>{r.sales.portions_sold}</b></div>
        </Card>
        <Card title="Hao hụt và xử lý">
          <div className="kv"><span>Bỏ đi</span><b>{vnd(r.waste_cost_vnd.value)}</b></div>
          <div className="kv"><span>Quyên góp (giá trị hàng)</span><b>{vnd(r.donation_cost_vnd.value)}</b></div>
          <div className="kv"><span>Bán thu mua: thu / vốn</span><b>{vnd(r.selloff.revenue_vnd.value)} / {vnd(r.selloff.cost_vnd.value)}</b></div>
          <div className="kv"><span>Điều chỉnh kho (ròng)</span><b>{vnd(r.adjustment_net_vnd.value)}</b></div>
          <div className="kv"><span>Thiếu hụt: mở / ghi ước tính / bỏ qua</span><b>{r.shortages.open_count} / {r.shortages.written_off_estimated_count} / {r.shortages.waived_count}</b></div>
        </Card>
        <Card title="Kết quả sau hao hụt nguyên liệu">
          <div className="kv"><span>Không gồm ước tính</span><b>{vnd(r.result_after_ingredient_loss.excluding_estimates_vnd)}</b></div>
          <div className="kv"><span>Gồm ước tính <Estimate /></span><b>{vnd(r.result_after_ingredient_loss.including_estimates_vnd.value)}</b></div>
          <p className="note">Chỉ tính chi phí nguyên liệu. Công thức đang chờ phê duyệt kế toán (D7), chưa phải lợi nhuận chính thức.</p>
        </Card>
      </>)}</Async>
      <Card title="Gợi ý nhập hàng (ước tính)">
        <Async s={repl}>{(d) => (<>
          {d.items.length === 0 ? <Empty>Chưa có mặt hàng nào cần nhập theo quy tắc.</Empty> :
            <ul className="list">{d.items.map((x: any) => (
              <li key={x.ingredient.id} className="col"><div className="row"><b className="grow">{x.ingredient.name}</b><span>{x.suggested_order_qty} {x.unit}</span></div>
                <small>Quy tắc {x.rule} · còn {x.usable_qty} {x.unit}{x.days_of_cover ? ` · đủ ${x.days_of_cover} ngày` : ""}</small></li>))}</ul>}
          {d.insufficient_data.length > 0 && <p className="note">Chưa đủ lịch sử để tính theo ngày tồn: {d.insufficient_data.map((x: any) => x.ingredient.name).join(", ")}.</p>}
          <p className="note">Tham số: {d.parameters.target_coverage_days} ngày tồn mục tiêu, cửa sổ {d.parameters.window_days} ngày, tối thiểu {d.parameters.min_history_days} ngày lịch sử (giá trị tạm).</p>
        </>)}</Async>
      </Card>
      <Card title="Cài đặt bếp (chỉ xem)">
        <Async s={st}>{(s) => <p className="note">Cảnh báo hết hạn trước {s.expiry_warning_days} ngày. Hàng hết hạn dùng được: {s.expired_batches_consumable ? "có" : "không"}. Hành động cho hàng hết hạn: {s.expired_batch_actions.join(", ")}. Các giá trị này là tạm thời chờ phê duyệt (D9).</p>}</Async>
      </Card>
    </>
  );
}
