import React, { useState, useEffect } from 'react';
import { ModalBackdrop } from './ModalBackdrop';
import {
  simulationStore,
  formatMoney,
  formatQty,
  capitalize,
  STORAGE_LOCATIONS
} from '../../services/mock/simulationStore';
import { MASTER_PRODUCTS } from '../../services/mock/seedData';
import { StorageLocation } from '../../types';
import {
  Boxes,
  Plus,
  SlidersHorizontal,
  Edit,
  CheckCircle2,
  Calendar,
  AlertTriangle,
  Scale
} from 'lucide-react';

interface InventoryEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialBatchId?: string | null;
  onShowToast: (msg: string) => void;
}

export const InventoryEditModal: React.FC<InventoryEditModalProps> = ({
  isOpen,
  onClose,
  initialBatchId,
  onShowToast,
}) => {
  const [tab, setTab] = useState<'RECEIPT' | 'ADJUST' | 'INFO'>(initialBatchId ? 'ADJUST' : 'RECEIPT');

  // Mode 1: Manual Receipt
  const [recName, setRecName] = useState('');
  const [recQty, setRecQty] = useState<number>(1);
  const [recUnit, setRecUnit] = useState<string>('kg');
  const [recCost, setRecCost] = useState<number>(30000);
  const [recLocation, setRecLocation] = useState<StorageLocation>('FRIDGE');
  const [recReceivedOn, setRecReceivedOn] = useState(() => new Date().toISOString().slice(0, 10));
  const [recExpiryDate, setRecExpiryDate] = useState(() =>
    new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10)
  );

  // Mode 2 & 3: Batch Selector
  const batches = simulationStore.getState().batches.filter((b) => parseFloat(b.remaining_qty) > 0.0001);
  const [selectedBatchId, setSelectedBatchId] = useState<string>(initialBatchId || batches[0]?.id || '');

  const selectedBatch = batches.find((b) => b.id === selectedBatchId);

  // Mode 2: Adjust
  const [adjustQty, setAdjustQty] = useState<number>(() =>
    selectedBatch ? parseFloat(selectedBatch.remaining_qty) : 0
  );
  const [adjustReason, setAdjustReason] = useState<string>('Kiểm kho định kỳ');
  const [adjustNote, setAdjustNote] = useState<string>('');

  // Mode 3: Info update
  const [infoLocation, setInfoLocation] = useState<StorageLocation>('FRIDGE');
  const [infoExpiry, setInfoExpiry] = useState<string>('');
  const [infoReceived, setInfoReceived] = useState<string>('');

  useEffect(() => {
    if (initialBatchId) {
      setSelectedBatchId(initialBatchId);
      setTab('ADJUST');
    }
  }, [initialBatchId]);

  useEffect(() => {
    if (selectedBatch) {
      setAdjustQty(parseFloat(selectedBatch.remaining_qty));
      setInfoLocation(selectedBatch.location);
      setInfoExpiry(selectedBatch.expiry_date || '');
      setInfoReceived(selectedBatch.received_on);
    }
  }, [selectedBatchId, selectedBatch]);

  const handleNameChange = (newName: string) => {
    setRecName(newName);
    const master = MASTER_PRODUCTS[newName.toLowerCase().trim()];
    if (master) {
      setRecUnit(master.unit);
      setRecCost(master.default_cost_vnd);
      setRecLocation(master.location);
      setRecExpiryDate(new Date(Date.now() + master.shelf_life_days * 86400000).toISOString().slice(0, 10));
    }
  };

  const handleConfirm = () => {
    try {
      if (tab === 'RECEIPT') {
        if (!recName.trim()) {
          onShowToast('Vui lòng nhập tên nguyên liệu.');
          return;
        }
        if (recQty <= 0) {
          onShowToast('Số lượng nhập phải lớn hơn 0.');
          return;
        }

        const b = simulationStore.addBatchManual({
          name: recName,
          qty: recQty,
          unit: recUnit,
          cost: recCost,
          location: recLocation,
          received_on: recReceivedOn,
          expiry_date: recExpiryDate,
        });

        onShowToast(`Đã thêm đợt nhập mới (${b.id}) cho ${capitalize(b.ingredient_name)}: ${formatQty(recQty)} ${b.unit}.`);
        onClose();
      } else if (tab === 'ADJUST') {
        if (!selectedBatch) {
          onShowToast('Vui lòng chọn đợt hàng cần kiểm kê.');
          return;
        }
        if (adjustQty < 0) {
          onShowToast('Số lượng kiểm kê không được âm.');
          return;
        }

        const res = simulationStore.adjustBatch(selectedBatch.id, adjustQty, adjustReason, adjustNote);
        const sign = res.delta >= 0 ? '+' : '';
        onShowToast(
          `Đã cân chỉnh đợt ${selectedBatch.id}: tồn mới ${formatQty(adjustQty)} ${selectedBatch.unit} (${sign}${formatQty(
            res.delta
          )} ${selectedBatch.unit}, ${formatMoney(res.deltaVal)}).`
        );
        onClose();
      } else {
        // INFO
        if (!selectedBatch) {
          onShowToast('Vui lòng chọn đợt hàng.');
          return;
        }

        simulationStore.updateBatchMetadata(selectedBatch.id, {
          location: infoLocation,
          expiry_date: infoExpiry,
          received_on: infoReceived,
        });

        onShowToast(`Đã cập nhật thông tin đợt ${selectedBatch.id}.`);
        onClose();
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      onShowToast(`Lỗi: ${errMsg}`);
    }
  };

  const currentBatchQty = selectedBatch ? parseFloat(selectedBatch.remaining_qty) : 0;
  const currentBatchCost = selectedBatch ? parseFloat(selectedBatch.unit_cost) : 0;
  const deltaQty = adjustQty - currentBatchQty;
  const deltaVal = Math.round(deltaQty * currentBatchCost);

  return (
    <ModalBackdrop
      isOpen={isOpen}
      onClose={onClose}
      title="Quản lý & Chỉnh sửa kho"
      subtitle="Thêm đợt nhập mới, cân chỉnh số lượng kiểm kê hoặc sửa thông tin vị trí / hạn dùng"
      icon={<Boxes size={20} />}
      maxWidthClass="max-w-xl"
    >
      <div className="space-y-4">
        {/* Tab Selection */}
        <div className="flex gap-1.5 p-1 bg-[var(--chip)] rounded-xl text-xs">
          <button
            type="button"
            onClick={() => setTab('RECEIPT')}
            className={`flex-1 py-2 px-2 rounded-lg font-bold flex items-center justify-center gap-1.5 transition-all ${
              tab === 'RECEIPT'
                ? 'bg-[var(--card)] text-[var(--accent-text)] shadow-xs'
                : 'text-[var(--muted)] hover:text-[var(--ink)]'
            }`}
          >
            <Plus size={15} />
            <span>Thêm đợt nhập</span>
          </button>

          <button
            type="button"
            onClick={() => setTab('ADJUST')}
            className={`flex-1 py-2 px-2 rounded-lg font-bold flex items-center justify-center gap-1.5 transition-all ${
              tab === 'ADJUST'
                ? 'bg-[var(--card)] text-[var(--accent-text)] shadow-xs'
                : 'text-[var(--muted)] hover:text-[var(--ink)]'
            }`}
          >
            <Scale size={15} />
            <span>Cân chỉnh kiểm kê</span>
          </button>

          <button
            type="button"
            onClick={() => setTab('INFO')}
            className={`flex-1 py-2 px-2 rounded-lg font-bold flex items-center justify-center gap-1.5 transition-all ${
              tab === 'INFO'
                ? 'bg-[var(--card)] text-[var(--accent-text)] shadow-xs'
                : 'text-[var(--muted)] hover:text-[var(--ink)]'
            }`}
          >
            <Edit size={15} />
            <span>Sửa thông tin lô</span>
          </button>
        </div>

        {/* Tab 1: RECEIPT */}
        {tab === 'RECEIPT' && (
          <div className="space-y-3 p-3.5 bg-[var(--bg)] rounded-xl border border-[var(--line)] text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="font-bold text-[var(--ink)] block mb-1">Tên nguyên liệu:</label>
                <input
                  type="text"
                  value={recName}
                  onChange={(e) => handleNameChange(e.target.value)}
                  placeholder="vd: Cà chua, thịt bò..."
                  className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)] font-semibold"
                />
              </div>

              <div>
                <label className="font-bold text-[var(--ink)] block mb-1">Vị trí bảo quản:</label>
                <select
                  value={recLocation}
                  onChange={(e) => setRecLocation(e.target.value as StorageLocation)}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)] font-semibold"
                >
                  <option value="FRIDGE">Tủ lạnh</option>
                  <option value="FREEZER">Ngăn đông</option>
                  <option value="PANTRY">Tủ bếp</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="font-bold text-[var(--ink)] block mb-1">Số lượng:</label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  value={recQty}
                  onChange={(e) => setRecQty(parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)] font-bold"
                />
              </div>

              <div>
                <label className="font-bold text-[var(--ink)] block mb-1">Đơn vị:</label>
                <input
                  type="text"
                  value={recUnit}
                  onChange={(e) => setRecUnit(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)]"
                />
              </div>

              <div>
                <label className="font-bold text-[var(--ink)] block mb-1">Đơn giá nhập (đ):</label>
                <input
                  type="number"
                  step="1000"
                  min="0"
                  value={recCost}
                  onChange={(e) => setRecCost(parseInt(e.target.value, 10) || 0)}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)] font-mono font-bold"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="font-bold text-[var(--ink)] block mb-1">Ngày nhận hàng:</label>
                <input
                  type="date"
                  value={recReceivedOn}
                  onChange={(e) => setRecReceivedOn(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)] font-medium"
                />
              </div>

              <div>
                <label className="font-bold text-[var(--ink)] block mb-1">Hạn sử dụng:</label>
                <input
                  type="date"
                  value={recExpiryDate}
                  onChange={(e) => setRecExpiryDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)] font-medium"
                />
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-[var(--card)] border border-[var(--line)] flex items-center justify-between text-xs">
              <span className="text-[var(--muted)]">Tổng giá trị lô hàng:</span>
              <span className="font-mono font-bold text-sm text-[var(--accent-text)]">
                {formatMoney(Math.round(recQty * recCost))}
              </span>
            </div>
          </div>
        )}

        {/* Tab 2: ADJUST */}
        {tab === 'ADJUST' && (
          <div className="space-y-3 p-3.5 bg-[var(--bg)] rounded-xl border border-[var(--line)] text-xs">
            <div>
              <label className="font-bold text-[var(--ink)] block mb-1">Chọn đợt hàng kiểm kê:</label>
              <select
                value={selectedBatchId}
                onChange={(e) => setSelectedBatchId(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)] font-semibold"
              >
                {batches.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.id} • {capitalize(b.ingredient_name)}: {formatQty(parseFloat(b.remaining_qty))} {b.unit} (HSD: {b.expiry_date})
                  </option>
                ))}
              </select>
            </div>

            {selectedBatch && (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-2.5 rounded-lg bg-[var(--card)] border border-[var(--line)]">
                    <span className="text-[11px] text-[var(--muted)] block">Tồn hiện tại trên sổ:</span>
                    <span className="text-base font-bold font-mono text-[var(--ink)]">
                      {formatQty(currentBatchQty)} {selectedBatch.unit}
                    </span>
                  </div>

                  <div>
                    <label className="font-bold text-[var(--ink)] block mb-1">
                      Số lượng thực tế đếm được ({selectedBatch.unit}):
                    </label>
                    <input
                      type="number"
                      step="0.05"
                      min="0"
                      value={adjustQty}
                      onChange={(e) => setAdjustQty(parseFloat(e.target.value) || 0)}
                      className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-base font-bold text-[var(--ink)]"
                    />
                  </div>
                </div>

                {/* Delta review */}
                <div
                  className={`p-2.5 rounded-lg border flex items-center justify-between text-xs font-semibold ${
                    deltaQty === 0
                      ? 'bg-[var(--chip)] border-[var(--line)] text-[var(--muted)]'
                      : deltaQty > 0
                      ? 'bg-[var(--ok-bg)]/40 border-[var(--ok-fg)]/40 text-[var(--ok-fg)]'
                      : 'bg-[var(--bad-bg)]/40 border-[var(--bad-fg)]/40 text-[var(--bad-fg)]'
                  }`}
                >
                  <span>Chênh lệch kiểm kê:</span>
                  <span className="font-mono text-sm">
                    {deltaQty > 0 ? `+${formatQty(deltaQty)}` : formatQty(deltaQty)} {selectedBatch.unit} (
                    {deltaVal >= 0 ? `+${formatMoney(deltaVal)}` : `-${formatMoney(Math.abs(deltaVal))}`})
                  </span>
                </div>

                <div>
                  <label className="font-bold text-[var(--ink)] block mb-1">Lý do điều chỉnh:</label>
                  <select
                    value={adjustReason}
                    onChange={(e) => setAdjustReason(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)] font-semibold"
                  >
                    <option value="Kiểm kho định kỳ">Kiểm kho định kỳ</option>
                    <option value="Hao hụt tự nhiên / Bay hơi">Hao hụt tự nhiên / Bay hơi</option>
                    <option value="Sai sót nhập liệu trước đó">Sai sót nhập liệu trước đó</option>
                    <option value="Tìm thấy thêm hàng">Tìm thấy thêm hàng</option>
                    <option value="Khác">Lý do khác</option>
                  </select>
                </div>

                <div>
                  <label className="font-bold text-[var(--ink)] block mb-1">Ghi chú:</label>
                  <input
                    type="text"
                    value={adjustNote}
                    onChange={(e) => setAdjustNote(e.target.value)}
                    placeholder="Ghi chú người kiểm kê..."
                    className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)]"
                  />
                </div>
              </>
            )}
          </div>
        )}

        {/* Tab 3: INFO */}
        {tab === 'INFO' && (
          <div className="space-y-3 p-3.5 bg-[var(--bg)] rounded-xl border border-[var(--line)] text-xs">
            <div>
              <label className="font-bold text-[var(--ink)] block mb-1">Chọn đợt hàng:</label>
              <select
                value={selectedBatchId}
                onChange={(e) => setSelectedBatchId(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)] font-semibold"
              >
                {batches.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.id} • {capitalize(b.ingredient_name)} ({STORAGE_LOCATIONS[b.location]})
                  </option>
                ))}
              </select>
            </div>

            {selectedBatch && (
              <>
                <div>
                  <label className="font-bold text-[var(--ink)] block mb-1">Vị trí cất trữ mới:</label>
                  <select
                    value={infoLocation}
                    onChange={(e) => setInfoLocation(e.target.value as StorageLocation)}
                    className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)] font-semibold"
                  >
                    <option value="FRIDGE">Tủ lạnh</option>
                    <option value="FREEZER">Ngăn đông</option>
                    <option value="PANTRY">Tủ bếp</option>
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="font-bold text-[var(--ink)] block mb-1">Ngày nhận hàng:</label>
                    <input
                      type="date"
                      value={infoReceived}
                      onChange={(e) => setInfoReceived(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)]"
                    />
                  </div>

                  <div>
                    <label className="font-bold text-[var(--ink)] block mb-1">Hạn sử dụng mới:</label>
                    <input
                      type="date"
                      value={infoExpiry}
                      onChange={(e) => setInfoExpiry(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-[var(--ink)]"
                    />
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--line)]">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl border border-[var(--line)] bg-[var(--card)] text-xs font-semibold text-[var(--ink)] hover:bg-[var(--chip)] transition-colors"
          >
            Hủy
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            className="px-5 py-2 rounded-xl bg-[var(--accent)] hover:opacity-90 text-[var(--on-accent)] text-xs font-bold transition-all shadow-md flex items-center gap-1.5"
          >
            <CheckCircle2 size={16} />
            <span>Xác nhận lưu thay đổi</span>
          </button>
        </div>
      </div>
    </ModalBackdrop>
  );
};
