import React, { useState, useMemo, useRef, useEffect } from 'react';
import {
  simulationStore,
  formatMoney,
  formatQty,
  capitalize,
  calculateDaysLeft,
  formatDaysLabel,
} from '../services/mock/simulationStore';
import { SegmentedControl } from '../components/common/SegmentedControl';
import { StatusTag } from '../components/common/StatusTag';
import { Icon } from '../components/common/Icon';
import {
  VerifiedFact,
  RecommendationItem,
  ProposedAction,
  ReplenishmentItem,
  AssistantMessageResponse,
} from '../types';
import { apiClient } from '../services/api/client';

type AISubTab = 'goiy' | 'pt' | 'kho' | 'hd';
type ReplenishFilter = 'items' | 'insufficient' | 'no_cons';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  facts?: VerifiedFact[];
  recommendations?: RecommendationItem[];
  data_gaps?: string[];
  proposed_actions?: ProposedAction[];
  provider?: 'rule_based' | 'external';
  isLoading?: boolean;
}

interface AssistantViewProps {
  onProcessBatch?: (batchId: string) => void;
  onOpenScan?: () => void;
  onOpenBell?: () => void;
  onOpenDish?: (dishId?: string) => void;
  onShowToast: (msg: string) => void;
}

const KITCHEN_ID = import.meta.env.VITE_KITCHEN_ID || '00000000-0000-0000-0000-000000000002';

