import React, { useState, useMemo, useEffect } from 'react';
import {
  simulationStore,
  formatMoney,
  capitalize,
  offsetDays,
  PeriodReportFull,
} from '../services/mock/simulationStore';
import { SegmentedControl } from '../components/common/SegmentedControl';
import { Icon } from '../components/common/Icon';
import { StatusTag } from '../components/common/StatusTag';
import { apiClient, API_BASE_URL } from '../services/api/client';

type PeriodType = 'day' | 'month' | 'quarter' | 'range';
type ReportSubTab = 'tong' | 'xuly' | 'bo';

interface ReportsViewProps {
  onNavigateToAI: () => void;
  onShowToast: (msg: string) => void;
  onOpenScan: (businessDate: string) => void;
  invoiceRefreshKey: number;
}

interface DailyInvoiceSummary {
  business_date: string;
  invoice_count: number;
  line_count: number;
  total_value_vnd: number;
  invoices: Array<{
    id: string;
    original_filename?: string | null;
    source_format: string;
    line_count: number;
    total_value_vnd: number;
    file_url?: string | null;
  }>;
}

const KITCHEN_ID = import.meta.env.VITE_KITCHEN_ID || '00000000-0000-0000-0000-000000000002';

export const ReportsView: React.FC<ReportsViewProps> = ({
  onNavigateToAI,
  onOpenScan,
  invoiceRefreshKey,
}) => {
  const [periodType, setPeriodType] = useState<PeriodType>('month');
  const [subTab, setSubTab] = useState<ReportSubTab>('tong');

  const today = useMemo(() => offsetDays(0), []);
  const [dayVal, setDayVal] = useState(today);
  const [dailyInvoices, setDailyInvoices] = useState<DailyInvoiceSummary | null>(null);
  const [invoiceLoading, setInvoiceLoading] = useState(true);
  const [invoiceError, setInvoiceError] = useState('');
  const [invoiceRetry, setInvoiceRetry] = useState(0);
  const [monthVal, setMonthVal] = useState(today.slice(0, 7));

  // Current quarter: YYYY-Q
  const currentQuarter = useMemo(() => {
    const d = new Date();
    return `${d.getFullYear()}-${Math.floor(d.getMonth() / 3) + 1}`;
  }, []);
  const [quarterVal, setQuarterVal] = useState(currentQuarter);

  const [fromVal, setFromVal] = useState(offsetDays(-6));
  const [toVal, setToVal] = useState(today);

  useEffect(() => {
    let active = true;
    setInvoiceLoading(true);
    setInvoiceError('');
    void apiClient.get<DailyInvoiceSummary>('/reports/daily-invoices', {
      kitchen_id: KITCHEN_ID,
      business_date: dayVal,
    }).then((summary) => {
      if (active) setDailyInvoices(summary);
    }).catch((error: unknown) => {
      if (!active) return;
      setInvoiceError(error instanceof Error ? error.message : 'Không tải được tổng hợp hóa đơn.');
    }).finally(() => {
      if (active) setInvoiceLoading(false);
    });
    return () => {
      active = false;
    };
  }, [dayVal, invoiceRefreshKey, invoiceRetry]);

  // Month options (past 12 months)
  const monthOptions = useMemo(() => {
    const opts: Array<{ value: string; label: string }> = [];
    const d = new Date();
    for (let i = 0; i < 12; i++) {
      const y = d.getFullYear();
      const m = d.getMonth() + 1;
      const v = `${y}-${m < 10 ? '0' + m : m}`;
      opts.push({ value: v, label: `Tháng ${m}/${y}` });
      d.setMonth(d.getMonth() - 1);
    }
    return opts;
  }, []);

  // Quarter options (past 6 quarters)
  const quarterOptions = useMemo(() => {
    const opts: Array<{ value: string; label: string }> = [];
    const d = new Date();
    let y = d.getFullYear();
    let q = Math.floor(d.getMonth() / 3) + 1;
    for (let i = 0; i < 6; i++) {
      opts.push({ value: `${y}-${q}`, label: `Quý ${q}/${y}` });
      q--;
      if (q < 1) {
        q = 4;
        y--;
      }
    }
    return opts;
  }, []);

  // Calculate stats for current period
  const reportData: PeriodReportFull = useMemo(() => {
    return simulationStore.getReportStats(
      periodType,
      dayVal,
      monthVal,
      quarterVal,
      fromVal,
      toVal
    );
  }, [periodType, dayVal, monthVal, quarterVal, fromVal, toVal]);

  const s = reportData.current;
  const isAllZero = !s.rev && !s.waste && !s.donate && !s.sellN && !s.adjust && !s.useCost;

  return (
    <div>
      {/* Header */}
      <div className="view-hd">
        <small>Doanh thu, lợi nhuận và hao hụt theo kỳ</small>
        <h1>Thống kê</h1>
      </div>

      {/* Period Type Chips */}
      <div className="chips-bar">
        {[
          { key: 'day', label: 'Ngày' },
          { key: 'month', label: 'Tháng' },
          { key: 'quarter', label: 'Quý' },
          { key: 'range', label: 'Đợt' },
        ].map((item) => (
          <button
            key={item.key}
            type="button"
            className={`filter-chip ${periodType === item.key ? 'active' : ''}`}
            onClick={() => setPeriodType(item.key as PeriodType)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* Period Pickers */}
      <div style={{ marginTop: '8px' }}>
        {periodType === 'day' && (
          <label className="form-label">
            Chọn ngày
            <input
              type="date"
              className="ui-input"
              max={today}
              value={dayVal}
              onChange={(e) => setDayVal(e.target.value || today)}
            />
          </label>
        )}

        {periodType === 'month' && (
          <label className="form-label">
            Chọn tháng
            <select
              className="ui-input"
              value={monthVal}
              onChange={(e) => setMonthVal(e.target.value)}
            >
              {monthOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
        )}

        {periodType === 'quarter' && (
          <label className="form-label">
            Chọn quý
            <select
              className="ui-input"
              value={quarterVal}
              onChange={(e) => setQuarterVal(e.target.value)}
            >
              {quarterOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
        )}

        {periodType === 'range' && (
          <div className="grid-2">
            <label className="form-label">
              Từ ngày
              <input
                type="date"
                className="ui-input"
                max={today}
                value={fromVal}
                onChange={(e) => {
                  const val = e.target.value;
                  setFromVal(val);
                  if (val > toVal) setToVal(val);
                }}
              />
            </label>
            <label className="form-label">
              Đến ngày
              <input
                type="date"
                className="ui-input"
                max={today}
                value={toVal}
                onChange={(e) => {
                  const val = e.target.value;
                  setToVal(val);
                  if (val < fromVal) setFromVal(val);
                }}
              />
            </label>
          </div>
        )}
      </div>

      <div className="note" style={{ marginTop: '6px', fontSize: '12px', color: 'var(--muted)' }}>
        <b>Đang xem: {reportData.label}</b>
        {periodType === 'range' &&
          '. Đợt là khoảng ngày bạn tự chọn, ví dụ một đợt khuyến mãi hoặc một mùa cao điểm.'}
      </div>

      <section
        aria-label="Tổng hợp hóa đơn nhập cuối ngày"
        style={{
          marginTop: '14px',
          padding: '14px',
          border: '1px solid var(--line)',
          borderRadius: '12px',
          background: 'var(--card)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
          <div>
            <div className="section-h3">Hóa đơn nhập cuối ngày</div>
            <label className="form-label" style={{ marginTop: '6px' }}>
              Ngày tổng hợp
              <input
                type="date"
                className="ui-input"
                max={today}
                value={dayVal}
                onChange={(event) => setDayVal(event.target.value || today)}
              />
            </label>
          </div>
          <button type="button" className="ui-btn primary" onClick={() => onOpenScan(dayVal)}>
            Quét hóa đơn
          </button>
        </div>

        {invoiceLoading ? (
          <p className="note" role="status" style={{ marginTop: '10px' }}>Đang tổng hợp hóa đơn...</p>
        ) : invoiceError ? (
          <div role="alert" style={{ marginTop: '10px', color: 'var(--bad-fg)' }}>
            <p>{invoiceError}</p>
            <button type="button" className="filter-chip" onClick={() => setInvoiceRetry((value) => value + 1)}>
              Thử tải lại
            </button>
          </div>
        ) : (
          <>
            <div className="metrics-grid" style={{ marginTop: '12px' }}>
              <div><span>Tổng tiền hóa đơn</span><b>{formatMoney(dailyInvoices?.total_value_vnd || 0)}</b></div>
              <div><span>Số hóa đơn</span><b>{dailyInvoices?.invoice_count || 0}</b></div>
              <div><span>Dòng nguyên liệu</span><b>{dailyInvoices?.line_count || 0}</b></div>
            </div>
            {!dailyInvoices?.invoices.length ? (
              <p className="note" style={{ marginTop: '10px' }}>Chưa có hóa đơn nhập kho đã xác nhận trong ngày này.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
                {dailyInvoices.invoices.map((invoice) => (
                  <div key={invoice.id} className="product-row" style={{ cursor: 'default' }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <span className="product-name">{invoice.original_filename || 'Hóa đơn nhập kho'}</span>
                      <span className="product-sub">
                        {invoice.line_count} dòng · {invoice.source_format}
                        {invoice.file_url && (
                          <> · <a href={`${API_BASE_URL}${invoice.file_url}`} target="_blank" rel="noreferrer">Tải tệp</a></>
                        )}
                      </span>
                    </div>
                    <StatusTag tone="ok">{formatMoney(invoice.total_value_vnd)}</StatusTag>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </section>

      {/* Sub Tabs */}
      <SegmentedControl
        options={[
          { value: 'tong', label: 'Tổng quan' },
          { value: 'xuly', label: 'Đã xử lí' },
          { value: 'bo', label: 'Đã bỏ' },
        ]}
        activeValue={subTab}
        onChange={(tab) => setSubTab(tab as ReportSubTab)}
      />

      {isAllZero && (
        <div style={{ marginTop: '16px', textAlign: 'center', color: 'var(--muted)', padding: '12px 0' }}>
          Chưa có số liệu trong khoảng này. Hãy chọn kỳ khác hoặc quét báo cáo bán hàng ở nút Quét.
        </div>
      )}

      {/* SUBTAB 1: TỔNG QUAN */}
      {subTab === 'tong' && (
        <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* Key Metrics */}
          <div className="metrics-grid">
            <div>
              <span>Doanh thu</span>
              <b>{formatMoney(s.rev)}</b>
              <span
                style={{
                  color: reportData.isPartial
                    ? 'var(--muted)'
                    : s.rev >= reportData.previous.stats.rev
                    ? 'var(--ok-fg)'
                    : 'var(--bad-fg)',
                }}
              >
                {reportData.deltaRevText}
              </span>
            </div>

            <div>
              <span>Lợi nhuận</span>
              <b style={{ color: s.profit >= 0 ? 'var(--ok-fg)' : 'var(--bad-fg)' }}>
                {formatMoney(s.profit)}
              </b>
              <span
                style={{
                  color: reportData.isPartial
                    ? 'var(--muted)'
                    : s.profit >= reportData.previous.stats.profit
                    ? 'var(--ok-fg)'
                    : 'var(--bad-fg)',
                }}
              >
                {reportData.deltaProfitText}
              </span>
            </div>

            <div>
              <span>Số phần bán</span>
              <b>{s.portions} phần</b>
              <span>
                {s.rev && s.portions
                  ? `Bình quân ${formatMoney(s.saleRev / Math.max(1, s.portions))}/phần`
                  : '—'}
              </span>
            </div>
          </div>

          {/* AI Period Review Card */}
          {reportData.aiReview && (
            <div className="ui-card" style={{ border: '2px solid var(--accent-text)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <h3 style={{ margin: 0 }}>AI nhận xét kỳ này</h3>
                <StatusTag tone="neutral">
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <Icon name="spark" size={14} /> AI
                  </span>
                </StatusTag>
              </div>

              <span className="product-sub">
                Con số do chương trình tính từ số liệu kỳ đang xem. AI chỉ đọc và diễn giải. Trong demo, nhận xét tạo bằng quy tắc, bản thật do mô hình AI viết từ cùng số liệu.
              </span>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
                <b style={{ fontSize: '12px', color: 'var(--muted)' }}>Nhận xét</b>
                {reportData.aiReview.summary.map((text, idx) => (
                  <span key={idx}>{text}</span>
                ))}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
                <b style={{ fontSize: '12px', color: 'var(--muted)' }}>Nguyên nhân</b>
                {reportData.aiReview.causes.map((text, idx) => (
                  <span key={idx}>• {text}</span>
                ))}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
                <b style={{ fontSize: '12px', color: 'var(--muted)' }}>
                  Bất thường{reportData.aiReview.anomalies.length ? ` (${reportData.aiReview.anomalies.length})` : ''}
                </b>
                {reportData.aiReview.anomalies.length === 0 ? (
                  <span>AI chưa thấy điểm bất thường trong kỳ này.</span>
                ) : (
                  reportData.aiReview.anomalies.map((text, idx) => (
                    <span key={idx} style={{ color: 'var(--warn-fg)' }}>
                      • {text}
                    </span>
                  ))
                )}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
                <b style={{ fontSize: '12px', color: 'var(--muted)' }}>Gợi ý hành động</b>
                {reportData.aiReview.actions.map((text, idx) => (
                  <span key={idx}>• {text}</span>
                ))}
              </div>

              <button
                type="button"
                className="ui-btn outline"
                onClick={onNavigateToAI}
              >
                Hỏi thêm Trợ lí AI
              </button>
            </div>
          )}

          {/* Buckets Bar Chart */}
          <div className="ui-card">
            <h3>Theo {reportData.bname}</h3>
            {reportData.buckets.map((b, idx) => (
              <div
                key={idx}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '84px 1fr',
                  gap: '8px',
                  alignItems: 'center',
                }}
              >
                <span
                  className="product-sub"
                  style={b.isSelected ? { fontWeight: 700, color: 'var(--ink)' } : {}}
                >
                  {b.label}
                </span>
                <div>
                  <div className="progress-hbar">
                    <i style={{ width: `${b.revenuePercent}%` }} />
                  </div>
                  <span className="product-sub">
                    Doanh thu <b>{formatMoney(b.stats.rev)}</b> · Lợi nhuận{' '}
                    <b style={{ color: b.stats.profit >= 0 ? 'var(--ok-fg)' : 'var(--bad-fg)' }}>
                      {formatMoney(b.stats.profit)}
                    </b>
                  </span>
                </div>
              </div>
            ))}
            <span className="product-sub" style={{ marginTop: '4px' }}>
              Cột dài theo doanh thu. Lợi nhuận đã trừ giá vốn, quyên góp, hao hụt và chênh lệch kiểm kho trong từng đoạn.
            </span>
          </div>

          {/* P&L Statement with 2 Profit Lines */}
          <div className="ui-card">
            <h3>Lãi lỗ cả kỳ</h3>
            <div className="kv-row">
              <span>Doanh thu bán món</span>
              <b>{formatMoney(s.saleRev)}</b>
            </div>
            <div className="kv-row">
              <span>Thu từ bán thu mua</span>
              <b>{formatMoney(s.sellRev)}</b>
            </div>
            <div className="kv-row">
              <span>Giá vốn nguyên liệu đã bán</span>
              <b>−{formatMoney(s.cogs)}</b>
            </div>
            <div className="kv-row">
              <span>Quyên góp (giá trị hàng)</span>
              <b>−{formatMoney(s.donate)}</b>
            </div>
            <div className="kv-row">
              <span>Hao hụt do bỏ đi</span>
              <b>−{formatMoney(s.waste)}</b>
            </div>
            <div className="kv-row">
              <span>Chênh lệch kiểm kho</span>
              <b>−{formatMoney(s.adjust)}</b>
            </div>
            <div className="kv-row">
              <span>
                <b style={{ color: 'var(--ink)' }}>Lợi nhuận</b>
              </span>
              <b style={{ color: s.profit >= 0 ? 'var(--ok-fg)' : 'var(--bad-fg)' }}>
                {formatMoney(s.profit)}
              </b>
            </div>
          </div>

          <div className="note" style={{ fontSize: '12px', color: 'var(--muted)', lineHeight: 1.5 }}>
            Lợi nhuận = Doanh thu − Giá vốn − Quyên góp − Hao hụt − Chênh lệch kiểm kho. Giá vốn lấy từ giá nhập thực tế của đúng đợt hàng đã dùng.
          </div>

          {/* Dish Profit Breakdown */}
          <div className="section-h3">Lợi nhuận theo món trong kỳ</div>
          {reportData.dishSales.length === 0 ? (
            <div className="note">Chưa có món nào được bán trong kỳ này.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {reportData.dishSales.map((d) => (
                <div key={d.name} className="product-row" style={{ cursor: 'default' }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <span className="product-name">{d.name}</span>
                    <span className="product-sub">
                      {d.portions} phần · doanh thu {formatMoney(d.revenue)} · giá vốn {formatMoney(d.cost)}
                    </span>
                  </div>
                  <StatusTag tone={d.profit >= 0 ? 'ok' : 'bad'}>
                    {formatMoney(d.profit)}
                  </StatusTag>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* SUBTAB 2: ĐÃ XỬ LÍ */}
      {subTab === 'xuly' && (
        <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div className="ui-card">
            <h3>Đã xử lí, không phải bỏ</h3>
            <div className="kv-row">
              <span>Giá trị hàng được cứu</span>
              <b>{formatMoney(s.donate + s.sellCost + s.repCost)}</b>
            </div>
            <div className="kv-row">
              <span>Thu về từ thu mua và món mới</span>
              <b>{formatMoney(s.sellRev + s.repRev)}</b>
            </div>
            <span className="product-sub">
              Phần này tách riêng khỏi Đã bỏ, vì hàng vẫn dùng được và mang lại giá trị.
            </span>
          </div>

          <div className="ui-card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span className="product-name">Quyên góp</span>
              <StatusTag tone="neutral">{s.donateN} lần</StatusTag>
            </div>
            <span className="product-sub">Giá trị {formatMoney(s.donate)}</span>
          </div>

          <div className="ui-card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span className="product-name">Bán cho chỗ thu mua</span>
              <StatusTag tone="neutral">{s.sellN} lần</StatusTag>
            </div>
            <span className="product-sub">
              Thu về {formatMoney(s.sellRev)} trên giá vốn {formatMoney(s.sellCost)}
            </span>
          </div>

          <div className="ui-card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span className="product-name">Làm món mới</span>
              <StatusTag tone="neutral">{s.repN} phần</StatusTag>
            </div>
            <span className="product-sub">
              Doanh thu {formatMoney(s.repRev)}, giá vốn {formatMoney(s.repCost)}
            </span>
          </div>

          <div className="section-h3">Trong kỳ</div>
          {reportData.repurposedLogs.length === 0 ? (
            <div className="note">Chưa có mục nào trong kỳ này.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {reportData.repurposedLogs.map((l) => {
                const text =
                  l.type === 'donate'
                    ? `Quyên góp ${l.qty} kg ${l.name}`
                    : l.type === 'sell'
                    ? `Bán thu mua ${l.qty} kg ${l.name}`
                    : `Nấu ${l.portions} phần ${l.dish}`;

                return (
                  <div key={l.id} className="product-row" style={{ cursor: 'default' }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <span className="product-name">{text}</span>
                      <span className="product-sub">
                        {l.date.split('-').reverse().slice(0, 2).join('/')}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* SUBTAB 3: ĐÃ BỎ */}
      {subTab === 'bo' && (
        <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div className="ui-card">
            <h3>Đã bỏ</h3>
            <div className="kv-row">
              <span>Số lần bỏ</span>
              <b>{s.wasteN}</b>
            </div>
            <div className="kv-row">
              <span>Giá trị hao hụt</span>
              <b style={{ color: 'var(--bad-fg)' }}>{formatMoney(s.waste)}</b>
            </div>
            <div className="kv-row">
              <span>So với {reportData.previous.label}</span>
              <b>
                {reportData.isPartial
                  ? 'Chưa so sánh (kỳ chưa kết thúc)'
                  : reportData.deltaProfitText.includes('Chưa có')
                  ? '—'
                  : 'Theo số liệu đối ứng'}
              </b>
            </div>
          </div>

          {s.waste > 0 && (
            <>
              <div className="ui-card">
                <h3>Theo lí do</h3>
                {Object.entries(reportData.wasteByReason)
                  .sort((a, b) => b[1] - a[1])
                  .map(([reason, cost]) => (
                    <div key={reason}>
                      <div className="kv-row" style={{ border: 'none', padding: '0 0 4px' }}>
                        <span>{reason}</span>
                        <b>{formatMoney(cost)}</b>
                      </div>
                      <div className="progress-hbar">
                        <i
                          style={{
                            width: `${(cost / s.waste) * 100}%`,
                            background: 'var(--bad-fg)',
                          }}
                        />
                      </div>
                    </div>
                  ))}
              </div>

              <div className="ui-card">
                <h3>Theo mặt hàng</h3>
                {reportData.wasteByIngredient.slice(0, 4).map((g) => (
                  <div key={g.name} className="kv-row">
                    <span>
                      {capitalize(g.name)} · {g.count} lần
                    </span>
                    <b>{formatMoney(g.cost)}</b>
                  </div>
                ))}
              </div>
            </>
          )}

          <div className="ui-card" style={{ border: '2px solid var(--accent-text)' }}>
            <h3>AI phân tích cho lần nhập tới</h3>
            <span className="product-sub">
              AI phân tích trên toàn bộ lịch sử, không chỉ riêng kỳ đang xem.
            </span>
            <span style={{ fontSize: '13px', color: 'var(--ink)' }}>
              • Hao hụt lớn nhất đến từ rau muống, lí do nhiều nhất: hết hạn.
            </span>
            <span style={{ fontSize: '13px', color: 'var(--ink)' }}>
              • Ưu tiên quyên góp, bán thu mua hoặc đưa vào thực đơn trước hạn 2 ngày.
            </span>
          </div>

          <div className="section-h3">Trong kỳ</div>
          {reportData.wasteLogs.length === 0 ? (
            <div className="note">Không có mục nào bị bỏ trong kỳ này.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {reportData.wasteLogs.map((l) => (
                <div key={l.id} className="product-row" style={{ cursor: 'default' }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <span className="product-name">
                      {capitalize(l.name || '')} · {l.qty} kg
                    </span>
                    <span className="product-sub">
                      {l.date.split('-').reverse().slice(0, 2).join('/')} · {l.reason}
                      {l.note ? `: ${l.note}` : ''}
                    </span>
                  </div>
                  <StatusTag tone="bad">{formatMoney(l.cost || 0)}</StatusTag>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
