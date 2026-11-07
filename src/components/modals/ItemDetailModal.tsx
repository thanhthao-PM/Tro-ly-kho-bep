import React from 'react';
import { ModalBackdrop } from './ModalBackdrop';
import {
  simulationStore,
  formatMoney,
  formatQty,
  capitalize,
  STORAGE_LOCATIONS
} from '../../services/mock/simulationStore';
import {
  Package,
  Calendar,
  Clock,
  Sparkles,
  ArrowRight,
  TrendingDown,
  TrendingUp,
  History,
  AlertTriangle,
  CheckCircle2,
  Edit3
} from 'lucide-react';

interface ItemDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  productName: string | null;
  onOpenProcessBatch: (batchId: string) => void;
  onOpenEditBatch: (batchId: string) => void;
}

export const ItemDetailModal: React.FC<ItemDetailModalProps> = ({
  isOpen,
  onClose,
  productName,
  onOpenProcessBatch,
  onOpenEditBatch,
}) => {
  if (!productName) return null;

  const products = simulationStore.getKhoProducts('', 'all', 'exp', 'all');
  const group = products.find((p) => p.name.toLowerCase() === productName.toLowerCase());
  const movements = simulationStore.getProductMovements(productName);

  if (!group) return null;

  return (
    <ModalBackdrop
      isOpen={isOpen}
      onClose={onClose}
      title={capitalize(group.name)}
      subtitle={`Vị trí: ${STORAGE_LOCATIONS[group.location]} • Đơn vị chuẩn: ${group.unit}`}
      icon={<Package size={20} />}
      maxWidthClass="max-w-2xl"
    >
      <div className="space-y-5">
        {/* Top Summary Banner */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 p-3.5 bg-[var(--bg)] rounded-xl border border-[var(--line)]">
          <div>
            <span className="text-[11px] text-[var(--muted)] block">Tổng tồn kho:</span>
            <span className="text-base font-bold text-[var(--ink)]">
              {formatQty(group.totalQty)} {group.unit}
            </span>
          </div>

          <div>
            <span className="text-[11px] text-[var(--muted)] block">Tổng giá trị:</span>
            <span className="text-base font-bold font-mono text-[var(--accent-text)]">
              {formatMoney(group.stockValue)}
            </span>
          </div>

          <div>
            <span className="text-[11px] text-[var(--muted)] block">Hạn dùng sớm nhất:</span>
            <span
              className={`text-xs font-bold px-2 py-0.5 rounded-md inline-block mt-0.5 ${
                group.tone === 'bad'
                  ? 'bg-[var(--bad-bg)] text-[var(--bad-fg)]'
                  : group.tone === 'warn'
                  ? 'bg-[var(--warn-bg)] text-[var(--warn-fg)]'
                  : 'bg-[var(--ok-bg)] text-[var(--ok-fg)]'
              }`}
            >
              {group.statusLabel}
            </span>
          </div>

          <div>
            <span className="text-[11px] text-[var(--muted)] block">Số đợt nhập:</span>
            <span className="text-base font-bold text-[var(--ink)]">
              {group.batches.length} đợt
            </span>
          </div>
        </div>

        {/* Batches Table (FEFO) */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--muted)] flex items-center gap-1.5">
              <Clock size={14} className="text-[var(--accent-text)]" />
              Các đợt nhập theo thứ tự FEFO (Ưu tiên xuất trước)
            </h3>
            <span className="text-[11px] text-[var(--muted)]">Sắp xếp theo hạn dùng tăng dần</span>
          </div>

          <div className="border border-[var(--line)] rounded-xl overflow-x-auto bg-[var(--card)]">
            <table className="w-full text-xs text-left">
              <thead className="bg-[var(--bg)] text-[var(--muted)] border-b border-[var(--line)] font-semibold">
                <tr>
                  <th className="p-2.5">Mã đợt</th>
                  <th className="p-2.5">Ngày nhập</th>
                  <th className="p-2.5">Hạn sử dụng</th>
                  <th className="p-2.5">Tồn / Ban đầu</th>
                  <th className="p-2.5">Đơn giá nhập</th>
                  <th className="p-2.5 text-right">Giá trị tồn</th>
                  <th className="p-2.5 text-center">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--line)]">
                {group.batches.map((batch) => {
                  const daysLeft = batch.days_to_expiry ?? 0;
                  const isExp = daysLeft < 0;
                  const isSoon = daysLeft >= 0 && daysLeft <= 2;

                  return (
                    <tr key={batch.id} className="hover:bg-[var(--bg)]/40 transition-colors">
                      <td className="p-2.5 font-mono text-[11px] font-semibold text-[var(--muted)]">
                        {batch.id}
                      </td>
                      <td className="p-2.5 text-[var(--ink)] whitespace-nowrap">
                        {batch.received_on}
                      </td>
                      <td className="p-2.5 whitespace-nowrap">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[11px] font-bold ${
                            isExp
                              ? 'bg-[var(--bad-bg)] text-[var(--bad-fg)]'
                              : isSoon
                              ? 'bg-[var(--warn-bg)] text-[var(--warn-fg)]'
                              : 'bg-[var(--chip)] text-[var(--ink)]'
                          }`}
                        >
                          {batch.expiry_date} ({daysLeft < 0 ? `quá ${Math.abs(daysLeft)}d` : `${daysLeft}d`})
                        </span>
                      </td>
                      <td className="p-2.5 font-semibold text-[var(--ink)] whitespace-nowrap">
                        {formatQty(parseFloat(batch.remaining_qty))} / {formatQty(parseFloat(batch.initial_qty))} {batch.unit}
                      </td>
                      <td className="p-2.5 font-mono text-[var(--muted)] whitespace-nowrap">
                        {formatMoney(Math.round(parseFloat(batch.unit_cost)))}
                      </td>
                      <td className="p-2.5 text-right font-mono font-bold text-[var(--ink)] whitespace-nowrap">
                        {formatMoney(batch.stock_value_vnd)}
                      </td>
                      <td className="p-2.5 text-center whitespace-nowrap">
                        <div className="flex items-center justify-center gap-1">
                          <button
                            type="button"
                            onClick={() => {
                              onClose();
                              onOpenProcessBatch(batch.id);
                            }}
                            className="px-2 py-1 rounded-md bg-[var(--accent)] hover:opacity-90 text-[var(--on-accent)] font-semibold text-[11px] transition-colors"
                            title="Xử lý lô hàng này"
                          >
                            Xử lý
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              onClose();
                              onOpenEditBatch(batch.id);
                            }}
                            className="p-1 rounded-md bg-[var(--chip)] hover:bg-[var(--line)] text-[var(--ink)] transition-colors"
                            title="Sửa thông tin hoặc cân chỉnh kiểm kê"
                          >
                            <Edit3 size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Ledger Movements */}
        <div className="space-y-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--muted)] flex items-center gap-1.5">
            <History size={14} className="text-[var(--accent-text)]" />
            Lịch sử biến động sổ cái gần nhất
          </h3>

          <div className="border border-[var(--line)] rounded-xl overflow-hidden bg-[var(--card)] max-h-48 overflow-y-auto">
            {movements.length === 0 ? (
              <div className="p-4 text-center text-xs text-[var(--muted)]">
                Chưa có biến động nào được ghi nhận cho mặt hàng này.
              </div>
            ) : (
              <div className="divide-y divide-[var(--line)] text-xs">
                {movements.slice(0, 8).map((m) => {
                  const qtyDelta = parseFloat(m.qty_delta);
                  const isPositive = qtyDelta > 0;

                  return (
                    <div key={m.id} className="p-2.5 flex items-center justify-between gap-3 hover:bg-[var(--bg)]/40">
                      <div className="flex items-center gap-2">
                        <span
                          className={`w-6 h-6 rounded-md flex items-center justify-center text-[11px] font-bold shrink-0 ${
                            isPositive
                              ? 'bg-[var(--ok-bg)] text-[var(--ok-fg)]'
                              : 'bg-[var(--bad-bg)] text-[var(--bad-fg)]'
                          }`}
                        >
                          {isPositive ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                        </span>
                        <div>
                          <span className="font-semibold text-[var(--ink)] block">
                            {m.type === 'RECEIPT'
                              ? 'Nhập kho'
                              : m.type === 'SALE_CONSUMPTION'
                              ? 'Xuất bán món'
                              : m.type === 'USAGE_CONSUMPTION'
                              ? 'Sử dụng nấu món'
                              : m.type === 'DONATION'
                              ? 'Quyên góp từ thiện'
                              : m.type === 'SELLOFF'
                              ? 'Bán thu mua'
                              : m.type === 'WASTE'
                              ? 'Hao hụt / Bỏ đi'
                              : 'Điều chỉnh kiểm kho'}
                          </span>
                          <span className="text-[11px] text-[var(--muted)]">
                            {m.occurred_on} • Đợt: {m.batch_id}
                          </span>
                        </div>
                      </div>

                      <div className="text-right">
                        <span
                          className={`font-mono font-bold block ${
                            isPositive ? 'text-[var(--ok-fg)]' : 'text-[var(--bad-fg)]'
                          }`}
                        >
                          {isPositive ? '+' : ''}
                          {formatQty(qtyDelta)} {m.unit}
                        </span>
                        <span className="text-[11px] font-mono text-[var(--muted)]">
                          {formatMoney(Math.abs(m.value_vnd))}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </ModalBackdrop>
  );
};
