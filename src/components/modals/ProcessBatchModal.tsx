import React, { useState } from 'react';
import { ModalBackdrop } from './ModalBackdrop';
import {
  simulationStore,
  formatMoney,
  formatQty,
  capitalize,
  calculateDaysLeft,
  formatDaysLabel,
  STORAGE_LOCATIONS
} from '../../services/mock/simulationStore';
import {
  CookingPot,
  Heart,
  DollarSign,
  Trash2,
  AlertTriangle,
  Clock,
  Sparkles,
  CheckCircle2,
  Scale
} from 'lucide-react';

interface ProcessBatchModalProps {
  isOpen: boolean;
  onClose: () => void;
  batchId: string | null;
  onShowToast: (msg: string) => void;
}

export const ProcessBatchModal: React.FC<ProcessBatchModalProps> = ({
  isOpen,
  onClose,
  batchId,
  onShowToast,
}) => {
  const [activeTab, setActiveTab] = useState<'COOK' | 'SELLOFF' | 'DONATION' | 'WASTE'>('COOK');

  const batch = batchId ? simulationStore.getBatchById(batchId) : undefined;
  const remainingQtyNum = batch ? parseFloat(batch.remaining_qty) : 0;
  const daysLeft = batch ? calculateDaysLeft(batch.expiry_date) : 0;
  const isExpired = daysLeft < 0;

  // Form states
  const [cookDishId, setCookDishId] = useState<string>('');
  const [cookPortions, setCookPortions] = useState<number>(2);

  const [sellQty, setSellQty] = useState<number>(remainingQtyNum);
  const [sellRevenue, setSellRevenue] = useState<number>(() => {
    if (!batch) return 0;
    const cost = Math.round(remainingQtyNum * parseFloat(batch.unit_cost));
    return Math.round(cost * 0.6); // 60% recovery default
  });
  const [sellBuyer, setSellBuyer] = useState<string>('Quán cơm bình dân / Chế biến nước dùng');

  const [donateQty, setDonateQty] = useState<number>(remainingQtyNum);
  const [donateRecipient, setDonateRecipient] = useState<string>('Bếp ăn từ thiện');
  const [donateNote, setDonateNote] = useState<string>('');

  const [wasteQty, setWasteQty] = useState<number>(remainingQtyNum);
  const [wasteReason, setWasteReason] = useState<'EXPIRED' | 'SPOILED' | 'OVERSTOCK' | 'OTHER'>(
    isExpired ? 'EXPIRED' : 'SPOILED'
  );
  const [wasteNote, setWasteNote] = useState<string>('');

  if (!batch) return null;

  // Find candidate dishes that use this ingredient
  const ingNameLow = batch.ingredient_name.toLowerCase();
  const allDishes = simulationStore.getState().dishes;
  const candidateDishes = allDishes.filter((d) =>
    d.recipe.some((r) => (r.ingredient_name || '').toLowerCase() === ingNameLow)
  );

  const selectedDish = allDishes.find((d) => d.id === (cookDishId || candidateDishes[0]?.id));

  // Determine max portions possible using this ingredient's batch
  let portionsFromThisBatch = 0;
  if (selectedDish) {
    const item = selectedDish.recipe.find((r) => (r.ingredient_name || '').toLowerCase() === ingNameLow);
    const needPerPortion = item ? parseFloat(item.quantity) : 0;
    if (needPerPortion > 0) {
      portionsFromThisBatch = Math.floor(remainingQtyNum / needPerPortion);
    }
  }

  const handleConfirm = () => {
    try {
      if (activeTab === 'COOK') {
        const targetDishId = cookDishId || candidateDishes[0]?.id;
        if (!targetDishId) {
          onShowToast('Vui lòng chọn món ăn cần chế biến.');
          return;
        }

        const res = simulationStore.cookDish(targetDishId, cookPortions, batch.id);
        let msg = `Đã chế biến ${res.portions} phần "${res.dishName}" từ đợt ${batch.id}.`;
        if (res.hasShortage) {
          msg += ' Có nguyên liệu thiếu hụt được ghi nhận vào Option C.';
        }
        onShowToast(msg);
        onClose();
      } else if (activeTab === 'SELLOFF') {
        if (sellQty <= 0) {
          onShowToast('Số lượng bán thu mua phải lớn hơn 0.');
          return;
        }
        const res = simulationStore.processBatchDisposal(
          batch.id,
          'SELLOFF',
          sellQty,
          undefined,
          `Bán cho ${sellBuyer}`,
          sellRevenue,
          sellBuyer
        );
        onShowToast(
          `Đã bán thu mua ${formatQty(sellQty)} ${batch.unit} ${batch.ingredient_name}, thu về ${formatMoney(
            res.revenueVnd
          )}.`
        );
        onClose();
      } else if (activeTab === 'DONATION') {
        if (donateQty <= 0) {
          onShowToast('Số lượng quyên góp phải lớn hơn 0.');
          return;
        }
        simulationStore.processBatchDisposal(
          batch.id,
          'DONATION',
          donateQty,
          undefined,
          donateNote,
          undefined,
          donateRecipient
        );
        onShowToast(`Đã quyên góp ${formatQty(donateQty)} ${batch.unit} ${batch.ingredient_name} cho ${donateRecipient}.`);
        onClose();
      } else {
        // WASTE
        if (wasteQty <= 0) {
          onShowToast('Số lượng loại bỏ phải lớn hơn 0.');
          return;
        }
        if (wasteReason === 'OTHER' && !wasteNote.trim()) {
          onShowToast('Vui lòng nhập lý do giải trình khi chọn "Khác".');
          return;
        }
        const res = simulationStore.processBatchDisposal(
          batch.id,
          'WASTE',
          wasteQty,
          wasteReason,
          wasteNote
        );
        onShowToast(
          `Đã ghi nhận bỏ ${formatQty(wasteQty)} ${batch.unit} ${batch.ingredient_name} (chi phí ${formatMoney(
            res.costVnd
          )}).`
        );
        onClose();
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      onShowToast(`Lỗi: ${errMsg}`);
    }
  };

  return (
    <ModalBackdrop
      isOpen={isOpen}
      onClose={onClose}
      title="Xử lý lô hàng"
      subtitle={`Đợt nhập: ${batch.id} • ${capitalize(batch.ingredient_name)}`}
      icon={<Sparkles size={20} />}
      maxWidthClass="max-w-xl"
    >
      <div className="space-y-4">
        {/* Batch Overview Banner */}
        <div
          className={`p-3 rounded-xl border flex items-center justify-between gap-3 text-xs ${
            isExpired
              ? 'bg-[var(--bad-bg)]/40 border-[var(--bad-fg)]/40 text-[var(--bad-fg)]'
              : daysLeft <= 2
              ? 'bg-[var(--warn-bg)]/40 border-[var(--warn-fg)]/40 text-[var(--warn-fg)]'
              : 'bg-[var(--card)] border-[var(--line)] text-[var(--ink)]'
          }`}
        >
          <div>
            <span className="font-bold text-sm block text-[var(--ink)]">
              {capitalize(batch.ingredient_name)}: {formatQty(remainingQtyNum)} {batch.unit}
            </span>
            <span className="text-[11px] text-[var(--muted)]">
              Vị trí: {STORAGE_LOCATIONS[batch.location]} • Giá nhập: {formatMoney(Math.round(parseFloat(batch.unit_cost)))}
            </span>
          </div>

          <div className="text-right">
            <span
              className={`px-2 py-0.5 rounded text-[11px] font-bold block ${
                isExpired
                  ? 'bg-[var(--bad-bg)] text-[var(--bad-fg)]'
                  : daysLeft <= 2
                  ? 'bg-[var(--warn-bg)] text-[var(--warn-fg)]'
                  : 'bg-[var(--ok-bg)] text-[var(--ok-fg)]'
              }`}
            >
              {formatDaysLabel(daysLeft)}
            </span>
            <span className="text-[11px] font-mono text-[var(--muted)] mt-0.5 block">
              HSD: {batch.expiry_date}
            </span>
          </div>
        </div>

        {/* 4 Action Tabs */}
        <div className="grid grid-cols-4 gap-1.5 p-1 bg-[var(--chip)] rounded-xl text-xs">
          <button
            type="button"
            onClick={() => setActiveTab('COOK')}
            className={`py-2 px-1 rounded-lg font-bold flex flex-col items-center gap-1 transition-all ${
              activeTab === 'COOK'
                ? 'bg-[var(--card)] text-[var(--accent-text)] shadow-xs'
                : 'text-[var(--muted)] hover:text-[var(--ink)]'
            }`}
          >
            <CookingPot size={16} />
            <span>Nấu món</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveTab('SELLOFF');
              setSellQty(remainingQtyNum);
            }}
            className={`py-2 px-1 rounded-lg font-bold flex flex-col items-center gap-1 transition-all ${
              activeTab === 'SELLOFF'
                ? 'bg-[var(--card)] text-[var(--accent-text)] shadow-xs'
                : 'text-[var(--muted)] hover:text-[var(--ink)]'
            }`}
          >
            <DollarSign size={16} />
            <span>Bán thu mua</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveTab('DONATION');
              setDonateQty(remainingQtyNum);
            }}
            className={`py-2 px-1 rounded-lg font-bold flex flex-col items-center gap-1 transition-all ${
              activeTab === 'DONATION'
                ? 'bg-[var(--card)] text-[var(--accent-text)] shadow-xs'
                : 'text-[var(--muted)] hover:text-[var(--ink)]'
            }`}
          >
            <Heart size={16} />
            <span>Quyên góp</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveTab('WASTE');
              setWasteQty(remainingQtyNum);
            }}
            className={`py-2 px-1 rounded-lg font-bold flex flex-col items-center gap-1 transition-all ${
              activeTab === 'WASTE'
                ? 'bg-[var(--card)] text-[var(--bad-fg)] shadow-xs'
                : 'text-[var(--muted)] hover:text-[var(--ink)]'
            }`}
          >
            <Trash2 size={16} />
            <span>Bỏ đi</span>
          </button>
        </div>

        {/* Tab 1: COOK */}
        {activeTab === 'COOK' && (
          <div className="space-y-3 p-3.5 bg-[var(--bg)] rounded-xl border border-[var(--line)] text-xs">
            {isExpired && (
              <div className="p-2.5 rounded-lg bg-[var(--bad-bg)] text-[var(--bad-fg)] font-medium flex items-center gap-2">
                <AlertTriangle size={15} />
                Lô này đã hết hạn. Theo chính sách an toàn thực phẩm, khuyến nghị kiểm tra kỹ chất lượng trước khi nấu.
              </div>
            )}

            <div>
              <label className="font-semibold text-[var(--ink)] block mb-1">
                Chọn món ăn trong thực đơn để tận dụng nguyên liệu này:
              </label>
              {candidateDishes.length === 0 ? (
                <p className="text-[var(--muted)] italic">
                  Chưa có món nào trong thực đơn dùng nguyên liệu "{batch.ingredient_name}". Bạn có thể thêm món mới ở tab Thực đơn.
                </p>
              ) : (
                <select
                  value={cookDishId || candidateDishes[0]?.id}
                  onChange={(e) => setCookDishId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)] font-semibold"
                >
                  {candidateDishes.map((dish) => (
                    <option key={dish.id} value={dish.id}>
                      {dish.name} (Giá bán {formatMoney(dish.price_vnd)})
                    </option>
                  ))}
                </select>
              )}
            </div>

            {selectedDish && (
              <div className="grid grid-cols-2 gap-3 pt-2">
                <div>
                  <label className="font-semibold text-[var(--ink)] block mb-1">
                    Số phần muốn chế biến:
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min="1"
                      max={Math.max(1, portionsFromThisBatch * 2)}
                      value={cookPortions}
                      onChange={(e) => setCookPortions(Math.max(1, parseInt(e.target.value, 10) || 1))}
                      className="w-24 px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)] font-bold text-center"
                    />
                    <span className="text-[11px] text-[var(--muted)]">
                      Lô này đủ nấu ~{portionsFromThisBatch} phần
                    </span>
                  </div>
                </div>

                <div className="p-2.5 rounded-lg bg-[var(--card)] border border-[var(--line)] flex flex-col justify-center">
                  <span className="text-[11px] text-[var(--muted)] block">Doanh thu dự kiến:</span>
                  <span className="text-sm font-bold font-mono text-[var(--accent-text)]">
                    {formatMoney(selectedDish.price_vnd * cookPortions)}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: SELLOFF */}
        {activeTab === 'SELLOFF' && (
          <div className="space-y-3 p-3.5 bg-[var(--bg)] rounded-xl border border-[var(--line)] text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="font-semibold text-[var(--ink)] block mb-1">
                  Số lượng bán thu mua ({batch.unit}):
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  max={remainingQtyNum}
                  value={sellQty}
                  onChange={(e) => setSellQty(Math.min(remainingQtyNum, parseFloat(e.target.value) || 0))}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)] font-semibold"
                />
              </div>

              <div>
                <label className="font-semibold text-[var(--ink)] block mb-1">
                  Doanh thu thu về (đ):
                </label>
                <input
                  type="number"
                  step="5000"
                  min="0"
                  value={sellRevenue}
                  onChange={(e) => setSellRevenue(parseInt(e.target.value, 10) || 0)}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)] font-mono font-bold"
                />
              </div>
            </div>

            <div>
              <label className="font-semibold text-[var(--ink)] block mb-1">
                Bên thu mua / Mục đích thanh lý:
              </label>
              <input
                type="text"
                value={sellBuyer}
                onChange={(e) => setSellBuyer(e.target.value)}
                placeholder="vd: Quán cơm bình dân, bên thu gom phụ phẩm..."
                className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)]"
              />
            </div>
          </div>
        )}

        {/* Tab 3: DONATION */}
        {activeTab === 'DONATION' && (
          <div className="space-y-3 p-3.5 bg-[var(--bg)] rounded-xl border border-[var(--line)] text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="font-semibold text-[var(--ink)] block mb-1">
                  Số lượng quyên góp ({batch.unit}):
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  max={remainingQtyNum}
                  value={donateQty}
                  onChange={(e) => setDonateQty(Math.min(remainingQtyNum, parseFloat(e.target.value) || 0))}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)] font-semibold"
                />
              </div>

              <div>
                <label className="font-semibold text-[var(--ink)] block mb-1">
                  Đơn vị nhận / Chương trình:
                </label>
                <input
                  type="text"
                  value={donateRecipient}
                  onChange={(e) => setDonateRecipient(e.target.value)}
                  placeholder="vd: Bếp ăn 0 đồng, Chùa, Mái ấm..."
                  className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)]"
                />
              </div>
            </div>

            <div>
              <label className="font-semibold text-[var(--ink)] block mb-1">
                Ghi chú thêm:
              </label>
              <input
                type="text"
                value={donateNote}
                onChange={(e) => setDonateNote(e.target.value)}
                placeholder="Ghi chú người giao nhận..."
                className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)]"
              />
            </div>
          </div>
        )}

        {/* Tab 4: WASTE */}
        {activeTab === 'WASTE' && (
          <div className="space-y-3 p-3.5 bg-[var(--bad-bg)]/20 rounded-xl border border-[var(--bad-fg)]/30 text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="font-semibold text-[var(--ink)] block mb-1">
                  Số lượng bỏ đi ({batch.unit}):
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  max={remainingQtyNum}
                  value={wasteQty}
                  onChange={(e) => setWasteQty(Math.min(remainingQtyNum, parseFloat(e.target.value) || 0))}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)] font-semibold"
                />
              </div>

              <div>
                <label className="font-semibold text-[var(--ink)] block mb-1">
                  Lý do loại bỏ:
                </label>
                <select
                  value={wasteReason}
                  onChange={(e) => setWasteReason(e.target.value as any)}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)] font-semibold"
                >
                  <option value="EXPIRED">Hết hạn sử dụng</option>
                  <option value="SPOILED">Hỏng / Ôi thiu / Mốc</option>
                  <option value="OVERSTOCK">Nhập dư không dùng kịp</option>
                  <option value="OTHER">Lý do khác (cần ghi chú)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="font-semibold text-[var(--ink)] block mb-1">
                Ghi chú giải trình {wasteReason === 'OTHER' && <span className="text-[var(--bad-fg)]">*</span>}:
              </label>
              <input
                type="text"
                value={wasteNote}
                onChange={(e) => setWasteNote(e.target.value)}
                placeholder={wasteReason === 'OTHER' ? 'Bắt buộc nhập lý do chi tiết...' : 'Ghi chú thêm...'}
                className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)]"
              />
            </div>
          </div>
        )}

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--line)]">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl border border-[var(--line)] bg-[var(--card)] text-xs font-semibold text-[var(--ink)] hover:bg-[var(--chip)] transition-colors"
          >
            Đóng
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            className="px-5 py-2 rounded-xl bg-[var(--accent)] hover:opacity-90 text-[var(--on-accent)] text-xs font-bold transition-all shadow-md flex items-center gap-1.5"
          >
            <CheckCircle2 size={16} />
            <span>Xác nhận xử lý</span>
          </button>
        </div>
      </div>
    </ModalBackdrop>
  );
};
