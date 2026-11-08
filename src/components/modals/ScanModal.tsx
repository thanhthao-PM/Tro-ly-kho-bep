import React, { useEffect, useRef, useState } from 'react';
import { ModalBackdrop } from './ModalBackdrop';
import { simulationStore, formatMoney, formatQty } from '../../services/mock/simulationStore';
import { apiClient } from '../../services/api/client';
import { StorageLocation } from '../../types';
import {
  FileText,
  Upload,
  Camera,
  ScanLine,
  RotateCw,
  X,
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
  initialBusinessDate?: string;
  onReceiptSaved?: () => void;
}

interface ScanInvoiceLine {
  id: string;
  isSelected: boolean;
  name: string;
  ingredientId?: string;
  qty: number;
  unit: string;
  cost: number;
  location: StorageLocation;
  expiryDate: string;
}

interface CatalogIngredient {
  id: string;
  name: string;
  base_unit_code: string;
  default_location: StorageLocation;
  expiry_warning_days: number | null;
  aliases: string[];
}

interface ScanSalesLine {
  id: string;
  isSelected: boolean;
  dishName: string;
  qty: number;
  unitPrice: number;
}

const KITCHEN_ID = import.meta.env.VITE_KITCHEN_ID || '00000000-0000-0000-0000-000000000002';

