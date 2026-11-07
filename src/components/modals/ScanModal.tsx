import React, { useState } from 'react';
import { ModalBackdrop } from './ModalBackdrop';
import { simulationStore, formatMoney, formatQty } from '../../services/mock/simulationStore';
import { StorageLocation } from '../../types';
import {
  FileText,
  Upload,
  Plus,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Receipt,
  ShoppingBag,
  Sparkles
} from 'lucide-react';

interface ScanModalProps {
  isOpen: boolean;
  onClose: () => void;
  onShowToast: (msg: string) => void;
}

interface ScanInvoiceLine {
  id: string;
  isSelected: boolean;
  name: string;
  qty: number;
  unit: string;
  cost: number;
  location: StorageLocation;
  expiryDate: string;
}

interface ScanSalesLine {
  id: string;
  isSelected: boolean;
  dishName: string;
  qty: number;
  unitPrice: number;
}

export const ScanModal: React.FC<ScanModalProps> = ({ isOpen, onClose, onShowToast }) => {
  const [docKind, setDocKind] = useState<'IMPORT' | 'SALES'>('IMPORT');
  const [docDate, setDocDate] = useState(() => new Date().toISOString().slice(0, 10));

  // Invoice lines state
  const [invoiceLines, setInvoiceLines] = useState<ScanInvoiceLine[]>([
    {
      id: 'inv-1',
      isSelected: true,
      name: 'cà chua',
      qty: 2.0,
      unit: 'kg',
      cost: 35000,
      location: 'FRIDGE',
      expiryDate: new Date(Date.now() + 5 * 86400000).toISOString().slice(0, 10),
    },
    {
      id: 'inv-2',
      isSelected: true,
      name: 'trứng gà',
      qty: 15,
      unit: 'quả',
      cost: 3500,
      location: 'FRIDGE',
      expiryDate: new Date(Date.now() + 10 * 86400000).toISOString().slice(0, 10),
    },
    {
      id: 'inv-3',
      isSelected: true,
      name: 'thịt ba rọi',
      qty: 2.5,
      unit: 'kg',
      cost: 150000,
      location: 'FREEZER',
      expiryDate: new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10),
    },
  ]);

  // Sales report lines state
  const [salesLines, setSalesLines] = useState<ScanSalesLine[]>([
    {
      id: 'sale-1',
      isSelected: true,
      dishName: 'Trứng chiên cà chua',
      qty: 4,
      unitPrice: 35000,
    },
    {
      id: 'sale-2',
      isSelected: true,
      dishName: 'Cơm chiên trứng',
      qty: 5,
      unitPrice: 40000,
    },
    {
      id: 'sale-3',
      isSelected: true,
      dishName: 'Gà xào nấm',
      qty: 3,
      unitPrice: 60000,
    },
  ]);

  const [isSubmitting, setIsSubmitting] = useState(false);

  // Quick Samples
  const handleLoadSample = (sampleType: 'VEGGIE' | 'MEAT' | 'LUNCH') => {
    if (sampleType === 'VEGGIE') {
      setDocKind('IMPORT');
      setInvoiceLines([
        {
          id: 'v1',
          isSelected: true,
          name: 'rau muống',
          qty: 3,
          unit: 'bó',
          cost: 15000,
          location: 'FRIDGE',
          expiryDate: new Date(Date.now() + 3 * 86400000).toISOString().slice(0, 10),
        },
        {
          id: 'v2',
          isSelected: true,
          name: 'cà chua',
          qty: 2.5,
          unit: 'kg',
          cost: 32000,
          location: 'FRIDGE',
          expiryDate: new Date(Date.now() + 6 * 86400000).toISOString().slice(0, 10),
        },
        {
          id: 'v3',
          isSelected: true,
          name: 'hành lá',
          qty: 1.5,
          unit: 'kg',
          cost: 12000,
          location: 'FRIDGE',
          expiryDate: new Date(Date.now() + 4 * 86400000).toISOString().slice(0, 10),
        },
        {
          id: 'v4',
          isSelected: true,
          name: 'tỏi',
          qty: 1,
          unit: 'kg',
          cost: 55000,
          location: 'PANTRY',
          expiryDate: new Date(Date.now() + 25 * 86400000).toISOString().slice(0, 10),
        },
      ]);
      onShowToast('Đã tải hóa đơn mẫu: Rau củ & gia vị tươi');
    } else if (sampleType === 'MEAT') {
      setDocKind('IMPORT');
      setInvoiceLines([
        {
          id: 'm1',
          isSelected: true,
          name: 'thịt ba rọi',
          qty: 3.0,
          unit: 'kg',
          cost: 155000,
          location: 'FREEZER',
          expiryDate: new Date(Date.now() + 28 * 86400000).toISOString().slice(0, 10),
        },
        {
          id: 'm2',
          isSelected: true,
          name: 'ức gà',
          qty: 2.0,
          unit: 'kg',
          cost: 85000,
          location: 'FRIDGE',
          expiryDate: new Date(Date.now() + 3 * 86400000).toISOString().slice(0, 10),
        },
        {
          id: 'm3',
          isSelected: true,
          name: 'trứng gà',
          qty: 20,
          unit: 'quả',
          cost: 3500,
          location: 'FRIDGE',
          expiryDate: new Date(Date.now() + 12 * 86400000).toISOString().slice(0, 10),
        },
      ]);
      onShowToast('Đã tải hóa đơn mẫu: Thịt tươi & trứng');
    } else {
      setDocKind('SALES');
      setSalesLines([
        { id: 's1', isSelected: true, dishName: 'Trứng chiên cà chua', qty: 6, unitPrice: 35000 },
        { id: 's2', isSelected: true, dishName: 'Cơm chiên trứng', qty: 8, unitPrice: 40000 },
        { id: 's3', isSelected: true, dishName: 'Gà xào nấm', qty: 4, unitPrice: 60000 },
        { id: 's4', isSelected: true, dishName: 'Canh cà chua trứng', qty: 5, unitPrice: 30000 },
      ]);
      onShowToast('Đã tải báo cáo xuất mẫu: Ca trưa');
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.name.toLowerCase().includes('xuat') || file.name.toLowerCase().includes('ban')) {
      handleLoadSample('LUNCH');
    } else {
      handleLoadSample('VEGGIE');
    }
    onShowToast(`Đã nhận diện file "${file.name}" và bóc tách thành công các dòng chứng từ.`);
  };

  // Add line
  const handleAddInvoiceLine = () => {
    setInvoiceLines((prev) => [
      ...prev,
      {
        id: `inv-${Date.now()}`,
        isSelected: true,
        name: '',
        qty: 1,
        unit: 'kg',
        cost: 20000,
        location: 'FRIDGE',
        expiryDate: new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10),
      },
    ]);
  };

  const handleAddSalesLine = () => {
    const dishes = simulationStore.getState().dishes;
    const defaultDish = dishes[0]?.name || 'Trứng chiên cà chua';
    const defaultPrice = dishes[0]?.price_vnd || 35000;
    setSalesLines((prev) => [
      ...prev,
      {
        id: `sale-${Date.now()}`,
        isSelected: true,
        dishName: defaultDish,
        qty: 1,
        unitPrice: defaultPrice,
      },
    ]);
  };

  // Totals
  const selectedInvoiceLines = invoiceLines.filter((l) => l.isSelected && l.name.trim() && l.qty > 0);
  const totalInvoiceValue = selectedInvoiceLines.reduce((sum, l) => sum + Math.round(l.qty * l.cost), 0);

  const selectedSalesLines = salesLines.filter((l) => l.isSelected && l.dishName.trim() && l.qty > 0);
  const totalSalesRevenue = selectedSalesLines.reduce((sum, l) => sum + Math.round(l.qty * l.unitPrice), 0);

  // Confirm Actions
  const handleConfirm = () => {
    setIsSubmitting(true);
    try {
      if (docKind === 'IMPORT') {
        if (selectedInvoiceLines.length === 0) {
          onShowToast('Vui lòng chọn ít nhất một dòng nguyên liệu hợp lệ để nhập kho.');
          setIsSubmitting(false);
          return;
        }

        const res = simulationStore.importReceiptDocument(
          selectedInvoiceLines.map((l) => ({
            name: l.name,
            qty: l.qty,
            unit: l.unit,
            cost: l.cost,
            location: l.location,
            expiry_date: l.expiryDate,
          })),
          docDate
        );

        onShowToast(`Đã xác nhận nhập ${res.createdCount} đợt hàng, tổng giá trị ${formatMoney(res.totalValue)} vào kho.`);
        onClose();
      } else {
        if (selectedSalesLines.length === 0) {
          onShowToast('Vui lòng chọn ít nhất một dòng món ăn hợp lệ để ghi nhận xuất bán.');
          setIsSubmitting(false);
          return;
        }

        const res = simulationStore.importSalesReportDocument(
          selectedSalesLines.map((l) => ({
            dish_name: l.dishName,
            qty: l.qty,
            unit_price: l.unitPrice,
          })),
          docDate
        );

        let msg = `Đã ghi nhận bán ${res.soldCount} phần món ăn, doanh thu ${formatMoney(res.totalRevenue)}.`;
        if (res.hasShortage) {
          msg += ` Phát hiện ${res.shortageCount} nguyên liệu thiếu hụt đã ghi nhận vào Option C.`;
        }
        onShowToast(msg);
        onClose();
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      onShowToast(`Lỗi xác nhận: ${errMsg}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ModalBackdrop
      isOpen={isOpen}
      onClose={onClose}
      title="Quét & Nhập chứng từ"
      subtitle="Bóc tách hóa đơn nhập nguyên liệu hoặc báo cáo xuất bán món theo ngày"
      icon={<FileText size={20} />}
      maxWidthClass="max-w-3xl"
    >
      <div className="space-y-5">
        {/* Document Kind Tabs */}
        <div className="flex gap-2 p-1 bg-[var(--chip)] rounded-xl">
          <button
            type="button"
            onClick={() => setDocKind('IMPORT')}
            className={`flex-1 py-2 px-3 rounded-lg text-xs sm:text-sm font-semibold flex items-center justify-center gap-2 transition-all ${
              docKind === 'IMPORT'
                ? 'bg-[var(--card)] text-[var(--ink)] shadow-xs'
                : 'text-[var(--muted)] hover:text-[var(--ink)]'
            }`}
          >
            <Receipt size={16} />
            <span>Hóa đơn nhập kho</span>
          </button>
          <button
            type="button"
            onClick={() => setDocKind('SALES')}
            className={`flex-1 py-2 px-3 rounded-lg text-xs sm:text-sm font-semibold flex items-center justify-center gap-2 transition-all ${
              docKind === 'SALES'
                ? 'bg-[var(--card)] text-[var(--ink)] shadow-xs'
                : 'text-[var(--muted)] hover:text-[var(--ink)]'
            }`}
          >
            <ShoppingBag size={16} />
            <span>Báo cáo xuất bán hàng</span>
          </button>
        </div>

        {/* Date and Sample Quick Buttons */}
        <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-[var(--bg)] rounded-xl border border-[var(--line)]">
          <div className="flex items-center gap-2 text-xs">
            <span className="font-medium text-[var(--muted)]">Ngày chứng từ:</span>
            <input
              type="date"
              value={docDate}
              onChange={(e) => setDocDate(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg border border-[var(--line)] bg-[var(--card)] font-medium text-[var(--ink)] text-xs"
            />
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-semibold text-[var(--muted)] flex items-center gap-1 mr-1">
              <Sparkles size={13} className="text-[var(--accent-text)]" /> Mẫu nhanh:
            </span>
            {docKind === 'IMPORT' ? (
              <>
                <button
                  type="button"
                  onClick={() => handleLoadSample('VEGGIE')}
                  className="px-2.5 py-1 text-[11px] rounded-lg bg-[var(--card)] border border-[var(--line)] text-[var(--ink)] hover:bg-[var(--chip)] transition-colors font-medium"
                >
                  Rau củ & gia vị
                </button>
                <button
                  type="button"
                  onClick={() => handleLoadSample('MEAT')}
                  className="px-2.5 py-1 text-[11px] rounded-lg bg-[var(--card)] border border-[var(--line)] text-[var(--ink)] hover:bg-[var(--chip)] transition-colors font-medium"
                >
                  Thịt & trứng
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => handleLoadSample('LUNCH')}
                className="px-2.5 py-1 text-[11px] rounded-lg bg-[var(--card)] border border-[var(--line)] text-[var(--ink)] hover:bg-[var(--chip)] transition-colors font-medium"
              >
                Ca trưa hôm nay
              </button>
            )}
          </div>
        </div>

        {/* Upload Dropzone */}
        <label className="border-2 border-dashed border-[var(--line)] hover:border-[var(--accent)] bg-[var(--bg)]/40 hover:bg-[var(--bg)] p-4 rounded-xl flex items-center justify-center gap-3 cursor-pointer transition-colors text-center">
          <Upload size={20} className="text-[var(--accent-text)]" />
          <div className="text-left">
            <span className="text-xs font-semibold text-[var(--ink)] block">
              Tải file hoặc chụp ảnh hóa đơn / bảng kê
            </span>
            <span className="text-[11px] text-[var(--muted)]">
              Hỗ trợ CSV, Excel (.xlsx), ảnh chụp hóa đơn (JPG, PNG). AI sẽ tự động bóc tách.
            </span>
          </div>
          <input
            type="file"
            accept=".csv, .xlsx, .xls, image/*"
            className="hidden"
            onChange={handleFileUpload}
          />
        </label>

        {/* Interactive Lines Table */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--muted)]">
              {docKind === 'IMPORT' ? 'Danh sách nguyên liệu nhập' : 'Danh sách món ăn xuất bán'} (
              {docKind === 'IMPORT' ? selectedInvoiceLines.length : selectedSalesLines.length} dòng được chọn)
            </h3>
            <button
              type="button"
              onClick={docKind === 'IMPORT' ? handleAddInvoiceLine : handleAddSalesLine}
              className="text-xs font-semibold text-[var(--accent-text)] hover:underline flex items-center gap-1"
            >
              <Plus size={14} /> Thêm dòng
            </button>
          </div>

          <div className="border border-[var(--line)] rounded-xl overflow-x-auto bg-[var(--card)]">
            {docKind === 'IMPORT' ? (
              <table className="w-full text-xs text-left">
                <thead className="bg-[var(--bg)] text-[var(--muted)] border-b border-[var(--line)]">
                  <tr>
                    <th className="p-2.5 w-8 text-center">✓</th>
                    <th className="p-2.5 min-w-[140px]">Tên nguyên liệu</th>
                    <th className="p-2.5 w-20">Số lượng</th>
                    <th className="p-2.5 w-16">Đơn vị</th>
                    <th className="p-2.5 w-24">Đơn giá (đ)</th>
                    <th className="p-2.5 w-24">Vị trí</th>
                    <th className="p-2.5 w-28">Hạn dùng</th>
                    <th className="p-2.5 w-24 text-right">Thành tiền</th>
                    <th className="p-2.5 w-8"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--line)]">
                  {invoiceLines.map((line, idx) => (
                    <tr key={line.id} className={line.isSelected ? 'hover:bg-[var(--bg)]/50' : 'opacity-40'}>
                      <td className="p-2 text-center">
                        <input
                          type="checkbox"
                          checked={line.isSelected}
                          onChange={(e) => {
                            const val = e.target.checked;
                            setInvoiceLines((prev) =>
                              prev.map((l) => (l.id === line.id ? { ...l, isSelected: val } : l))
                            );
                          }}
                          className="rounded border-[var(--line)] text-[var(--accent)]"
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="text"
                          value={line.name}
                          onChange={(e) => {
                            const val = e.target.value;
                            setInvoiceLines((prev) =>
                              prev.map((l) => (l.id === line.id ? { ...l, name: val } : l))
                            );
                          }}
                          placeholder="vd: Cà chua"
                          className="w-full px-2 py-1 rounded border border-[var(--line)] bg-[var(--bg)] text-[var(--ink)] font-medium"
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="number"
                          step="0.1"
                          min="0"
                          value={line.qty}
                          onChange={(e) => {
                            const val = parseFloat(e.target.value) || 0;
                            setInvoiceLines((prev) =>
                              prev.map((l) => (l.id === line.id ? { ...l, qty: val } : l))
                            );
                          }}
                          className="w-full px-2 py-1 rounded border border-[var(--line)] bg-[var(--bg)] text-[var(--ink)]"
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="text"
                          value={line.unit}
                          onChange={(e) => {
                            const val = e.target.value;
                            setInvoiceLines((prev) =>
                              prev.map((l) => (l.id === line.id ? { ...l, unit: val } : l))
                            );
                          }}
                          className="w-full px-2 py-1 rounded border border-[var(--line)] bg-[var(--bg)] text-[var(--ink)]"
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="number"
                          step="500"
                          min="0"
                          value={line.cost}
                          onChange={(e) => {
                            const val = parseInt(e.target.value, 10) || 0;
                            setInvoiceLines((prev) =>
                              prev.map((l) => (l.id === line.id ? { ...l, cost: val } : l))
                            );
                          }}
                          className="w-full px-2 py-1 rounded border border-[var(--line)] bg-[var(--bg)] text-[var(--ink)] font-mono"
                        />
                      </td>
                      <td className="p-2">
                        <select
                          value={line.location}
                          onChange={(e) => {
                            const val = e.target.value as StorageLocation;
                            setInvoiceLines((prev) =>
                              prev.map((l) => (l.id === line.id ? { ...l, location: val } : l))
                            );
                          }}
                          className="w-full px-2 py-1 rounded border border-[var(--line)] bg-[var(--bg)] text-[var(--ink)]"
                        >
                          <option value="FRIDGE">Tủ lạnh</option>
                          <option value="FREEZER">Ngăn đông</option>
                          <option value="PANTRY">Tủ bếp</option>
                        </select>
                      </td>
                      <td className="p-2">
                        <input
                          type="date"
                          value={line.expiryDate}
                          onChange={(e) => {
                            const val = e.target.value;
                            setInvoiceLines((prev) =>
                              prev.map((l) => (l.id === line.id ? { ...l, expiryDate: val } : l))
                            );
                          }}
                          className="w-full px-2 py-1 rounded border border-[var(--line)] bg-[var(--bg)] text-[var(--ink)] text-[11px]"
                        />
                      </td>
                      <td className="p-2 text-right font-semibold font-mono text-[var(--ink)] whitespace-nowrap">
                        {formatMoney(Math.round(line.qty * line.cost))}
                      </td>
                      <td className="p-2 text-center">
                        <button
                          type="button"
                          onClick={() => setInvoiceLines((prev) => prev.filter((l) => l.id !== line.id))}
                          className="text-[var(--muted)] hover:text-[var(--bad-fg)] transition-colors p-1"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <table className="w-full text-xs text-left">
                <thead className="bg-[var(--bg)] text-[var(--muted)] border-b border-[var(--line)]">
                  <tr>
                    <th className="p-2.5 w-8 text-center">✓</th>
                    <th className="p-2.5 min-w-[160px]">Tên món ăn</th>
                    <th className="p-2.5 w-24">Số phần bán</th>
                    <th className="p-2.5 w-32">Giá bán (đ/phần)</th>
                    <th className="p-2.5 w-32 text-right">Doanh thu</th>
                    <th className="p-2.5 w-8"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--line)]">
                  {salesLines.map((line) => (
                    <tr key={line.id} className={line.isSelected ? 'hover:bg-[var(--bg)]/50' : 'opacity-40'}>
                      <td className="p-2 text-center">
                        <input
                          type="checkbox"
                          checked={line.isSelected}
                          onChange={(e) => {
                            const val = e.target.checked;
                            setSalesLines((prev) =>
                              prev.map((l) => (l.id === line.id ? { ...l, isSelected: val } : l))
                            );
                          }}
                          className="rounded border-[var(--line)] text-[var(--accent)]"
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="text"
                          value={line.dishName}
                          onChange={(e) => {
                            const val = e.target.value;
                            setSalesLines((prev) =>
                              prev.map((l) => (l.id === line.id ? { ...l, dishName: val } : l))
                            );
                          }}
                          className="w-full px-2 py-1 rounded border border-[var(--line)] bg-[var(--bg)] text-[var(--ink)] font-medium"
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="number"
                          min="1"
                          value={line.qty}
                          onChange={(e) => {
                            const val = parseInt(e.target.value, 10) || 0;
                            setSalesLines((prev) =>
                              prev.map((l) => (l.id === line.id ? { ...l, qty: val } : l))
                            );
                          }}
                          className="w-full px-2 py-1 rounded border border-[var(--line)] bg-[var(--bg)] text-[var(--ink)] font-semibold"
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="number"
                          step="1000"
                          min="0"
                          value={line.unitPrice}
                          onChange={(e) => {
                            const val = parseInt(e.target.value, 10) || 0;
                            setSalesLines((prev) =>
                              prev.map((l) => (l.id === line.id ? { ...l, unitPrice: val } : l))
                            );
                          }}
                          className="w-full px-2 py-1 rounded border border-[var(--line)] bg-[var(--bg)] text-[var(--ink)] font-mono"
                        />
                      </td>
                      <td className="p-2 text-right font-semibold font-mono text-[var(--ink)] whitespace-nowrap">
                        {formatMoney(Math.round(line.qty * line.unitPrice))}
                      </td>
                      <td className="p-2 text-center">
                        <button
                          type="button"
                          onClick={() => setSalesLines((prev) => prev.filter((l) => l.id !== line.id))}
                          className="text-[var(--muted)] hover:text-[var(--bad-fg)] transition-colors p-1"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Footer Summary & Confirm Button */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 bg-[var(--bg)] rounded-xl border border-[var(--line)]">
          <div className="text-left w-full sm:w-auto">
            <span className="text-xs text-[var(--muted)] block">
              {docKind === 'IMPORT' ? 'Tổng giá trị nhập dự kiến:' : 'Tổng doanh thu dự kiến:'}
            </span>
            <span className="text-lg font-bold font-mono text-[var(--accent-text)]">
              {docKind === 'IMPORT' ? formatMoney(totalInvoiceValue) : formatMoney(totalSalesRevenue)}
            </span>
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2.5 rounded-xl border border-[var(--line)] bg-[var(--card)] hover:bg-[var(--chip)] text-xs font-semibold text-[var(--ink)] transition-colors"
            >
              Hủy
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={isSubmitting}
              className="px-5 py-2.5 rounded-xl bg-[var(--accent)] hover:opacity-90 text-[var(--on-accent)] text-xs font-bold transition-all shadow-md flex items-center gap-1.5"
            >
              <CheckCircle2 size={16} />
              <span>
                {docKind === 'IMPORT' ? 'Xác nhận nhập kho' : 'Xác nhận xuất bán (FEFO)'}
              </span>
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  );
};