export const AssistantView: React.FC<AssistantViewProps> = ({
  onProcessBatch,
  onOpenScan,
  onOpenBell,
  onOpenDish,
  onShowToast,
}) => {
  const [subTab, setSubTab] = useState<AISubTab>('goiy');
  const [replFilter, setReplFilter] = useState<ReplenishFilter>('items');
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: 'init-1',
      role: 'assistant',
      text: 'Xin chào! Mình là trợ lí kho bếp (Fact-based Assistant). Mọi số liệu và đề xuất của mình đều được đối chiếu trực tiếp với sổ cái và số lượng thực tế trong kho.',
      facts: [
        {
          id: 'F-SYS-01',
          tool: 'grounding_engine',
          label: 'Chế độ Grounding',
          value: 'Bật (Chống bịa đặt số liệu)',
          as_of: new Date().toISOString().slice(0, 10),
        },
      ],
      recommendations: [
        {
          text: 'Bạn có thể hỏi bất kỳ câu hỏi nào về tồn kho, kiểm tra lô cận date, gợi ý đặt hàng D25 hoặc phân tích lãi lỗ từng món ăn.',
          assumptions: ['Dữ liệu sổ cái và hạn dùng được cập nhật liên tục'],
          basis: 'VERIFIED_FACT',
        },
      ],
    },
  ]);
  const [inputQuestion, setInputQuestion] = useState('');
  const [isSending, setIsSending] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const subTabOptions: Array<{ value: AISubTab; label: string }> = [
    { value: 'goiy', label: 'Gợi ý' },
    { value: 'pt', label: 'Nhập–xuất' },
    { value: 'kho', label: 'Kho chung' },
    { value: 'hd', label: 'Hỏi đáp' },
  ];

  // 1. Data for Gợi ý - Lô cận date
  const expiringBatches = useMemo(() => {
    return simulationStore
      .getState()
      .batches.filter((b) => {
        const d = calculateDaysLeft(b.expiry_date);
        return d >= 0 && d <= 3 && parseFloat(b.remaining_qty) > 0.0001;
      })
      .sort((a, b) => (a.expiry_date || '').localeCompare(b.expiry_date || ''));
  }, []);

  // 2. Data for Gợi ý - Thuật toán bổ sung hàng D25
  const replenishment = useMemo(() => {
    return simulationStore.getD25ReplenishmentSuggestions();
  }, []);

  // 3. Data for Nhập-xuất
  const cashflow = useMemo(() => simulationStore.getAICashflow(), []);
  const productInsights = useMemo(() => simulationStore.getAIProductInsights(), []);

  // 4. Data for Kho chung
  const stockOverview = useMemo(() => simulationStore.getAIStockOverview(), []);

  // Chat handling with Grounding
  const handleSendQuestion = async (questionToSend?: string) => {
    const q = (questionToSend || inputQuestion).trim();
    if (!q || isSending) return;

    setInputQuestion('');
    const userMsgId = `usr-${Date.now()}`;
    const loadingMsgId = `loading-${Date.now()}`;

    setChatMessages((prev) => [
      ...prev,
      { id: userMsgId, role: 'user', text: q },
      { id: loadingMsgId, role: 'assistant', text: 'Đang truy xuất sổ cái và phân tích dữ liệu kho...', isLoading: true },
    ]);
    setIsSending(true);

    try {
      const historyTurns = chatMessages
        .filter((m) => !m.isLoading)
        .slice(-6)
        .map((m) => ({ role: m.role, text: m.text }));

      const res = await apiClient.request<AssistantMessageResponse>('/assistant/messages', {
        method: 'POST',
        params: { kitchen_id: KITCHEN_ID },
        body: JSON.stringify({ message: q, history: historyTurns }),
      });

      setChatMessages((prev) =>
        prev.map((m) => {
          if (m.id === loadingMsgId) {
            return {
              id: res.request_id || `ast-${Date.now()}`,
              role: 'assistant',
              text: res.answer_text,
              facts: res.facts,
              recommendations: res.recommendations,
              data_gaps: res.data_gaps,
              proposed_actions: res.proposed_actions,
              provider: res.provider,
              isLoading: false,
            };
          }
          return m;
        })
      );
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Không kết nối được dữ liệu kho.';
      setChatMessages((prev) =>
        prev.map((m) => {
          if (m.id === loadingMsgId) {
            return {
              id: `err-${Date.now()}`,
              role: 'assistant',
              text: `Không đọc được dữ liệu thật từ máy chủ: ${errorMessage}`,
              isLoading: false,
            };
          }
          return m;
        })
      );
    } finally {
      setIsSending(false);
    }
  };

  const handleExecuteAction = (act: ProposedAction) => {
    switch (act.type) {
      case 'OPEN_EXPIRING_BATCH':
        if (act.target_id && onProcessBatch) {
          onProcessBatch(act.target_id);
        } else {
          onShowToast(`Mở xử lý đợt: ${act.label}`);
        }
        break;
      case 'OPEN_REPLENISHMENT':
        setSubTab('goiy');
        setReplFilter('items');
        onShowToast('Đã chuyển sang bảng đề xuất bổ sung hàng D25');
        break;
      case 'OPEN_SHORTAGE':
        if (onOpenBell) {
          onOpenBell();
        } else {
          onShowToast('Mở danh sách thiếu hụt Option C');
        }
        break;
      case 'OPEN_DISH':
        if (onOpenDish) {
          onOpenDish(act.target_id || undefined);
        } else {
          onShowToast(`Mở chi tiết món ăn: ${act.label}`);
        }
        break;
      default:
        onShowToast(`Thực hiện: ${act.label}`);
    }
  };

  useEffect(() => {
    if (subTab === 'hd') {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, subTab, isSending]);

  return (
    <div>
      {/* Header */}
      <div className="view-hd">
        <small>Dựa trên dữ liệu thực tế và sổ cái kho bếp</small>
        <h1>Trợ lí AI & Bổ sung hàng</h1>
      </div>

      {/* Sub Tabs */}
      <SegmentedControl
        options={subTabOptions}
        activeValue={subTab}
        onChange={(tab) => setSubTab(tab)}
      />

      {/* SUBTAB 1: GỢI Ý & ĐỀ XUẤT BỔ SUNG HÀNG (D25) */}
      {subTab === 'goiy' && (
        <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* PHẦN A: ƯU TIÊN XỬ LÝ HÔM NAY */}
          <div>
            <div className="section-h3" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Ưu tiên xử lí hôm nay</span>
              <span style={{ fontSize: '12px', fontWeight: 500, color: 'var(--muted)' }}>
                {expiringBatches.length} đợt cận date
              </span>
            </div>

            {expiringBatches.length === 0 ? (
              <div className="ui-card" style={{ marginTop: '8px', textAlign: 'center', color: 'var(--muted)', padding: '16px' }}>
                Không có đợt nào sắp hết hạn trong 3 ngày tới. Tình trạng hạn sử dụng an toàn.
              </div>
            ) : (
              <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {expiringBatches.map((b) => {
                  const daysLeft = calculateDaysLeft(b.expiry_date);
                  const tone = daysLeft < 0 ? 'bad' : daysLeft <= 2 ? 'warn' : 'ok';
                  const rankList = simulationStore.getDishRank();
                  const matchedDish = rankList.find((r) =>
                    r.dish.recipe.some(
                      (i) => i.ingredient_name && i.ingredient_name.toLowerCase() === b.ingredient_name.toLowerCase()
                    )
                  );

                  const suggestionText =
                    matchedDish && matchedDish.maxPortions > 0
                      ? `nấu ${matchedDish.dish.name} (${matchedDish.maxPortions} phần, lãi gộp dự kiến ${formatMoney(matchedDish.grossMargin * matchedDish.maxPortions)}), hoặc quyên góp, bán thu mua.`
                      : 'quyên góp hoặc bán cho chỗ thu mua để không phải bỏ.';

                  return (
                    <div key={b.id} className="ui-card">
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div>
                          <span className="product-name">
                            {capitalize(b.ingredient_name)} · {formatQty(parseFloat(b.remaining_qty))} {b.unit}
                          </span>
                          <span className="product-sub">
                            Đợt nhập {b.received_on.split('-').reverse().slice(0, 2).join('/')} · Hạn {b.expiry_date}
                          </span>
                        </div>
                        <StatusTag tone={tone}>{formatDaysLabel(daysLeft)}</StatusTag>
                      </div>

                      <span style={{ fontSize: '13px', color: 'var(--ink)', lineHeight: 1.5, marginTop: '4px' }}>
                        <b>AI gợi ý:</b> {suggestionText}
                      </span>

                      <button
                        type="button"
                        className="ui-btn primary full"
                        style={{ marginTop: '6px' }}
                        onClick={() => {
                          if (onProcessBatch) {
                            onProcessBatch(b.id);
                          } else {
                            onShowToast(`Mở quy trình xử lý lô ${b.ingredient_name} (${b.id})`);
                          }
                        }}
                      >
                        Xử lí đợt này
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* PHẦN B: ĐỀ XUẤT BỔ SUNG HÀNG (THUẬT TOÁN D25) */}
          <div>
            <div className="section-h3" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Đề xuất bổ sung hàng (Thuật toán D25)</span>
              <span style={{ fontSize: '11px', background: 'var(--accent-tint, rgba(16, 149, 193, 0.1))', color: 'var(--accent)', padding: '2px 8px', borderRadius: '12px', fontWeight: 600 }}>
                Chuẩn Revision 6.3
              </span>
            </div>

            {/* Thông số D25 Banner */}
            <div className="ui-card" style={{ marginTop: '8px', padding: '10px 14px', background: 'var(--bg-subtle, rgba(0,0,0,0.02))' }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', fontSize: '12px', color: 'var(--muted)' }}>
                <span>🎯 Mục tiêu bao phủ: <b style={{ color: 'var(--ink)' }}>{String(replenishment.parameters.target_coverage_days || 3)} ngày</b></span>
                <span>📅 Cửa sổ quan sát: <b style={{ color: 'var(--ink)' }}>{String(replenishment.parameters.consumption_window_days || 14)} ngày</b></span>
                <span>⏱ Ngưỡng lịch sử: <b style={{ color: 'var(--ink)' }}>{String(replenishment.parameters.min_history_days || 7)} ngày</b></span>
                <span>📦 Ngày chốt: <b style={{ color: 'var(--ink)' }}>{replenishment.as_of}</b></span>
              </div>
            </div>

            {/* Replenishment Filter Chips */}
            <div className="chips-bar" style={{ marginTop: '8px' }}>
              <button
                type="button"
                className={`filter-chip ${replFilter === 'items' ? 'active' : ''}`}
                onClick={() => setReplFilter('items')}
              >
                Cần đặt hàng ({replenishment.items.length})
              </button>
              <button
                type="button"
                className={`filter-chip ${replFilter === 'insufficient' ? 'active' : ''}`}
                onClick={() => setReplFilter('insufficient')}
              >
                Chưa đủ lịch sử ({replenishment.insufficient_data.length})
              </button>
              <button
                type="button"
                className={`filter-chip ${replFilter === 'no_cons' ? 'active' : ''}`}
                onClick={() => setReplFilter('no_cons')}
              >
                Không có tiêu thụ ({replenishment.no_recent_consumption.length})
              </button>
            </div>

            {/* 1. Nhóm Cần đặt hàng */}
            {replFilter === 'items' && (
              <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {replenishment.items.length === 0 ? (
                  <div className="ui-card" style={{ textAlign: 'center', color: 'var(--muted)', padding: '16px' }}>
                    Tồn kho khả dụng của các mặt hàng hiện tại đều đủ đáp ứng mục tiêu bao phủ D25.
                  </div>
                ) : (
                  replenishment.items.map((item: ReplenishmentItem) => {
                    const ruleTone = item.rule === 'BOTH' ? 'bad' : item.rule === 'MIN_STOCK_ONLY' ? 'warn' : 'ok';
                    const ruleLabel =
                      item.rule === 'BOTH'
                        ? 'Dưới tối thiểu & Thiếu bao phủ'
                        : item.rule === 'MIN_STOCK_ONLY'
                        ? 'Dưới tồn tối thiểu'
                        : 'Thiếu ngày bao phủ';

                    return (
                      <div key={item.ingredient_id} className="ui-card" style={{ borderLeft: '4px solid var(--accent)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <div>
                            <span className="product-name">{capitalize(item.ingredient_name)}</span>
                            <span className="product-sub">
                              Tồn khả dụng: <b>{item.usable_qty} {item.unit}</b>
                            </span>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <span style={{ fontSize: '16px', fontWeight: 700, color: 'var(--accent)' }}>
                              +{item.suggested_order_qty} {item.unit}
                            </span>
                            <div style={{ fontSize: '11px', color: 'var(--muted)' }}>Đề xuất đặt</div>
                          </div>
                        </div>

                        {/* Metric stats row */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px', margin: '8px 0', padding: '8px', background: 'var(--bg-subtle, rgba(0,0,0,0.02))', borderRadius: '8px', fontSize: '12px' }}>
                          <div>
                            <span style={{ color: 'var(--muted)' }}>Tiêu thụ TB/ngày: </span>
                            <b>{item.avg_daily_consumption ? `${item.avg_daily_consumption} ${item.unit}` : 'N/A'}</b>
                          </div>
                          <div>
                            <span style={{ color: 'var(--muted)' }}>Số ngày còn đủ: </span>
                            <b>{item.days_of_cover ? `~${item.days_of_cover} ngày` : 'N/A'}</b>
                          </div>
                          <div>
                            <span style={{ color: 'var(--muted)' }}>Lượng thô (raw): </span>
                            <span>{item.raw_order_qty} {item.unit}</span>
                          </div>
                          <div>
                            <span style={{ color: 'var(--muted)' }}>Bước đặt (step): </span>
                            <span>{item.order_step || '0.5'} {item.unit}</span>
                          </div>
                        </div>

                        {/* Rule and Basis Tag */}
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
                          <StatusTag tone={ruleTone}>{ruleLabel}</StatusTag>
                          <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '4px', background: 'rgba(0,0,0,0.05)', color: 'var(--muted)', fontWeight: 600 }}>
                            Cơ sở: {item.basis}
                          </span>
                        </div>

                        {/* Assumptions */}
                        {item.assumptions && item.assumptions.length > 0 && (
                          <div style={{ marginTop: '6px', fontSize: '12px', color: 'var(--muted)', lineHeight: 1.4 }}>
                            {item.assumptions.map((asm, aIdx) => (
                              <div key={aIdx}>• {asm}</div>
                            ))}
                          </div>
                        )}

                        {/* Action CTA */}
                        <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                          <button
                            type="button"
                            className="ui-btn primary"
                            style={{ flex: 1, padding: '6px 12px', fontSize: '13px' }}
                            onClick={() => {
                              if (onOpenScan) {
                                onOpenScan();
                              } else {
                                onShowToast(`Thêm ${capitalize(item.ingredient_name)} (${item.suggested_order_qty} ${item.unit}) vào phiếu đặt hàng`);
                              }
                            }}
                          >
                            Tạo phiếu nhập hàng
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {/* 2. Nhóm Chưa đủ lịch sử */}
            {replFilter === 'insufficient' && (
              <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ fontSize: '12px', color: 'var(--muted)', lineHeight: 1.4, padding: '4px 2px' }}>
                  Các mặt hàng dưới đây chưa đủ điều kiện đánh giá theo quy tắc chu kỳ bao phủ (số ngày quan sát &lt; ngưỡng tối thiểu). Nếu dưới mức tồn tối thiểu, hệ thống chỉ đề xuất theo ngưỡng tối thiểu (MIN_STOCK_ONLY).
                </div>

                {replenishment.insufficient_data.length === 0 ? (
                  <div className="ui-card" style={{ textAlign: 'center', color: 'var(--muted)', padding: '16px' }}>
                    Tất cả mặt hàng đều đã có đủ lịch sử quan sát.
                  </div>
                ) : (
                  replenishment.insufficient_data.map((ins, idx) => {
                    const reasonText =
                      ins.reason === 'NO_HISTORY'
                        ? 'Chưa có bất kỳ biến động nhập/xuất nào'
                        : ins.reason === 'NO_COMPLETE_DAYS'
                        ? 'Mọi biến động đều diễn ra hôm nay, chưa có ngày trọn vẹn kết thúc'
                        : `Số ngày có số liệu (${ins.observed_days} ngày) ngắn hơn ngưỡng tối thiểu (${String(replenishment.parameters.min_history_days)} ngày)`;

                    return (
                      <div key={idx} className="ui-card">
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span className="product-name">{capitalize(ins.ingredient_name)}</span>
                          <StatusTag tone="warn">{ins.reason}</StatusTag>
                        </div>
                        <div style={{ fontSize: '13px', color: 'var(--ink)', marginTop: '4px' }}>
                          <b>Lý do bỏ qua chu kỳ:</b> {reasonText}
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '2px' }}>
                          Số ngày quan sát thực tế: {ins.observed_days} ngày
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {/* 3. Nhóm Không có tiêu thụ gần đây */}
            {replFilter === 'no_cons' && (
              <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ fontSize: '12px', color: 'var(--muted)', lineHeight: 1.4, padding: '4px 2px' }}>
                  Các mặt hàng có đủ lịch sử quan sát nhưng không phát sinh tiêu thụ trong kỳ và tồn kho khả dụng vẫn đạt mức an toàn.
                </div>

                {replenishment.no_recent_consumption.length === 0 ? (
                  <div className="ui-card" style={{ textAlign: 'center', color: 'var(--muted)', padding: '16px' }}>
                    Không có mặt hàng nào thuộc nhóm này.
                  </div>
                ) : (
                  replenishment.no_recent_consumption.map((nc, idx) => (
                    <div key={idx} className="ui-card">
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div>
                          <span className="product-name">{capitalize(nc.ingredient_name)}</span>
                          <span className="product-sub">
                            Đang tồn kho: <b>{nc.usable_qty} {nc.unit}</b>
                          </span>
                        </div>
                        <StatusTag tone="ok">ĐỦ DÙNG</StatusTag>
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '4px' }}>
                        Không có lượt xuất bán hoặc nấu chế biến trong cửa sổ {String(replenishment.parameters.consumption_window_days)} ngày qua.
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* SUBTAB 2: NHẬP-XUẤT */}
      {subTab === 'pt' && (
        <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div className="ui-card">
            <h3>Dòng tiền hàng hóa</h3>
            <div className="kv-row">
              <span>Tổng nhập</span>
              <b>{formatMoney(cashflow.inV)}</b>
            </div>
            <div className="kv-row">
              <span>Tổng xuất (bán, xử lí, bỏ)</span>
              <b>{formatMoney(cashflow.out)}</b>
            </div>
            <div className="kv-row">
              <span>Còn trong kho</span>
              <b>{formatMoney(cashflow.stockVal)}</b>
            </div>

            {/* Multi-color stack bar */}
            <div className="color-stack-bar" role="img" aria-label="Cơ cấu hàng nhập">
              {cashflow.segments.map((seg, idx) => (
                <i
                  key={idx}
                  style={{
                    width: `${seg.percent}%`,
                    background: seg.color,
                  }}
                />
              ))}
            </div>

            {/* Legend */}
            <div className="color-legend">
              {cashflow.segments.map((seg, idx) => (
                <span key={idx}>
                  <i style={{ background: seg.color }} />
                  {seg.label} {seg.percent}%
                </span>
              ))}
            </div>

            <span className="product-sub" style={{ marginTop: '4px' }}>
              Tổng nhập − Tổng xuất = Giá trị còn trong kho. Nếu kiểm kho thực tế lệch, phần lệch được ghi là hao hụt chưa rõ.
            </span>
          </div>

          {/* Cảnh báo nhập */}
          <div className="ui-card">
            <h3>Cảnh báo nhập</h3>
            <span style={{ fontSize: '13px', color: 'var(--ink)', lineHeight: 1.5 }}>
              {cashflow.unusualWarningCount > 0
                ? `Đã có ${cashflow.unusualWarningCount} lần AI cảnh báo số lượng nhập bất thường.`
                : 'Chưa có lần nhập bất thường nào.'}{' '}
              AI so sánh mỗi lần nhập với mức nhập thường ngày của từng mặt hàng.
            </span>
          </div>

          {/* Nhận xét theo sản phẩm */}
          <div className="section-h3">Nhận xét theo sản phẩm</div>
          <div className="product-sub" style={{ marginTop: '-4px' }}>
            Xếp theo giá trị hao hụt, nhiều nhất trước.
          </div>

          {productInsights.length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--muted)', padding: '16px 0' }}>
              Chưa có sản phẩm nào bị bỏ, nên chưa có nhận xét.
            </div>
          ) : (
            productInsights.map((item) => (
              <div key={item.name} className="ui-card">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <span className="product-name">{capitalize(item.name)}</span>
                    <span className="product-sub">
                      Đã bỏ {formatQty(item.qty)} {item.unit} qua {item.count} lần
                    </span>
                  </div>
                  <StatusTag tone="bad">~{formatMoney(item.cost)}</StatusTag>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '13px', marginTop: '6px' }}>
                  <b style={{ fontSize: '12px', color: 'var(--muted)' }}>Lí do</b>
                  <span>{item.reasonsText}</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '13px' }}>
                  <b style={{ fontSize: '12px', color: 'var(--muted)' }}>Nhận xét</b>
                  <span>{item.observations}</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '13px' }}>
                  <b style={{ fontSize: '12px', color: 'var(--muted)' }}>Gợi ý lần nhập tới</b>
                  <span>{item.suggestion}</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* SUBTAB 3: KHO CHUNG */}
      {subTab === 'kho' && (
        <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div className="ui-card">
            <h3>Tổng quan kho</h3>
            <div className="kv-row">
              <span>Số mặt hàng</span>
              <b>{stockOverview.totalIngredients}</b>
            </div>
            <div className="kv-row">
              <span>Số đợt hàng còn tồn</span>
              <b>{stockOverview.totalBatches}</b>
            </div>
            <div className="kv-row">
              <span>Giá trị tồn kho</span>
              <b>{formatMoney(stockOverview.stockVal)}</b>
            </div>
            <span className="product-sub">
              Mỗi lần nhập của một mặt hàng là một đợt. Ví dụ thịt ba rọi nhập 2 lần thì tính 1 mặt hàng và 2 đợt.
            </span>
          </div>

          <div className="ui-card">
            <h3>Theo nơi cất (số mặt hàng)</h3>
            <div>
              <div className="kv-row" style={{ border: 'none', padding: '0 0 4px' }}>
                <span>Tủ lạnh</span>
                <b>{stockOverview.byLocation.fridge} mặt hàng</b>
              </div>
              <div className="progress-hbar">
                <i
                  style={{
                    width: `${stockOverview.totalIngredients ? (stockOverview.byLocation.fridge / stockOverview.totalIngredients) * 100 : 0}%`,
                  }}
                />
              </div>
            </div>

            <div>
              <div className="kv-row" style={{ border: 'none', padding: '0 0 4px' }}>
                <span>Tủ bếp</span>
                <b>{stockOverview.byLocation.pantry} mặt hàng</b>
              </div>
              <div className="progress-hbar">
                <i
                  style={{
                    width: `${stockOverview.totalIngredients ? (stockOverview.byLocation.pantry / stockOverview.totalIngredients) * 100 : 0}%`,
                  }}
                />
              </div>
            </div>

            <div>
              <div className="kv-row" style={{ border: 'none', padding: '0 0 4px' }}>
                <span>Ngăn đông</span>
                <b>{stockOverview.byLocation.freezer} mặt hàng</b>
              </div>
              <div className="progress-hbar">
                <i
                  style={{
                    width: `${stockOverview.totalIngredients ? (stockOverview.byLocation.freezer / stockOverview.totalIngredients) * 100 : 0}%`,
                  }}
                />
              </div>
            </div>
          </div>

          <div className="ui-card">
            <h3>Theo tình trạng (số mặt hàng)</h3>
            <div className="kv-row">
              <span>Còn lâu</span>
              <b>{stockOverview.byTone.ok} mặt hàng</b>
            </div>
            <div className="kv-row">
              <span>Sắp hết hạn (trong 3 ngày)</span>
              <b>{stockOverview.byTone.warn} mặt hàng</b>
            </div>
            <div className="kv-row">
              <span>Đã có đợt hết hạn</span>
              <b>{stockOverview.byTone.bad} mặt hàng</b>
            </div>
            <span className="product-sub">
              Mỗi mặt hàng tính theo đợt hết hạn sớm nhất của nó.
            </span>
          </div>

          <div className="ui-card">
            <h3>Cần nhập thêm ({stockOverview.needReorder.length} mặt hàng)</h3>
            {stockOverview.needReorder.length === 0 ? (
              <span className="product-sub">Chưa có mặt hàng nào thiếu.</span>
            ) : (
              stockOverview.needReorder.map((t, idx) => (
                <span key={idx} style={{ fontSize: '13px', color: 'var(--ink)' }}>
                  • {t}
                </span>
              ))
            )}
          </div>

          <div className="ui-card">
            <h3>Đang dư so với mức thường dùng ({stockOverview.overstocked.length} mặt hàng)</h3>
            {stockOverview.overstocked.length === 0 ? (
              <span className="product-sub">Chưa có mặt hàng nào dư.</span>
            ) : (
              stockOverview.overstocked.map((t, idx) => (
                <span key={idx} style={{ fontSize: '13px', color: 'var(--ink)' }}>
                  • {t}
                </span>
              ))
            )}
          </div>
        </div>
      )}

      {/* SUBTAB 4: HỎI ĐÁP GROUNDED CHAT */}
      {subTab === 'hd' && (
        <div style={{ marginTop: '12px' }}>
          {/* Quick chips */}
          <div className="chips-bar">
            {[
              'Hôm nay nên xử lí gì trước?',
              'Đề xuất đặt hàng theo D25',
              'Thịt ba rọi còn bao nhiêu?',
              'Thiếu hụt Option C đang mở?',
              'Món nào lãi nhất?',
              'Đồ nào bỏ nhiều nhất?',
            ].map((q) => (
              <button
                key={q}
                type="button"
                className="filter-chip"
                onClick={() => handleSendQuestion(q)}
                disabled={isSending}
              >
                {q}
              </button>
            ))}
          </div>

          {/* Chat Bubble List */}
          <div className="chat-container">
            {chatMessages.map((m) => (
              <div
                key={m.id}
                className={`chat-bubble ${m.role === 'user' ? 'user' : 'assistant'}`}
                style={{ position: 'relative' }}
              >
                {/* Text Content */}
                <div style={{ whiteSpace: 'pre-line' }}>{m.text}</div>

                {/* Loading indicator */}
                {m.isLoading && (
                  <div style={{ display: 'flex', gap: '4px', marginTop: '6px' }}>
                    <span className="animate-pulse">●</span>
                    <span className="animate-pulse" style={{ animationDelay: '0.2s' }}>●</span>
                    <span className="animate-pulse" style={{ animationDelay: '0.4s' }}>●</span>
                  </div>
                )}

                {/* Grounding Facts List */}
                {m.facts && m.facts.length > 0 && (
                  <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid var(--line)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      ✓ Dữ liệu thực tế đối chiếu (Verified Facts):
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {m.facts.map((fact) => (
                        <div
                          key={fact.id}
                          style={{
                            fontSize: '11px',
                            background: 'var(--bg-subtle, rgba(0,0,0,0.04))',
                            border: '1px solid var(--line)',
                            borderRadius: '6px',
                            padding: '3px 8px',
                            display: 'flex',
                            gap: '4px',
                            alignItems: 'center',
                          }}
                        >
                          <span style={{ color: 'var(--muted)', fontWeight: 600 }}>[{fact.id}]</span>
                          <span style={{ color: 'var(--ink)' }}>{fact.label}: <b>{fact.value} {fact.unit || ''}</b></span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recommendations with Basis Disclosure */}
                {m.recommendations && m.recommendations.length > 0 && (
                  <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      💡 Khuyến nghị & Căn cứ:
                    </div>
                    {m.recommendations.map((rec, rIdx) => (
                      <div
                        key={rIdx}
                        style={{
                          background: 'var(--card-subtle, rgba(0,0,0,0.02))',
                          border: '1px solid var(--line)',
                          borderRadius: '8px',
                          padding: '8px 10px',
                          fontSize: '13px',
                          lineHeight: 1.4,
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                          <span
                            style={{
                              fontSize: '10px',
                              padding: '1px 6px',
                              borderRadius: '4px',
                              fontWeight: 700,
                              background: rec.basis === 'VERIFIED_FACT' ? 'rgba(40, 167, 69, 0.12)' : 'rgba(16, 149, 193, 0.12)',
                              color: rec.basis === 'VERIFIED_FACT' ? '#28a745' : 'var(--accent)',
                            }}
                          >
                            CƠ SỞ: {rec.basis}
                          </span>
                        </div>
                        <div>{rec.text}</div>
                        {rec.assumptions && rec.assumptions.length > 0 && (
                          <div style={{ marginTop: '4px', fontSize: '11px', color: 'var(--muted)' }}>
                            {rec.assumptions.map((asm, aIdx) => (
                              <div key={aIdx}>• Giả định: {asm}</div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Data Gaps Alert */}
                {m.data_gaps && m.data_gaps.length > 0 && (
                  <div
                    style={{
                      marginTop: '8px',
                      background: 'rgba(237, 137, 54, 0.08)',
                      border: '1px solid rgba(237, 137, 54, 0.3)',
                      borderRadius: '8px',
                      padding: '8px 10px',
                      fontSize: '12px',
                      color: 'var(--ink)',
                      lineHeight: 1.4,
                    }}
                  >
                    <b style={{ color: '#d97706' }}>⚠️ Cảnh báo thiếu dữ liệu / Giới hạn suy luận:</b>
                    {m.data_gaps.map((gap, gIdx) => (
                      <div key={gIdx} style={{ marginTop: '2px' }}>• {gap}</div>
                    ))}
                  </div>
                )}

                {/* Proposed Actions CTA */}
                {m.proposed_actions && m.proposed_actions.length > 0 && (
                  <div style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {m.proposed_actions.map((act, aIdx) => (
                      <button
                        key={aIdx}
                        type="button"
                        className="ui-btn secondary"
                        style={{ padding: '6px 10px', fontSize: '12px' }}
                        onClick={() => handleExecuteAction(act)}
                      >
                        ⚡ {act.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          {/* Chat Input */}
          <div style={{ display: 'flex', gap: '8px', marginTop: '14px' }}>
            <input
              type="text"
              className="ui-input"
              placeholder="Hỏi trợ lý AI về kho, bổ sung hàng, hạn dùng…"
              value={inputQuestion}
              onChange={(e) => setInputQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSendQuestion();
              }}
              aria-label="Câu hỏi gửi tới trợ lý kho"
              maxLength={120}
              disabled={isSending}
            />
            <button
              type="button"
              className="ui-btn primary"
              style={{ flex: 'none', minWidth: '52px', padding: '0 16px' }}
              onClick={() => handleSendQuestion()}
              aria-label="Gửi câu hỏi"
              disabled={isSending || !inputQuestion.trim()}
            >
              <Icon name="send" size={20} />
            </button>
          </div>

          <div className="note" style={{ marginTop: '10px', fontSize: '12px', color: 'var(--muted)', lineHeight: 1.5 }}>
            🛡️ <b>Nguyên tắc Grounding:</b> Trợ lý AI chỉ sử dụng số liệu xác thực từ sổ cái, không tự bịa đặt số lượng hay doanh thu.
          </div>
        </div>
      )}
    </div>
  );
};