export const ScanModal: React.FC<ScanModalProps> = ({
  isOpen,
  onClose,
  onShowToast,
  initialBusinessDate,
  onReceiptSaved,
}) => {
  const [docKind, setDocKind] = useState<'IMPORT' | 'SALES'>('IMPORT');
  const [docDate, setDocDate] = useState(() => new Date().toISOString().slice(0, 10));

  // Invoice lines state
  const [invoiceLines, setInvoiceLines] = useState<ScanInvoiceLine[]>([]);

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
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [isScanningImage, setIsScanningImage] = useState(false);
  const [cameraError, setCameraError] = useState('');
  const [capturedImageUrl, setCapturedImageUrl] = useState('');
  const [selectedImageFile, setSelectedImageFile] = useState<File | null>(null);
  const [catalogIngredients, setCatalogIngredients] = useState<CatalogIngredient[]>([]);
  const [catalogError, setCatalogError] = useState('');
  const cameraStreamRef = useRef<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const imageInputRef = useRef<HTMLInputElement | null>(null);
  const invoiceFileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (isOpen) setDocDate(initialBusinessDate || new Date().toISOString().slice(0, 10));
  }, [isOpen, initialBusinessDate]);

  useEffect(() => {
    if (!isOpen) return;
    let isCurrent = true;
    setCatalogError('');
    void apiClient.get<{ ingredients: CatalogIngredient[] }>('/documents/ingredients', { kitchen_id: KITCHEN_ID })
      .then(({ ingredients }) => {
        if (!isCurrent) return;
        setCatalogIngredients(ingredients);
        setInvoiceLines((previous) => previous.map((line) => {
          if (line.ingredientId) return line;
          const match = ingredients.find((item) => item.name.toLocaleLowerCase('vi') === line.name.trim().toLocaleLowerCase('vi'));
          return match ? { ...line, ingredientId: match.id, unit: match.base_unit_code } : line;
        }));
      })
      .catch((error: unknown) => {
        if (!isCurrent) return;
        const message = error instanceof Error ? error.message : 'Không tải được danh mục nguyên liệu.';
        setCatalogError(`Không kết nối được danh mục nguyên liệu: ${message}`);
      });
    return () => {
      isCurrent = false;
    };
  }, [isOpen]);

  const stopCamera = () => {
    cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
    cameraStreamRef.current = null;
    setIsCameraActive(false);
  };

  useEffect(() => {
    if (isOpen && docKind === 'IMPORT') return;
    stopCamera();
  }, [isOpen, docKind]);

  useEffect(() => {
    if (!isCameraActive || !videoRef.current || !cameraStreamRef.current) return;
    videoRef.current.srcObject = cameraStreamRef.current;
    void videoRef.current.play().catch(() => {
      setCameraError('Không thể phát video từ camera. Vui lòng kiểm tra quyền truy cập camera.');
    });
  }, [isCameraActive]);

  useEffect(() => {
    return () => {
      cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    return () => {
      if (capturedImageUrl) URL.revokeObjectURL(capturedImageUrl);
    };
  }, [capturedImageUrl]);

  const handleScanFile = async (file: File) => {
    const extension = file.name.split('.').pop()?.toLowerCase();
    const mimeByExtension: Record<string, string> = {
      jpg: 'image/jpeg',
      jpeg: 'image/jpeg',
      png: 'image/png',
      webp: 'image/webp',
      pdf: 'application/pdf',
    };
    const normalizedFile = !file.type || file.type === 'application/octet-stream'
      ? file
      : new File([file], file.name, { type: mimeByExtension[extension || ''] || '' });
    const isImage = normalizedFile.type === 'image/jpeg'
      || normalizedFile.type === 'image/png'
      || normalizedFile.type === 'image/webp';
    const isImageOrPdf = isImage || normalizedFile.type === 'application/pdf';
    const isTabular = extension === 'csv' || extension === 'xlsx';
    if (!isImageOrPdf && !isTabular) {
      onShowToast('Chỉ hỗ trợ ảnh JPG, PNG, WebP, PDF, CSV hoặc XLSX.');
      return;
    }

    stopCamera();
    setCameraError('');
    setDocKind('IMPORT');
    setSelectedImageFile(normalizedFile);
    setCapturedImageUrl(isImage ? URL.createObjectURL(normalizedFile) : '');
    setInvoiceLines([]);
    setIsScanningImage(true);

    try {
      const formData = new FormData();
      formData.append('file', normalizedFile, normalizedFile.name);
      const endpoint = isTabular ? '/documents/parse-invoice-file' : '/documents/scan-invoice-image';
      const result = await apiClient.request<{ lines?: Array<{
        name?: string;
        qty?: number;
        unit?: string;
        cost?: number;
        location?: string;
        expiry_date?: string | null;
        ingredient_id?: string | null;
      }>; message?: string }>(endpoint, {
        method: 'POST',
        body: formData,
        params: { kitchen_id: KITCHEN_ID },
      });

      if (!Array.isArray(result.lines) || result.lines.length === 0) {
        throw new Error(result.message || 'Không tìm thấy dòng nguyên liệu trong hóa đơn.');
      }

      const fallbackExpiry = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);
      const parsedLines = result.lines.map((line, index): ScanInvoiceLine => {
        const location = line.location?.toUpperCase();
        return {
          id: `scan-${Date.now()}-${index}`,
          isSelected: true,
          name: line.name?.trim() || '',
          ingredientId: line.ingredient_id || undefined,
          qty: Number.isFinite(Number(line.qty)) ? Number(line.qty) : 0,
          unit: line.unit?.trim() || 'kg',
          cost: Number.isFinite(Number(line.cost)) ? Number(line.cost) : 0,
          location: location === 'FREEZER' ? 'FREEZER' : location === 'DRY' || location === 'PANTRY' ? 'PANTRY' : 'FRIDGE',
          expiryDate: line.expiry_date || fallbackExpiry,
        };
      });

      setDocKind('IMPORT');
      setInvoiceLines(parsedLines);
      onShowToast(`Đã đọc ${parsedLines.length} dòng từ hóa đơn. Kiểm tra nguyên liệu rồi xác nhận để lưu vào kho.`);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Không thể đọc hóa đơn.';
      setCameraError(`${message} Bạn vẫn có thể nhập hoặc chỉnh sửa các dòng thủ công.`);
      onShowToast(`Đọc hóa đơn thất bại: ${message}`);
    } finally {
      setIsScanningImage(false);
    }
  };

  const handleStartCamera = async () => {
    setCameraError('');
    setInvoiceLines([]);
    setSelectedImageFile(null);
    setCapturedImageUrl('');
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError('Trình duyệt không hỗ trợ camera. Vui lòng tải ảnh hóa đơn lên.');
      return;
    }

    try {
      stopCamera();
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
        audio: false,
      });
      if (!isOpen || docKind !== 'IMPORT') {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      cameraStreamRef.current = stream;
      setIsCameraActive(true);
    } catch (error: unknown) {
      const name = error instanceof Error ? error.name : '';
      setCameraError(
        name === 'NotAllowedError'
          ? 'Bạn chưa cấp quyền sử dụng camera. Hãy cho phép truy cập hoặc tải ảnh hóa đơn lên.'
          : 'Không thể bật camera. Hãy kiểm tra thiết bị, quyền truy cập camera hoặc tải ảnh lên.'
      );
    }
  };

  const handleCaptureAndScan = () => {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0 || video.videoHeight === 0) {
      setCameraError('Camera chưa sẵn sàng. Vui lòng đợi hình ảnh hiển thị rồi chụp lại.');
      return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext('2d');
    if (!context) {
      setCameraError('Không thể xử lý ảnh chụp trên trình duyệt này.');
      return;
    }

    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (!blob) {
        setCameraError('Không thể tạo ảnh chụp. Vui lòng thử lại.');
        return;
      }

      void handleScanFile(new File([blob], `invoice-${Date.now()}.jpg`, { type: 'image/jpeg' }));
    }, 'image/jpeg', 0.9);
  };

  // Quick Samples
  const handleLoadSample = (sampleType: 'VEGGIE' | 'MEAT' | 'LUNCH') => {
    setSelectedImageFile(null);
    setCapturedImageUrl('');
    setCameraError('');
    setSelectedImageFile(null);
    setCapturedImageUrl('');
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

    void handleScanFile(file);
    e.currentTarget.value = '';
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
  const handleConfirm = async () => {
    setIsSubmitting(true);
    try {
      if (docKind === 'IMPORT') {
        if (selectedInvoiceLines.length === 0) {
          onShowToast('Vui lòng chọn ít nhất một dòng nguyên liệu hợp lệ để nhập kho.');
          setIsSubmitting(false);
          return;
        }

        const unresolvedLines = selectedInvoiceLines.filter((line) => !line.ingredientId);
        if (unresolvedLines.length > 0) {
          onShowToast(`Vui lòng chọn nguyên liệu trong danh mục cho: ${unresolvedLines.map((line) => line.name || 'dòng chưa đặt tên').join(', ')}.`);
          return;
        }

        const fileSha256 = selectedImageFile && crypto.subtle
          ? Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', await selectedImageFile.arrayBuffer())))
              .map((byte) => byte.toString(16).padStart(2, '0')).join('')
          : undefined;
        const idempotencyKey = typeof crypto.randomUUID === 'function'
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
        const receiptPayload = {
          business_date: docDate,
          original_filename: selectedImageFile?.name,
          file_sha256: fileSha256,
          lines: selectedInvoiceLines.map((line) => ({
            ingredient_id: line.ingredientId,
            name: line.name,
            quantity: line.qty,
            unit_code: line.unit,
            unit_cost: line.cost,
            location: line.location,
            expiry_date: line.expiryDate || null,
          })),
        };
        let body: BodyInit;
        let endpoint = '/documents/receipts';
        if (selectedImageFile) {
          const formData = new FormData();
          formData.append('file', selectedImageFile, selectedImageFile.name);
          formData.append('payload', JSON.stringify(receiptPayload));
          body = formData;
          endpoint = '/documents/receipts/upload';
        } else {
          body = JSON.stringify(receiptPayload);
        }
        const result = await apiClient.request<{ summary: { line_count: number; total_value_vnd: number } }>(
          endpoint,
          {
            method: 'POST',
            params: { kitchen_id: KITCHEN_ID },
            idempotencyKey,
            body,
          }
        );

        onShowToast(`Đã lưu ${result.summary.line_count} dòng nhập kho vào PostgreSQL, tổng giá trị ${formatMoney(result.summary.total_value_vnd)}.`);
        setSelectedImageFile(null);
        setCapturedImageUrl('');
        onReceiptSaved?.();
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

        {docKind === 'IMPORT' && (
          <section className="space-y-3 rounded-xl border border-[var(--line)] bg-[var(--bg)]/40 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 className="flex items-center gap-2 text-sm font-bold text-[var(--ink)]">
                  <ScanLine size={16} className="text-[var(--accent-text)]" />
                  Quét hóa đơn nhập kho
                </h3>
                <p className="mt-1 text-[11px] text-[var(--muted)]">
                  Chọn quét trực tiếp bằng camera hoặc gửi ảnh hóa đơn từ thiết bị.
                </p>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-3" role="group" aria-label="Chọn cách nhập hóa đơn">
              <button
                type="button"
                onClick={() => invoiceFileInputRef.current?.click()}
                disabled={isScanningImage || isCameraActive}
                className="flex items-start gap-3 rounded-xl border border-[var(--line)] bg-[var(--card)] p-4 text-left transition hover:border-[var(--accent)] hover:bg-[var(--chip)] disabled:opacity-50"
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--chip)] text-[var(--accent-text)]">
                  <FileText size={20} />
                </span>
                <span>
                  <span className="block text-sm font-bold text-[var(--ink)]">Chọn tệp hóa đơn</span>
                  <span className="mt-1 block text-[11px] text-[var(--muted)]">CSV, XLSX, PDF hoặc ảnh.</span>
                </span>
              </button>
              <button
                type="button"
                onClick={() => imageInputRef.current?.click()}
                disabled={isScanningImage || isCameraActive}
                className="flex items-start gap-3 rounded-xl border border-[var(--line)] bg-[var(--card)] p-4 text-left transition hover:border-[var(--accent)] hover:bg-[var(--chip)] disabled:opacity-50"
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--chip)] text-[var(--accent-text)]">
                  <Upload size={20} />
                </span>
                <span>
                  <span className="block text-sm font-bold text-[var(--ink)]">Chọn hình ảnh</span>
                  <span className="mt-1 block text-[11px] text-[var(--muted)]">JPG, PNG hoặc WebP.</span>
                </span>
              </button>
              <button
                type="button"
                onClick={() => void handleStartCamera()}
                disabled={isScanningImage || isCameraActive}
                className="flex items-start gap-3 rounded-xl border border-[var(--line)] bg-[var(--card)] p-4 text-left transition hover:border-[var(--accent)] hover:bg-[var(--chip)] disabled:opacity-50"
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--chip)] text-[var(--accent-text)]">
                  <Camera size={20} />
                </span>
                <span>
                  <span className="block text-sm font-bold text-[var(--ink)]">Chụp bằng camera</span>
                  <span className="mt-1 block text-[11px] text-[var(--muted)]">Chụp và đọc hóa đơn trực tiếp.</span>
                </span>
              </button>
            </div>
            <p className="text-[11px] text-[var(--muted)]">
              CSV/XLSX được đọc trực tiếp. Đọc ảnh/PDF cần cấu hình GEMINI_API_KEY ở backend. Sau khi kiểm tra các dòng,
              bấm “Xác nhận nhập kho” để ghi dữ liệu và tệp gốc vào hệ thống.
            </p>

            <input
              ref={imageInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              capture="environment"
              className="hidden"
              onChange={handleFileUpload}
            />
            <input
              ref={invoiceFileInputRef}
              type="file"
              accept=".csv,.xlsx,.pdf,image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={handleFileUpload}
            />

            {isCameraActive && (
              <div className="space-y-2">
                <div className="relative mx-auto w-full max-w-xl overflow-hidden rounded-xl bg-black">
                  <video ref={videoRef} autoPlay playsInline muted className="block max-h-[55vh] w-full object-contain" />
                  <div className="pointer-events-none absolute inset-[7%] rounded-lg border-2 border-white/90 shadow-[0_0_0_999px_rgba(0,0,0,0.2)]">
                    <span className="absolute left-1/2 top-2 -translate-x-1/2 rounded bg-black/50 px-2 py-1 text-[10px] font-medium text-white">
                      Căn hóa đơn trong khung hình
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={handleCaptureAndScan}
                    disabled={isScanningImage}
                    className="absolute bottom-3 left-1/2 flex -translate-x-1/2 items-center gap-2 whitespace-nowrap rounded-full bg-[var(--accent)] px-5 py-3 text-xs font-bold text-[var(--on-accent)] shadow-lg disabled:opacity-50"
                  >
                    <ScanLine size={16} /> Chụp & Quét AI
                  </button>
                </div>
                <button
                  type="button"
                  onClick={stopCamera}
                  className="mx-auto flex items-center gap-2 rounded-lg border border-[var(--line)] bg-[var(--card)] px-3 py-2 text-xs font-semibold text-[var(--ink)]"
                >
                  <X size={14} /> Tắt camera
                </button>
              </div>
            )}

            {!isCameraActive && selectedImageFile && (
              <div className="flex flex-col items-center gap-2 rounded-xl border border-[var(--line)] bg-[var(--card)] p-3">
                {capturedImageUrl ? (
                  <img
                    src={capturedImageUrl}
                    alt="Ảnh hóa đơn đã chọn"
                    className="max-h-56 max-w-full rounded-lg object-contain"
                  />
                ) : (
                  <div className="flex items-center gap-2 rounded-lg bg-[var(--bg)] px-4 py-3 text-xs font-medium text-[var(--ink)]">
                    <FileText size={18} /> {selectedImageFile.name}
                  </div>
                )}
                <div className="flex flex-wrap justify-center gap-2">
                  <button
                    type="button"
                    onClick={() => selectedImageFile && void handleScanFile(selectedImageFile)}
                    disabled={isScanningImage || !selectedImageFile}
                    className="flex items-center gap-2 rounded-lg bg-[var(--accent)] px-3 py-2 text-xs font-semibold text-[var(--on-accent)] disabled:opacity-50"
                  >
                    <RotateCw size={14} /> Quét lại tệp này
                  </button>
                  <button
                    type="button"
                    onClick={() => invoiceFileInputRef.current?.click()}
                    disabled={isScanningImage}
                    className="rounded-lg border border-[var(--line)] px-3 py-2 text-xs font-semibold text-[var(--ink)] disabled:opacity-50"
                  >
                    Chọn tệp khác
                  </button>
                </div>
              </div>
            )}
            {catalogError && <p role="alert" className="text-xs text-[var(--bad-fg)]">{catalogError}</p>}
            {isScanningImage && (
              <p role="status" className="flex items-center gap-2 text-xs font-medium text-[var(--accent-text)]">
                <RotateCw size={14} className="animate-spin" /> Đang gửi tệp và quét hóa đơn...
              </p>
            )}
            {cameraError && <p role="alert" className="text-xs text-[var(--bad-fg)]">{cameraError}</p>}
            {!invoiceLines.length && !isScanningImage && (
              <p className="text-xs text-[var(--muted)]">
                Chưa có dòng hóa đơn. Chọn tệp, hình ảnh, camera hoặc “Thêm dòng” để nhập thủ công.
              </p>
            )}
          </section>
        )}

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
                              const match = catalogIngredients.find(
                                (ingredient) => ingredient.name.toLocaleLowerCase('vi') === val.trim().toLocaleLowerCase('vi')
                            );
                              setInvoiceLines((prev) =>
                                prev.map((l) => (l.id === line.id
                                  ? {
                                      ...l,
                                      name: val,
                                      ingredientId: match?.id,
                                      unit: match?.base_unit_code || l.unit,
                                    }
                                  : l))
                              );
                            }}
                            placeholder="vd: Cà chua"
                            className="w-full px-2 py-1 rounded border border-[var(--line)] bg-[var(--bg)] text-[var(--ink)] font-medium"
                          />
                          <select
                            value={line.ingredientId || ''}
                            onChange={(e) => {
                              const ingredient = catalogIngredients.find((item) => item.id === e.target.value);
                              setInvoiceLines((prev) => prev.map((item) => item.id === line.id
                                ? {
                                    ...item,
                                    ingredientId: ingredient?.id,
                                    name: ingredient?.name || item.name,
                                    unit: ingredient?.base_unit_code || item.unit,
                                    location: ingredient?.default_location || item.location,
                                    expiryDate: ingredient
                                      ? new Date(Date.now() + (ingredient.expiry_warning_days ?? 7) * 86400000).toISOString().slice(0, 10)
                                      : item.expiryDate,
                                  }
                                : item));
                            }}
                            aria-label={`Chọn nguyên liệu trong danh mục cho ${line.name || 'dòng hàng'}`}
                            className="mt-1 w-full rounded border border-[var(--line)] bg-[var(--bg)] px-2 py-1 text-[10px] text-[var(--muted)]"
                          >
                            <option value="">Chọn nguyên liệu trong danh mục kho...</option>
                            {catalogIngredients.map((ingredient) => (
                              <option key={ingredient.id} value={ingredient.id}>
                                {ingredient.name} ({ingredient.base_unit_code})
                              </option>
                            ))}
                          </select>
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
