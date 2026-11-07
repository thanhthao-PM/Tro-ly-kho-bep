import React, { useState, useEffect } from 'react';
import { ModalBackdrop } from './ModalBackdrop';
import {
  simulationStore,
  formatMoney,
  formatQty,
  capitalize
} from '../../services/mock/simulationStore';
import { MASTER_PRODUCTS } from '../../services/mock/seedData';
import {
  UtensilsCrossed,
  Plus,
  Trash2,
  AlertCircle,
  CheckCircle2,
  DollarSign,
  PieChart,
  CookingPot
} from 'lucide-react';

interface RecipeModalProps {
  isOpen: boolean;
  onClose: () => void;
  dishId: string | null;
  onShowToast: (msg: string) => void;
}

interface RecipeRow {
  id: string;
  name: string;
  qty: string;
  unit: string;
}

export const RecipeModal: React.FC<RecipeModalProps> = ({
  isOpen,
  onClose,
  dishId,
  onShowToast,
}) => {
  const existingDish = dishId ? simulationStore.getDishById(dishId) : undefined;
  const isEditing = !!existingDish;

  const [name, setName] = useState('');
  const [priceVnd, setPriceVnd] = useState<number>(35000);
  const [recipeRows, setRecipeRows] = useState<RecipeRow[]>([
    { id: '1', name: 'trứng gà', qty: '2', unit: 'quả' },
    { id: '2', name: 'cà chua', qty: '0.1', unit: 'kg' },
    { id: '3', name: 'hành lá', qty: '0.05', unit: 'kg' },
  ]);

  useEffect(() => {
    if (existingDish) {
      setName(existingDish.name);
      setPriceVnd(existingDish.price_vnd);
      setRecipeRows(
        existingDish.recipe.map((r, i) => ({
          id: String(i + 1),
          name: r.ingredient_name || '',
          qty: r.quantity,
          unit: r.unit || 'kg',
        }))
      );
    } else {
      setName('');
      setPriceVnd(35000);
      setRecipeRows([
        { id: '1', name: 'trứng gà', qty: '2', unit: 'quả' },
        { id: '2', name: 'cà chua', qty: '0.1', unit: 'kg' },
      ]);
    }
  }, [existingDish, isOpen]);

  // Live Calculations
  let estimatedCost = 0;
  let maxPortions = 999999;
  const missingIngredients: string[] = [];

  recipeRows.forEach((r) => {
    const ingName = r.name.trim().toLowerCase();
    const needed = parseFloat(r.qty) || 0;
    if (needed > 0 && ingName) {
      const avgCost = simulationStore.getAvgUnitCost(ingName);
      estimatedCost += needed * avgCost;

      const avail = simulationStore.getAvailableQty(ingName);
      const possible = Math.floor(avail / needed);
      maxPortions = Math.min(maxPortions, possible);
      if (avail < needed) {
        missingIngredients.push(r.name);
      }
    }
  });

  if (maxPortions === 999999 || recipeRows.length === 0) maxPortions = 0;
  const roundedCost = Math.round(estimatedCost);
  const grossMargin = priceVnd - roundedCost;
  const marginPercent = priceVnd > 0 ? Math.round((grossMargin / priceVnd) * 100) : 0;

  const handleAddRow = () => {
    setRecipeRows((prev) => [
      ...prev,
      {
        id: String(Date.now()),
        name: '',
        qty: '0.1',
        unit: 'kg',
      },
    ]);
  };

  const handleRemoveRow = (id: string) => {
    if (recipeRows.length <= 1) {
      onShowToast('Công thức cần ít nhất một nguyên liệu.');
      return;
    }
    setRecipeRows((prev) => prev.filter((r) => r.id !== id));
  };

  const handleIngredientChange = (id: string, newName: string) => {
    const master = MASTER_PRODUCTS[newName.toLowerCase().trim()];
    const defaultUnit = master?.unit || 'kg';
    setRecipeRows((prev) =>
      prev.map((r) => (r.id === id ? { ...r, name: newName, unit: defaultUnit } : r))
    );
  };

  const handleSave = () => {
    if (!name.trim()) {
      onShowToast('Vui lòng nhập tên món ăn.');
      return;
    }
    if (priceVnd < 0) {
      onShowToast('Giá bán không được âm.');
      return;
    }
    const validRows = recipeRows.filter((r) => r.name.trim() && parseFloat(r.qty) > 0);
    if (validRows.length === 0) {
      onShowToast('Vui lòng nhập ít nhất một nguyên liệu hợp lệ.');
      return;
    }

    try {
      simulationStore.saveDish({
        id: existingDish?.id,
        name,
        price_vnd: priceVnd,
        recipe: validRows.map((r) => ({
          ingredient_name: r.name,
          quantity: r.qty,
          unit: r.unit,
        })),
      });

      onShowToast(`Đã ${isEditing ? 'cập nhật' : 'thêm'} món "${name}" vào thực đơn thành công.`);
      onClose();
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      onShowToast(`Lỗi: ${errMsg}`);
    }
  };

  const handleDelete = () => {
    if (!existingDish) return;
    simulationStore.deleteDish(existingDish.id);
    onShowToast(`Đã xóa món "${existingDish.name}" khỏi thực đơn.`);
    onClose();
  };

  return (
    <ModalBackdrop
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? `Định lượng: ${existingDish.name}` : 'Thêm món mới vào thực đơn'}
      subtitle="Thiết lập công thức nguyên liệu chuẩn cho 1 phần ăn và tính toán biên lợi nhuận"
      icon={<UtensilsCrossed size={20} />}
      maxWidthClass="max-w-2xl"
    >
      <div className="space-y-4">
        {/* Name and Price Fields */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3.5 bg-[var(--bg)] rounded-xl border border-[var(--line)]">
          <div>
            <label className="text-xs font-bold text-[var(--ink)] block mb-1">
              Tên món ăn <span className="text-[var(--accent-text)]">*</span>:
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="vd: Canh chua cá lóc"
              className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-sm font-semibold text-[var(--ink)]"
            />
          </div>

          <div>
            <label className="text-xs font-bold text-[var(--ink)] block mb-1">
              Giá bán thực đơn (đ/phần) <span className="text-[var(--accent-text)]">*</span>:
            </label>
            <input
              type="number"
              step="1000"
              min="0"
              value={priceVnd}
              onChange={(e) => setPriceVnd(parseInt(e.target.value, 10) || 0)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--line)] bg-[var(--card)] text-sm font-bold font-mono text-[var(--accent-text)]"
            />
          </div>
        </div>

        {/* Live Calculation Cards */}
        <div className="grid grid-cols-3 gap-2.5 p-3 bg-[var(--card)] rounded-xl border border-[var(--line)] text-center text-xs">
          <div>
            <span className="text-[11px] text-[var(--muted)] block">Giá vốn ước tính:</span>
            <span className="text-sm font-bold font-mono text-[var(--ink)]">
              {formatMoney(roundedCost)}
            </span>
          </div>

          <div>
            <span className="text-[11px] text-[var(--muted)] block">Lãi gộp & biên lãi:</span>
            <span
              className={`text-sm font-bold font-mono ${
                grossMargin >= 0 ? 'text-[var(--ok-fg)]' : 'text-[var(--bad-fg)]'
              }`}
            >
              {formatMoney(grossMargin)} ({marginPercent}%)
            </span>
          </div>

          <div>
            <span className="text-[11px] text-[var(--muted)] block">Nấu được ngay:</span>
            <span
              className={`text-sm font-bold ${
                maxPortions > 0 ? 'text-[var(--accent-text)]' : 'text-[var(--bad-fg)]'
              }`}
            >
              {maxPortions > 0 ? `${maxPortions} phần` : 'Hết hàng'}
            </span>
          </div>
        </div>

        {missingIngredients.length > 0 && (
          <div className="p-2.5 rounded-lg bg-[var(--warn-bg)]/60 text-[var(--warn-fg)] text-xs flex items-center gap-2">
            <AlertCircle size={15} className="shrink-0" />
            <span>
              Kho hiện đang thiếu: <strong>{missingIngredients.join(', ')}</strong> để nấu đủ 1 phần món này.
            </span>
          </div>
        )}

        {/* Dynamic Recipe Items Table */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--muted)]">
              Định lượng nguyên liệu cho 1 phần ăn
            </h3>
            <button
              type="button"
              onClick={handleAddRow}
              className="text-xs font-semibold text-[var(--accent-text)] hover:underline flex items-center gap-1"
            >
              <Plus size={14} /> Thêm nguyên liệu
            </button>
          </div>

          <div className="border border-[var(--line)] rounded-xl overflow-hidden bg-[var(--card)]">
            <table className="w-full text-xs text-left">
              <thead className="bg-[var(--bg)] text-[var(--muted)] border-b border-[var(--line)] font-semibold">
                <tr>
                  <th className="p-2.5 min-w-[160px]">Nguyên liệu</th>
                  <th className="p-2.5 w-28">Định lượng</th>
                  <th className="p-2.5 w-24">Đơn vị</th>
                  <th className="p-2.5 w-32 text-right">Chi phí ước tính</th>
                  <th className="p-2.5 w-8"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--line)]">
                {recipeRows.map((row) => {
                  const ingName = row.name.toLowerCase().trim();
                  const needed = parseFloat(row.qty) || 0;
                  const avgCost = simulationStore.getAvgUnitCost(ingName);
                  const lineCost = Math.round(needed * avgCost);

                  return (
                    <tr key={row.id} className="hover:bg-[var(--bg)]/40 transition-colors">
                      <td className="p-2">
                        <input
                          type="text"
                          value={row.name}
                          onChange={(e) => handleIngredientChange(row.id, e.target.value)}
                          placeholder="vd: Thịt ba rọi"
                          className="w-full px-2.5 py-1.5 rounded border border-[var(--line)] bg-[var(--bg)] text-[var(--ink)] font-medium"
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="number"
                          step="0.05"
                          min="0.01"
                          value={row.qty}
                          onChange={(e) => {
                            const val = e.target.value;
                            setRecipeRows((prev) =>
                              prev.map((r) => (r.id === row.id ? { ...r, qty: val } : r))
                            );
                          }}
                          className="w-full px-2.5 py-1.5 rounded border border-[var(--line)] bg-[var(--bg)] text-[var(--ink)] font-semibold"
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="text"
                          value={row.unit}
                          onChange={(e) => {
                            const val = e.target.value;
                            setRecipeRows((prev) =>
                              prev.map((r) => (r.id === row.id ? { ...r, unit: val } : r))
                            );
                          }}
                          className="w-full px-2.5 py-1.5 rounded border border-[var(--line)] bg-[var(--bg)] text-[var(--ink)]"
                        />
                      </td>
                      <td className="p-2 text-right font-mono text-[var(--ink)] whitespace-nowrap">
                        {formatMoney(lineCost)}
                      </td>
                      <td className="p-2 text-center">
                        <button
                          type="button"
                          onClick={() => handleRemoveRow(row.id)}
                          className="p-1 text-[var(--muted)] hover:text-[var(--bad-fg)] transition-colors"
                          title="Xóa nguyên liệu"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between pt-2 border-t border-[var(--line)]">
          {isEditing ? (
            <button
              type="button"
              onClick={handleDelete}
              className="px-3.5 py-2 rounded-xl border border-[var(--bad-fg)]/30 text-[var(--bad-fg)] hover:bg-[var(--bad-bg)] text-xs font-semibold transition-colors flex items-center gap-1"
            >
              <Trash2 size={14} /> Xóa món này
            </button>
          ) : (
            <div></div>
          )}

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-[var(--line)] bg-[var(--card)] text-xs font-semibold text-[var(--ink)] hover:bg-[var(--chip)] transition-colors"
            >
              Hủy
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="px-5 py-2 rounded-xl bg-[var(--accent)] hover:opacity-90 text-[var(--on-accent)] text-xs font-bold transition-all shadow-md flex items-center gap-1.5"
            >
              <CheckCircle2 size={16} />
              <span>{isEditing ? 'Lưu thay đổi' : 'Thêm vào thực đơn'}</span>
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  );
};
