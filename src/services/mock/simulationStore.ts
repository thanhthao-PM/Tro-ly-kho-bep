/**
 * simulationStore.ts
 *
 * Engine mô phỏng nghiệp vụ trong trình duyệt (In-memory Simulation Engine)
 * dành riêng cho việc xem trước giao diện trên Google AI Studio Preview.
 *
 * Tái hiện 100% nghiệp vụ và giao diện từ demogiaodien.html:
 * - 4 Màn hình chính: Kho (KhoView), Thực đơn (MenuView), Trợ lý AI (AssistantView), Thống kê (ReportsView).
 * - Thuật toán FEFO, Option C (StockShortage), định lượng món ăn, 2 dòng lợi nhuận P&L,
 *   phân tích dòng tiền hàng hóa, nhận xét AI theo kỳ và hỏi đáp quy tắc.
 */

import {
  Batch,
  StockMovement,
  Dish,
  Sale,
  StockShortage,
  StorageLocation,
  ExpiryStatus,
  ReplenishmentSuggestion,
  ReplenishmentItem,
  AssistantMessageResponse,
  VerifiedFact,
  RecommendationItem,
  ProposedAction,
  ChatTurn
} from '../../types';
import { MASTER_PRODUCTS, INITIAL_DISHES } from './seedData';

const STORAGE_KEY = 'kitchen_assistant_preview_state_v2';

export interface SimLogEntry {
  id: number;
  date: string; // YYYY-MM-DD
  type: 'in' | 'sale' | 'use' | 'sell' | 'donate' | 'waste' | 'adjust';
  name?: string;
  dish?: string;
  qty?: number;
  portions?: number;
  value?: number;
  revenue?: number;
  cost?: number;
  src?: string;
  reason?: string;
  item?: string;
  note?: string;
}

export interface SimulationState {
  uid: number;
  kitchen: {
    id: string;
    name: string;
    timezone: string;
  };
  settings: {
    expiry_warning_days: number;
    target_coverage_days: number;
    consumption_window_days: number;
    min_history_days: number;
    unusual_quantity_ratio: number;
    backdate_limit_days: number;
    expired_batches_consumable: boolean;
    expired_batch_actions: string[];
  };
  batches: Batch[];
  movements: StockMovement[];
  dishes: Dish[];
  sales: Sale[];
  shortages: StockShortage[];
  logs: SimLogEntry[];
  events: Array<{ id: number; text: string; tone: 'ok' | 'warn' | 'bad' | 'neutral'; date: string }>;
  notification_reads: Record<string, boolean>;
  chat_history: Array<{ role: 'user' | 'assistant'; text: string }>;
}

export interface KhoProductGroup {
  name: string;
  unit: string;
  batches: Batch[];
  totalQty: number;
  stockValue: number;
  minDaysLeft: number;
  location: StorageLocation;
  lastImportDate: string;
  tone: 'ok' | 'warn' | 'bad';
  statusLabel: string;
}

export interface DishRankItem {
  dish: Dish;
  cost: number;
  price: number;
  grossMargin: number;
  marginPercent: number;
  maxPortions: number;
  missingIngredients: string[];
  usesExpiring: boolean;
}

export interface PeriodStatsResult {
  portions: number;
  saleRev: number;
  saleCost: number;
  useCost: number;
  sellRev: number;
  sellCost: number;
  sellN: number;
  donate: number;
  donateN: number;
  waste: number;
  wasteN: number;
  adjust: number;
  inV: number;
  repRev: number;
  repCost: number;
  repN: number;
  rev: number;
  cogs: number;
  profit: number;
  out: number;
}

export interface AIPeriodReview {
  summary: string[];
  causes: string[];
  anomalies: string[];
  actions: string[];
}

export interface PeriodReportFull {
  label: string;
  bname: string;
  from: string;
  to: string;
  current: PeriodStatsResult;
  previous: {
    label: string;
    stats: PeriodStatsResult;
  };
  isPartial: boolean;
  deltaRevText: string;
  deltaProfitText: string;
  buckets: Array<{
    label: string;
    from: string;
    to: string;
    isSelected?: boolean;
    stats: PeriodStatsResult;
    revenuePercent: number;
  }>;
  aiReview: AIPeriodReview | null;
  dishSales: Array<{
    name: string;
    portions: number;
    revenue: number;
    cost: number;
    profit: number;
  }>;
  repurposedLogs: SimLogEntry[];
  wasteByReason: Record<string, number>;
  wasteByIngredient: Array<{
    name: string;
    qty: number;
    cost: number;
    count: number;
    reasons: Record<string, number>;
  }>;
  wasteLogs: SimLogEntry[];
}

function pad(n: number): string {
  return n < 10 ? '0' + n : '' + n;
}

function toIsoDate(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function offsetDays(n: number): string {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() + n);
  return toIsoDate(d);
}

export function calculateDaysLeft(expiryDateStr?: string | null): number {
  if (!expiryDateStr) return 999;
  const parts = expiryDateStr.split('-');
  const exp = new Date(+parts[0], +parts[1] - 1, +parts[2]);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((exp.getTime() - today.getTime()) / 86400000);
}

export function formatDaysLabel(d: number): string {
  if (d < -1) return `Hết hạn ${-d} ngày`;
  if (d === -1) return 'Hết hạn hôm qua';
  if (d === 0) return 'Hết hạn hôm nay';
  if (d >= 60) return `Còn ~${Math.round(d / 30)} tháng`;
  return `Còn ${d} ngày`;
}

export function formatMoney(n: number): string {
  const r = Math.round(n);
  return (r < 0 ? '-' : '') + Math.abs(r).toLocaleString('vi-VN') + ' đ';
}

export function formatQty(n: number): string {
  const rounded = Math.round(n * 100) / 100;
  return String(rounded).replace('.', ',');
}

export function capitalize(s: string): string {
  if (!s) return '';
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function normalizeStr(s: string): string {
  return String(s)
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd');
}

export const STORAGE_LOCATIONS: Record<StorageLocation, string> = {
  FRIDGE: 'Tủ lạnh',
  PANTRY: 'Tủ bếp',
  FREEZER: 'Ngăn đông',
};

class SimulationStore {
  private state: SimulationState;
  private listeners: Array<() => void> = [];

  constructor() {
    this.state = this.loadState();
  }

  private initDefaultState(): SimulationState {
    const kitchenId = '00000000-0000-0000-0000-000000000001';
    let uid = 100;

    const batches: Batch[] = [];
    const movements: StockMovement[] = [];
    const logs: SimLogEntry[] = [];
    const events: Array<{ id: number; text: string; tone: 'ok' | 'warn' | 'bad' | 'neutral'; date: string }> = [];

    const addB = (name: string, q: number, loc: StorageLocation, imp: number, exp: number, cost: number) => {
      const bId = `batch-${uid++}`;
      const impDate = offsetDays(imp);
      const expDate = offsetDays(exp);
      const dLeft = calculateDaysLeft(expDate);
      const unit = MASTER_PRODUCTS[name.toLowerCase()]?.unit || 'kg';
      const val = Math.round(q * cost);

      batches.push({
        id: bId,
        ingredient_id: `ing-${name}`,
        ingredient_name: name,
        received_on: impDate,
        expiry_date: expDate,
        initial_qty: q.toFixed(3),
        remaining_qty: q.toFixed(3),
        unit,
        unit_cost: cost.toFixed(6),
        stock_value_vnd: val,
        location: loc,
        expiry_status: dLeft < 0 ? 'EXPIRED' : dLeft <= 3 ? 'EXPIRES_SOON' : 'OK',
        days_to_expiry: dLeft,
      });

      movements.push({
        id: `m-${uid++}`,
        occurred_on: impDate,
        type: 'RECEIPT',
        category: 'RECEIPT',
        ingredient_id: `ing-${name}`,
        ingredient_name: name,
        batch_id: bId,
        qty_delta: q.toFixed(3),
        unit,
        unit_cost_snapshot: cost.toFixed(6),
        value_vnd: val,
        reference_kind: 'INITIAL_SEED',
        created_at: new Date().toISOString(),
      });

      logs.push({
        id: uid++,
        date: impDate,
        type: 'in',
        name,
        qty: q,
        value: val,
        src: 'Hóa đơn',
      });
    };

    // 13 lô hàng mẫu ban đầu từ demogiaodien.html
    addB('rau muống', 1, 'FRIDGE', -2, -1, 20000);
    addB('sữa tươi', 2, 'FRIDGE', -5, 1, 30000);
    addB('cà chua', 1, 'FRIDGE', -5, 2, 35000);
    addB('cà chua', 1.5, 'FRIDGE', -1, 6, 38000);
    addB('trứng gà', 12, 'FRIDGE', -6, 9, 3500);
    addB('thịt ba rọi', 1, 'FREEZER', -3, 25, 150000);
    addB('thịt ba rọi', 2, 'FREEZER', 0, 28, 155000);
    addB('gạo', 10, 'PANTRY', -10, 300, 24000);
    addB('tỏi', 0.5, 'PANTRY', -8, 20, 60000);
    addB('hành tây', 2, 'PANTRY', -6, 12, 30000);
    addB('hành lá', 2, 'FRIDGE', -2, 3, 8000);
    addB('ức gà', 1, 'FRIDGE', -1, 2, 85000);
    addB('nấm', 0.5, 'FRIDGE', -1, 4, 90000);

    // Dữ liệu bán hàng & xử lý hàng quá khứ
    const addL = (o: Partial<SimLogEntry>, offset: number) => {
      logs.push({
        id: uid++,
        date: offsetDays(offset),
        type: o.type || 'sale',
        name: o.name,
        dish: o.dish,
        portions: o.portions,
        revenue: o.revenue,
        cost: o.cost,
        src: o.src,
        item: o.item,
        reason: o.reason,
        qty: o.qty,
        value: o.value,
        note: o.note,
      });
    };

    addL({ type: 'sale', dish: 'Trứng chiên cà chua', portions: 18, revenue: 630000, cost: 203400, src: 'menu' }, -9);
    addL({ type: 'sale', dish: 'Cơm chiên trứng', portions: 15, revenue: 600000, cost: 171000, src: 'menu' }, -6);
    addL({ type: 'sale', dish: 'Gà xào nấm', portions: 10, revenue: 600000, cost: 238500, src: 'menu' }, -4);
    addL({ type: 'sale', dish: 'Canh cà chua trứng', portions: 12, revenue: 360000, cost: 93600, src: 'menu' }, -1);
    addL({ type: 'sale', dish: 'Gà xào nấm', portions: 4, revenue: 240000, cost: 95400, src: 'repurpose', item: 'ức gà' }, -5);
    addL({ type: 'donate', name: 'cà chua', qty: 2, cost: 70000 }, -7);
    addL({ type: 'sell', name: 'thịt bằm', qty: 1, cost: 120000, revenue: 70000 }, -8);
    addL({ type: 'waste', name: 'rau muống', qty: 2, cost: 40000, reason: 'Hết hạn' }, -12);
    addL({ type: 'waste', name: 'rau muống', qty: 3, cost: 60000, reason: 'Nhập dư' }, -5);
    addL({ type: 'waste', name: 'sữa tươi', qty: 2, cost: 60000, reason: 'Hết hạn' }, -6);
    addL({ type: 'waste', name: 'cà chua', qty: 1.5, cost: 52500, reason: 'Hỏng/ôi thiu' }, -3);
    addL({ type: 'waste', name: 'đậu hũ', qty: 4, cost: 24000, reason: 'Hết hạn' }, -2);
    addL({ type: 'adjust', name: 'trứng gà', qty: 3, cost: 10500, reason: 'Kiểm kho' }, -4);

    const sl = (dish: string, portions: number, price: number, costPer: number, offset: number) => {
      addL({ type: 'sale', dish, portions, revenue: portions * price, cost: Math.round(portions * costPer), src: 'menu' }, offset);
    };
    sl('Cơm chiên trứng', 12, 40000, 11400, -13);
    sl('Trứng chiên cà chua', 14, 35000, 11300, -12);
    sl('Gà xào nấm', 8, 60000, 23850, -11);
    sl('Thịt kho trứng', 9, 65000, 31000, -8);
    sl('Canh cà chua trứng', 10, 30000, 7800, -7);
    sl('Rau muống xào tỏi', 16, 30000, 5200, -3);
    sl('Trứng chiên cà chua', 16, 35000, 11300, -2);
    sl('Cơm chiên trứng', 10, 40000, 11400, 0);
    sl('Trứng chiên cà chua', 60, 35000, 11300, -33);
    sl('Cơm chiên trứng', 55, 40000, 11400, -34);
    sl('Gà xào nấm', 30, 60000, 23850, -41);
    sl('Thịt kho trứng', 28, 65000, 31000, -48);
    sl('Trứng chiên cà chua', 70, 35000, 11300, -66);
    sl('Cơm chiên trứng', 64, 40000, 11400, -72);
    sl('Canh cà chua trứng', 50, 30000, 7800, -79);
    sl('Gà xào nấm', 36, 60000, 23850, -95);
    addL({ type: 'waste', name: 'rau muống', qty: 4, cost: 80000, reason: 'Hết hạn' }, -35);
    addL({ type: 'waste', name: 'sữa tươi', qty: 3, cost: 90000, reason: 'Hết hạn' }, -70);
    addL({ type: 'donate', name: 'cà chua', qty: 1.5, cost: 52500 }, -45);

    // Tính dòng nhập lịch sử tổng hợp
    let outs = 0;
    logs.forEach((l) => {
      if (l.type !== 'in') outs += l.cost || 0;
    });
    const currentStock = batches.reduce((sum, b) => sum + b.stock_value_vnd, 0);
    const bIn = batches.reduce((sum, b) => sum + b.stock_value_vnd, 0);
    const hist = outs + currentStock - bIn;
    if (hist > 0) {
      logs.push({
        id: uid++,
        date: offsetDays(-120),
        type: 'in',
        name: 'Nhập hàng các kỳ trước',
        qty: 0,
        value: hist,
        src: 'Tổng hợp',
      });
    }

    const dishes: Dish[] = INITIAL_DISHES.map((d) => {
      const dishId = `dish-${uid++}`;
      return {
        id: dishId,
        name: d.name,
        price_vnd: d.price_vnd,
        recipe: d.ingredients.map((ing) => ({
          ingredient_id: `ing-${ing.name}`,
          ingredient_name: ing.name,
          quantity: ing.quantity,
          unit: MASTER_PRODUCTS[ing.name]?.unit || 'kg',
        })),
        cost_estimate_vnd: { value: 0, basis: 'ESTIMATE' },
        gross_margin_estimate: { amount_vnd: 0, percent: 0, basis: 'ESTIMATE' },
        max_portions: 0,
        missing_ingredients: [],
        uses_expiring_stock: false,
      };
    });

    return {
      uid,
      kitchen: {
        id: kitchenId,
        name: 'Bếp Cơm Gia Đình',
        timezone: 'Asia/Ho_Chi_Minh',
      },
      settings: {
        expiry_warning_days: 3,
        target_coverage_days: 3,
        consumption_window_days: 14,
        min_history_days: 7,
        unusual_quantity_ratio: 2.0,
        backdate_limit_days: 2,
        expired_batches_consumable: false,
        expired_batch_actions: ['WASTE'],
      },
      batches,
      movements,
      dishes,
      sales: [],
      shortages: [],
      logs,
      events,
      notification_reads: {},
      chat_history: [
        {
          role: 'assistant',
          text: 'Xin chào! Mình là trợ lí kho bếp. Bạn có thể hỏi về tồn kho, đồ cần xử lí, lãi lỗ hoặc món nên nấu.',
        },
      ],
    };
  }

  private loadState(): SimulationState {
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      if (data) {
        const parsed = JSON.parse(data);
        if (parsed && parsed.batches && parsed.dishes && parsed.logs) {
          return parsed;
        }
      }
    } catch {
      // Fallback
    }
    return this.initDefaultState();
  }

  saveState() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.state));
    } catch {
      // ignore
    }
    this.notify();
  }

  resetDemo() {
    this.state = this.initDefaultState();
    this.saveState();
  }

  subscribe(listener: () => void) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  private notify() {
    this.listeners.forEach((l) => l());
  }

  getState(): SimulationState {
    return this.state;
  }

  // ==========================================
  // VIEW 1: KHO (KhoView)
  // ==========================================

  getImportDates(): string[] {
    const dates = new Set<string>();
    this.state.batches.forEach((b) => dates.add(b.received_on));
    return Array.from(dates).sort().reverse();
  }

  getUsableBatches(name: string): Batch[] {
    const today = offsetDays(0);
    return this.state.batches
      .filter((b) => {
        if (b.ingredient_name.toLowerCase() !== name.toLowerCase()) return false;
        if (parseFloat(b.remaining_qty) <= 0.0001) return false;
        return calculateDaysLeft(b.expiry_date) >= 0;
      })
      .sort((a, b) => (a.expiry_date || '').localeCompare(b.expiry_date || ''));
  }

  getAvailableQty(name: string): number {
    return this.getUsableBatches(name).reduce((sum, b) => sum + parseFloat(b.remaining_qty), 0);
  }

  getAvgUnitCost(name: string): number {
    const usable = this.getUsableBatches(name);
    let qty = 0;
    let val = 0;
    usable.forEach((b) => {
      const q = parseFloat(b.remaining_qty);
      qty += q;
      val += q * parseFloat(b.unit_cost);
    });
    if (qty > 0) return val / qty;
    return MASTER_PRODUCTS[name.toLowerCase()]?.default_cost_vnd || 0;
  }

  getExpiringSummary() {
    let soon = 0;
    let expired = 0;
    this.state.batches.forEach((b) => {
      const d = calculateDaysLeft(b.expiry_date);
      if (d < 0) expired++;
      else if (d <= 2) soon++;
    });
    return { soon, expired };
  }

  getKhoProducts(
    search = '',
    dateFilter = 'all',
    sort = 'exp',
    locationFilter = 'all'
  ): KhoProductGroup[] {
    const q = normalizeStr(search.trim());
    const today = offsetDays(0);
    const sevenDaysAgo = offsetDays(-6);

    const filteredBatches = this.state.batches.filter((b) => {
      if (parseFloat(b.remaining_qty) <= 0.0001) return false;
      if (q && !normalizeStr(b.ingredient_name).includes(q)) return false;
      if (dateFilter === 'today' && b.received_on !== today) return false;
      if (dateFilter === '7' && b.received_on < sevenDaysAgo) return false;
      if (dateFilter !== 'all' && dateFilter !== 'today' && dateFilter !== '7' && b.received_on !== dateFilter) {
        return false;
      }
      return true;
    });

    const groupsMap = new Map<string, Batch[]>();
    filteredBatches.forEach((b) => {
      const key = b.ingredient_name.toLowerCase();
      const list = groupsMap.get(key) || [];
      list.push(b);
      groupsMap.set(key, list);
    });

    const groups: KhoProductGroup[] = [];
    groupsMap.forEach((batchList, name) => {
      batchList.sort((a, b) => (a.expiry_date || '').localeCompare(b.expiry_date || ''));
      let totalQty = 0;
      let stockValue = 0;
      let lastImp = '';

      batchList.forEach((b) => {
        const qVal = parseFloat(b.remaining_qty);
        totalQty += qVal;
        stockValue += Math.round(qVal * parseFloat(b.unit_cost));
        if (b.received_on > lastImp) lastImp = b.received_on;
      });

      const earliest = batchList[0];
      const minD = calculateDaysLeft(earliest.expiry_date);
      const tone: 'ok' | 'warn' | 'bad' = minD < 0 ? 'bad' : minD <= 3 ? 'warn' : 'ok';
      const unit = MASTER_PRODUCTS[name]?.unit || earliest.unit || 'kg';

      if (locationFilter === 'all' || earliest.location === locationFilter.toUpperCase()) {
        groups.push({
          name,
          unit,
          batches: batchList,
          totalQty,
          stockValue,
          minDaysLeft: minD,
          location: earliest.location,
          lastImportDate: lastImp,
          tone,
          statusLabel: formatDaysLabel(minD),
        });
      }
    });

    if (sort === 'exp') {
      groups.sort((a, b) => a.minDaysLeft - b.minDaysLeft);
    } else if (sort === 'imp') {
      groups.sort((a, b) => b.lastImportDate.localeCompare(a.lastImportDate));
    } else {
      groups.sort((a, b) => a.name.localeCompare(b.name, 'vi'));
    }

    return groups;
  }

  // ==========================================
  // VIEW 2: THỰC ĐƠN (MenuView)
  // ==========================================

  getDishRank(): DishRankItem[] {
    return this.state.dishes
      .map((dish) => {
        let cost = 0;
        let maxPortions = 999999;
        const missing: string[] = [];
        let usesExpiring = false;

        dish.recipe.forEach((item) => {
          const ingName = item.ingredient_name || '';
          const needed = parseFloat(item.quantity) || 0;
          const avgCost = this.getAvgUnitCost(ingName);
          cost += needed * avgCost;

          const avail = this.getAvailableQty(ingName);
          if (needed > 0) {
            const p = Math.floor(avail / needed);
            maxPortions = Math.min(maxPortions, p);
            if (avail < needed) missing.push(ingName);
          }

          const usable = this.getUsableBatches(ingName);
          if (usable.some((b) => calculateDaysLeft(b.expiry_date) <= 3)) {
            usesExpiring = true;
          }
        });

        if (maxPortions === 999999) maxPortions = 0;
        const roundedCost = Math.round(cost);
        const price = dish.price_vnd;
        const grossMargin = price - roundedCost;
        const marginPercent = price > 0 ? Math.round((grossMargin / price) * 100) : 0;

        return {
          dish,
          cost: roundedCost,
          price,
          grossMargin,
          marginPercent,
          maxPortions,
          missingIngredients: missing,
          usesExpiring,
        };
      })
      .sort((a, b) => {
        const scoreA = (a.maxPortions > 0 ? 100 : 0) + (a.usesExpiring ? 20 : 0) + a.marginPercent / 10;
        const scoreB = (b.maxPortions > 0 ? 100 : 0) + (b.usesExpiring ? 20 : 0) + b.marginPercent / 10;
        return scoreB - scoreA;
      });
  }

  setDishPrice(dishId: string, price: number) {
    const dish = this.state.dishes.find((d) => d.id === dishId);
    if (dish && price >= 0) {
      dish.price_vnd = Math.round(price);
      this.saveState();
    }
  }

  // ==========================================
  // VIEW 3: TRỢ LÝ AI (AssistantView)
  // ==========================================

  getAICashflow() {
    const s = this.computePeriodStats(undefined);
    const stockVal = this.state.batches.reduce(
      (sum, b) => sum + Math.round(parseFloat(b.remaining_qty) * parseFloat(b.unit_cost)),
      0
    );

    const segments = [
      { label: 'Giá vốn bán', value: s.cogs, color: 'var(--ok-fg)', percent: 0 },
      { label: 'Quyên góp', value: s.donate, color: 'var(--accent-text)', percent: 0 },
      { label: 'Đã bỏ', value: s.waste + s.adjust, color: 'var(--bad-fg)', percent: 0 },
      { label: 'Còn trong kho', value: stockVal, color: 'var(--muted)', percent: 0 },
    ];

    const total = segments.reduce((sum, item) => sum + item.value, 0);
    if (total > 0) {
      segments.forEach((seg) => {
        seg.percent = Math.round((seg.value / total) * 100);
      });
    }

    return {
      inV: s.inV,
      out: s.out,
      stockVal,
      segments,
      unusualWarningCount: this.state.events.filter((e) => e.text.includes('bất thường')).length,
    };
  }

  getAIProductInsights() {
    const wasteGroups = this.getWasteGroups(undefined);
    return wasteGroups.slice(0, 5).map((g) => {
      const c = MASTER_PRODUCTS[g.name];
      const obs: string[] = [];
      if (g.reasons['Nhập dư']) obs.push(`Từng nhập vượt nhu cầu ${g.reasons['Nhập dư']} lần.`);
      if (c && c.shelf_life_days <= 4) obs.push(`Hạn dùng ngắn (~${c.shelf_life_days} ngày), dễ hết hạn nếu nhập nhiều.`);
      if (g.reasons['Hết hạn'] && !g.reasons['Nhập dư']) obs.push(`Dùng không kịp trước hạn ${g.reasons['Hết hạn']} lần.`);
      if (g.reasons['Hỏng/ôi thiu']) obs.push(`Hỏng khi còn hạn ${g.reasons['Hỏng/ôi thiu']} lần, nên xem lại bảo quản.`);

      const rec = c?.usual_quantity
        ? `Nhập ${c.usual_quantity[0]}–${c.usual_quantity[1]} ${c.unit} mỗi lần${c.shelf_life_days <= 4 ? ', chia 2 lần mỗi tuần' : ''}.`
        : 'Giảm khoảng 20–30% so với lần nhập gần nhất.';
      const tip = g.reasons['Hỏng/ôi thiu'] && c?.storage_tip ? ` Bảo quản: ${c.storage_tip}` : '';

      return {
        name: g.name,
        qty: g.qty,
        unit: c?.unit || 'kg',
        cost: g.cost,
        count: g.count,
        reasonsText: Object.entries(g.reasons)
          .map(([r, n]) => `${r} ×${n}`)
          .join(', '),
        observations: obs.length ? obs.join(' ') : 'Chưa có ghi nhận thêm.',
        suggestion: rec + tip,
      };
    });
  }

  getAIStockOverview() {
    const products = this.getKhoProducts();
    const totalIngredients = products.length;
    const totalBatches = this.state.batches.filter((b) => parseFloat(b.remaining_qty) > 0.0001).length;
    const stockVal = products.reduce((sum, p) => sum + p.stockValue, 0);

    const byLocation = { fridge: 0, pantry: 0, freezer: 0 };
    const byTone = { ok: 0, warn: 0, bad: 0 };

    products.forEach((p) => {
      if (p.location === 'FRIDGE') byLocation.fridge++;
      else if (p.location === 'FREEZER') byLocation.freezer++;
      else byLocation.pantry++;

      byTone[p.tone]++;
    });

    const needReorder: string[] = [];
    const overstocked: string[] = [];

    products.forEach((p) => {
      const c = MASTER_PRODUCTS[p.name];
      if (!c?.usual_quantity) return;
      const [low, high] = c.usual_quantity;
      if (p.totalQty < low * 0.5) {
        needReorder.push(`${capitalize(p.name)}: còn ${formatQty(p.totalQty)} ${p.unit}, mức thường ${low}–${high}`);
      } else if (p.totalQty > high * 2) {
        overstocked.push(`${capitalize(p.name)}: đang có ${formatQty(p.totalQty)} ${p.unit}, mức thường ${low}–${high}`);
      }
    });

    return {
      totalIngredients,
      totalBatches,
      stockVal,
      byLocation,
      byTone,
      needReorder,
      overstocked,
    };
  }

  askAI(question: string): string {
    const n = normalizeStr(question);
    const productNames = Object.keys(MASTER_PRODUCTS);
    const matchedNames = productNames.filter((k) => n.includes(normalizeStr(k)));

    if (matchedNames.length && /con|bao nhieu|ton|het|dang co/.test(n)) {
      return matchedNames
        .map((nm) => {
          const bs = this.state.batches.filter((b) => b.ingredient_name.toLowerCase() === nm.toLowerCase() && parseFloat(b.remaining_qty) > 0.0001);
          if (!bs.length) return `${capitalize(nm)}: kho đang không có.`;
          const total = bs.reduce((sum, b) => sum + parseFloat(b.remaining_qty), 0);
          const unit = bs[0].unit;
          return `${capitalize(nm)}: còn ${formatQty(total)} ${unit} (${bs.length} đợt).\n` +
            bs.map((b) => `• Nhập ${b.received_on.slice(5)}: ${formatQty(parseFloat(b.remaining_qty))} ${unit}, ${formatDaysLabel(calculateDaysLeft(b.expiry_date)).toLowerCase()}`).join('\n');
        })
        .join('\n\n');
    }

    if (/xu li|xu ly|hom nay|sap het|uu tien/.test(n)) {
      const bs = this.state.batches
        .filter((b) => parseFloat(b.remaining_qty) > 0.0001 && calculateDaysLeft(b.expiry_date) <= 2)
        .sort((a, b) => (a.expiry_date || '').localeCompare(b.expiry_date || ''));
      if (!bs.length) return 'Hôm nay chưa có đợt nào cần xử lí gấp. Kho đang ổn.';
      return (
        'Nên xử lí theo thứ tự:\n' +
        bs
          .map((b, i) => {
            const d = calculateDaysLeft(b.expiry_date);
            const action = d >= 0 ? 'nấu món hoặc quyên góp, bán thu mua' : 'nên bỏ và ghi nhận hao hụt';
            return `${i + 1}. ${capitalize(b.ingredient_name)} ${formatQty(parseFloat(b.remaining_qty))} ${b.unit} (${formatDaysLabel(d).toLowerCase()}): ${action}.`;
          })
          .join('\n')
      );
    }

    if (/lang phi|bo nhieu|bo di|hao hut/.test(n)) {
      const g = this.getWasteGroups(undefined);
      if (!g.length) return 'Chưa có dữ liệu hao hụt bỏ đi.';
      return (
        'Đồ bỏ nhiều nhất theo giá trị:\n' +
        g.slice(0, 3).map((x) => `• ${capitalize(x.name)}: ${formatQty(x.qty)} ${MASTER_PRODUCTS[x.name]?.unit || 'kg'} (~${formatMoney(x.cost)})`).join('\n') +
        '\n\nKhuyến nghị: Ưu tiên quyên góp, bán thu mua hoặc đưa vào thực đơn trước hạn 2 ngày.'
      );
    }

    if (/lai|loi nhuan|doanh thu/.test(n)) {
      const ranks = this.getDishRank();
      const s = this.computePeriodStats(undefined);
      if (!ranks.length) return 'Thực đơn chưa có món nào.';
      const best = ranks[0];
      return `Món lãi gộp cao nhất mỗi phần: ${best.dish.name} (${formatMoney(best.grossMargin)}, biên ${best.marginPercent}%).\nTổng doanh thu kỳ: ${formatMoney(s.rev)}, lợi nhuận sau hao hụt: ${formatMoney(s.profit)}.`;
    }

    if (/nau|mon|thuc don|du/.test(n)) {
      const available = this.getDishRank().filter((r) => r.maxPortions > 0).slice(0, 3);
      if (!available.length) return 'Kho hiện chưa đủ nguyên liệu để làm trọn vẹn món nào.';
      return (
        'Kho đang đủ nguyên liệu để nấu:\n' +
        available.map((r) => `• ${r.dish.name}: tối đa ${r.maxPortions} phần, lãi ${formatMoney(r.grossMargin)}/phần`).join('\n')
      );
    }

    if (/nhap/.test(n)) {
      const s = this.computePeriodStats(undefined);
      const stockVal = this.state.batches.reduce((sum, b) => sum + Math.round(parseFloat(b.remaining_qty) * parseFloat(b.unit_cost)), 0);
      return `Tổng nhập từ đầu: ${formatMoney(s.inV)}. Giá trị còn trong kho: ${formatMoney(stockVal)}.`;
    }

    if (/dat hang|bo sung|replenishment|d25/.test(n)) {
      const repl = this.getD25ReplenishmentSuggestions();
      if (repl.items.length) {
        return (
          `Thuật toán D25 đề xuất bổ sung ${repl.items.length} mặt hàng:\n` +
          repl.items.map((it) => `• ${capitalize(it.ingredient_name)}: đề xuất đặt ${it.suggested_order_qty} ${it.unit} (tồn khả dụng: ${it.usable_qty} ${it.unit}, còn đủ ~${it.days_of_cover || '?'} ngày, quy tắc: ${it.rule})`).join('\n')
        );
      }
      return 'Tồn kho hiện tại đủ an toàn theo mục tiêu bao phủ D25. Chưa cần đặt thêm hàng.';
    }

    if (/thieu hut|shortage|option c/.test(n)) {
      const open = this.state.shortages.filter((s) => s.status === 'OPEN');
      if (open.length) {
        return (
          `Đang có ${open.length} bản ghi thiếu hụt Option C cần giải quyết:\n` +
          open.map((s) => `• ${capitalize(s.ingredient_name)}: thiếu ${s.short_qty} ${s.unit}`).join('\n')
        );
      }
      return 'Không có trường hợp thiếu hụt Option C nào đang mở.';
    }

    return 'Mình chưa hiểu rõ câu hỏi này. Bạn có thể hỏi về tồn kho một mặt hàng (ví dụ: "thịt ba rọi còn bao nhiêu?"), món nên xử lí, đề xuất bổ sung hàng D25, món lãi nhất hoặc nguyên liệu hao hụt nhiều nhất.';
  }

  // ==========================================
  // THUẬT TOÁN D25: ĐỀ XUẤT BỔ SUNG HÀNG (REPLENISHMENT)
  // Tuân thủ nghiêm ngặt Revision 6.3 §2.4
  // ==========================================

  getD25ReplenishmentSuggestions(
    asOfDate?: string,
    targetCoverageDays?: number,
    consumptionWindowDays?: number,
    minHistoryDays?: number
  ): ReplenishmentSuggestion {
    const today = asOfDate || offsetDays(0);
    const yesterday = offsetDays(-1);

    const covDays = targetCoverageDays ?? this.state.settings.target_coverage_days ?? 3;
    const winDays = consumptionWindowDays ?? this.state.settings.consumption_window_days ?? 14;
    const minHist = minHistoryDays ?? this.state.settings.min_history_days ?? 7;
    const allowExpired = this.state.settings.expired_batches_consumable ?? false;

    // Danh sách nguyên liệu duy nhất từ MASTER_PRODUCTS và các lô thực tế
    const ingredientNames = Array.from(
      new Set([
        ...Object.keys(MASTER_PRODUCTS),
        ...this.state.batches.map((b) => b.ingredient_name.toLowerCase())
      ])
    ).sort();

    const items: ReplenishmentItem[] = [];
    const insufficient_data: Array<{ ingredient_name: string; reason: string; observed_days: number }> = [];
    const no_recent_consumption: Array<{ ingredient_name: string; usable_qty: string; unit: string }> = [];

    for (const name of ingredientNames) {
      const master = MASTER_PRODUCTS[name];
      const unit = master?.unit || this.state.batches.find((b) => b.ingredient_name.toLowerCase() === name)?.unit || 'kg';
      const minStock = master?.usual_quantity ? master.usual_quantity[0] : 0;
      const orderStep = 0.5;

      // 1. Tồn khả dụng (usable_qty): tổng remaining_qty của các lô còn hạn (hoặc tất cả nếu allowExpired)
      const usableBatches = this.state.batches.filter((b) => {
        if (b.ingredient_name.toLowerCase() !== name) return false;
        if (parseFloat(b.remaining_qty) <= 0.0001) return false;
        if (allowExpired) return true;
        const dLeft = calculateDaysLeft(b.expiry_date);
        return dLeft >= 0;
      });
      const usableQty = usableBatches.reduce((sum, b) => sum + parseFloat(b.remaining_qty), 0);

      // 2. Lịch sử biến động
      const ingMovements = this.state.movements.filter(
        (m) => (m.ingredient_name || '').toLowerCase() === name
      );

      if (ingMovements.length === 0) {
        insufficient_data.push({
          ingredient_name: name,
          reason: 'NO_HISTORY',
          observed_days: 0,
        });

        if (usableQty < minStock && minStock > 0) {
          const raw = minStock - usableQty;
          const suggested = Math.ceil(raw / orderStep) * orderStep;
          items.push({
            ingredient_id: `ing-${name}`,
            ingredient_name: name,
            usable_qty: usableQty.toFixed(2),
            unit,
            rule: 'MIN_STOCK_ONLY',
            raw_order_qty: raw.toFixed(2),
            order_step: orderStep.toString(),
            suggested_order_qty: suggested.toFixed(1),
            basis: 'ESTIMATE',
            assumptions: ['Chưa có lịch sử tiêu thụ; đề xuất chỉ căn cứ theo ngưỡng tồn tối thiểu']
          });
        }
        continue;
      }

      // Ngày phát sinh sớm nhất
      const sortedOccurred = ingMovements.map((m) => m.occurred_on).sort();
      const historyStart = sortedOccurred[0];

      // Cửa sổ quan sát kết thúc hôm qua (yesterday)
      const yDate = new Date(yesterday);
      const winStartDateObj = new Date(yDate.getTime() - (winDays - 1) * 86400000);
      const winStartDateStr = toIsoDate(winStartDateObj);
      const windowStart = winStartDateStr > historyStart ? winStartDateStr : historyStart;

      let observedDays = 0;
      if (historyStart <= yesterday) {
        const d1 = new Date(windowStart).getTime();
        const d2 = new Date(yesterday).getTime();
        observedDays = Math.max(0, Math.round((d2 - d1) / 86400000) + 1);
      }

      if (observedDays < minHist) {
        const reason = observedDays === 0 ? 'NO_COMPLETE_DAYS' : 'HISTORY_TOO_SHORT';
        insufficient_data.push({
          ingredient_name: name,
          reason,
          observed_days: observedDays,
        });

        if (usableQty < minStock && minStock > 0) {
          const raw = minStock - usableQty;
          const suggested = Math.ceil(raw / orderStep) * orderStep;
          items.push({
            ingredient_id: `ing-${name}`,
            ingredient_name: name,
            usable_qty: usableQty.toFixed(2),
            unit,
            rule: 'MIN_STOCK_ONLY',
            raw_order_qty: raw.toFixed(2),
            order_step: orderStep.toString(),
            suggested_order_qty: suggested.toFixed(1),
            basis: 'ESTIMATE',
            assumptions: [`Lịch sử quan sát (${observedDays} ngày) < ngưỡng tối thiểu (${minHist} ngày); đề xuất theo tồn tối thiểu`]
          });
        }
        continue;
      }

      // Tiêu thụ trong cửa sổ quan sát
      const windowConsMovements = ingMovements.filter((m) => {
        const isCons = m.type === 'SALE_CONSUMPTION' || m.type === 'USAGE_CONSUMPTION';
        return isCons && m.occurred_on >= windowStart && m.occurred_on <= yesterday;
      });

      const consumptionTotal = windowConsMovements.reduce(
        (sum, m) => sum + Math.abs(parseFloat(m.qty_delta)),
        0
      );
      const avgDaily = observedDays > 0 ? consumptionTotal / observedDays : 0;

      if (avgDaily > 0) {
        const daysOfCover = usableQty / avgDaily;
        const rawCov = Math.max(0, covDays * avgDaily - usableQty);
        const rawMin = Math.max(0, minStock - usableQty);

        const underCov = daysOfCover < covDays;
        const underMin = usableQty < minStock;

        if (underCov || underMin) {
          const rawOrder = Math.max(rawCov, rawMin);
          const suggested = Math.ceil(rawOrder / orderStep) * orderStep;
          const rule: 'COVERAGE' | 'MIN_STOCK_ONLY' | 'BOTH' =
            underCov && underMin ? 'BOTH' : underCov ? 'COVERAGE' : 'MIN_STOCK_ONLY';

          items.push({
            ingredient_id: `ing-${name}`,
            ingredient_name: name,
            usable_qty: usableQty.toFixed(2),
            unit,
            avg_daily_consumption: avgDaily.toFixed(2),
            days_of_cover: daysOfCover.toFixed(1),
            rule,
            raw_order_qty: rawOrder.toFixed(2),
            order_step: orderStep.toString(),
            suggested_order_qty: suggested.toFixed(1),
            basis: 'ESTIMATE',
            assumptions: [
              `Tiêu thụ bình quân: ${avgDaily.toFixed(2)} ${unit}/ngày trong ${observedDays} ngày quan sát`,
              `Tồn khả dụng đủ dùng ~${daysOfCover.toFixed(1)} ngày (mục tiêu: ${covDays} ngày)`
            ]
          });
        }
      } else {
        // avgDaily === 0
        if (usableQty < minStock && minStock > 0) {
          const raw = minStock - usableQty;
          const suggested = Math.ceil(raw / orderStep) * orderStep;
          items.push({
            ingredient_id: `ing-${name}`,
            ingredient_name: name,
            usable_qty: usableQty.toFixed(2),
            unit,
            avg_daily_consumption: '0.00',
            days_of_cover: null,
            rule: 'MIN_STOCK_ONLY',
            raw_order_qty: raw.toFixed(2),
            order_step: orderStep.toString(),
            suggested_order_qty: suggested.toFixed(1),
            basis: 'ESTIMATE',
            assumptions: ['Không có tiêu thụ trong kỳ quan sát; đề xuất theo tồn tối thiểu']
          });
        } else {
          no_recent_consumption.push({
            ingredient_name: name,
            usable_qty: usableQty.toFixed(2),
            unit
          });
        }
      }
    }

    return {
      as_of: today,
      parameters: {
        target_coverage_days: covDays,
        consumption_window_days: winDays,
        min_history_days: minHist,
        expired_batches_consumable: allowExpired
      },
      items,
      insufficient_data,
      no_recent_consumption
    };
  }

  // ==========================================
  // FACT-BASED GROUNDED ASSISTANT CHAT
  // ==========================================

  async askAIGrounded(
    question: string,
    history?: ChatTurn[]
  ): Promise<AssistantMessageResponse> {
    const today = offsetDays(0);

    // Thu thập dữ liệu thực tế (Facts Grounding)
    const batches = this.state.batches.filter((b) => parseFloat(b.remaining_qty) > 0.0001);
    const totalBatches = batches.length;
    const totalStockValue = batches.reduce(
      (sum, b) => sum + Math.round(parseFloat(b.remaining_qty) * parseFloat(b.unit_cost)),
      0
    );

    const expiringSoonBatches = batches.filter((b) => {
      const d = calculateDaysLeft(b.expiry_date);
      return d >= 0 && d <= 3;
    });

    const expiredBatches = batches.filter((b) => {
      const d = calculateDaysLeft(b.expiry_date);
      return d < 0;
    });

    const openShortages = this.state.shortages.filter((s) => s.status === 'OPEN');
    const replenishment = this.getD25ReplenishmentSuggestions();
    const dishRanks = this.getDishRank();

    const contextFacts = {
      today,
      total_batches: totalBatches,
      total_stock_value_vnd: totalStockValue,
      expiring_soon_count: expiringSoonBatches.length,
      expiring_soon_items: expiringSoonBatches.map((b) => ({
        id: b.id,
        name: b.ingredient_name,
        remaining_qty: b.remaining_qty,
        unit: b.unit,
        days_left: calculateDaysLeft(b.expiry_date)
      })),
      expired_count: expiredBatches.length,
      expired_items: expiredBatches.map((b) => ({
        id: b.id,
        name: b.ingredient_name,
        remaining_qty: b.remaining_qty,
        unit: b.unit
      })),
      open_shortages_count: openShortages.length,
      replenishment_suggestions_d25: replenishment.items.map((r) => ({
        ingredient_name: r.ingredient_name,
        usable_qty: r.usable_qty,
        unit: r.unit,
        suggested_order_qty: r.suggested_order_qty,
        rule: r.rule,
        days_of_cover: r.days_of_cover
      })),
      dish_profitability_top: dishRanks.slice(0, 3).map((d) => ({
        name: d.dish.name,
        gross_margin: d.grossMargin,
        margin_percent: d.marginPercent,
        max_portions: d.maxPortions
      }))
    };

    const facts: VerifiedFact[] = [
      {
        id: `F-VAL-${Math.random().toString(36).substring(2, 7)}`,
        tool: 'get_stock_overview',
        label: 'Tổng giá trị tồn kho',
        value: formatMoney(totalStockValue),
        unit: 'VND',
        as_of: today
      },
      {
        id: `F-BATCH-${Math.random().toString(36).substring(2, 7)}`,
        tool: 'get_stock_overview',
        label: 'Số đợt hàng còn tồn',
        value: totalBatches.toString(),
        unit: 'đợt',
        as_of: today
      }
    ];

    if (expiredBatches.length > 0) {
      facts.push({
        id: `F-EXP-${Math.random().toString(36).substring(2, 7)}`,
        tool: 'list_expiring',
        label: 'Số lô đã quá hạn',
        value: expiredBatches.length.toString(),
        unit: 'đợt',
        as_of: today
      });
    }

    if (expiringSoonBatches.length > 0) {
      facts.push({
        id: `F-SOON-${Math.random().toString(36).substring(2, 7)}`,
        tool: 'list_expiring',
        label: 'Số lô cận date (≤ 3 ngày)',
        value: expiringSoonBatches.length.toString(),
        unit: 'đợt',
        as_of: today
      });
    }

    if (replenishment.items.length > 0) {
      facts.push({
        id: `F-REPL-${Math.random().toString(36).substring(2, 7)}`,
        tool: 'get_d25_replenishment',
        label: 'Mặt hàng cần đặt theo D25',
        value: replenishment.items.length.toString(),
        unit: 'mặt hàng',
        as_of: today
      });
    }

    const recommendations: RecommendationItem[] = [];
    const data_gaps: string[] = [];
    const proposed_actions: ProposedAction[] = [];

    const n = normalizeStr(question);

    if (/xu li|xu ly|hom nay|sap het|can date|qua han/.test(n)) {
      if (expiringSoonBatches.length > 0) {
        recommendations.push({
          text: `Ưu tiên đưa các lô cận date (${expiringSoonBatches.map((b) => b.ingredient_name).join(', ')}) vào thực đơn chế biến hôm nay hoặc quyên góp / bán thu mua.`,
          assumptions: ['Thời hạn cảm quan thực phẩm còn tốt và chưa đổi mùi vị'],
          basis: 'VERIFIED_FACT'
        });
        for (const b of expiringSoonBatches.slice(0, 2)) {
          proposed_actions.push({
            type: 'OPEN_EXPIRING_BATCH',
            target_id: b.id,
            label: `Xử lý lô ${capitalize(b.ingredient_name)} (${b.id})`
          });
        }
      }
      if (expiredBatches.length > 0) {
        recommendations.push({
          text: `Có ${expiredBatches.length} lô quá hạn cần lập biên bản hủy / bỏ để đảm bảo an toàn thực phẩm.`,
          assumptions: ['Lô đã qua ngày hết hạn in trên nhãn'],
          basis: 'VERIFIED_FACT'
        });
      }
    }

    if (/dat hang|bo sung|nhap|d25|thieu/.test(n)) {
      if (replenishment.items.length > 0) {
        recommendations.push({
          text: `Đề xuất đặt bổ sung ${replenishment.items.length} mặt hàng để duy trì đủ tồn kho mục tiêu (${replenishment.parameters.target_coverage_days} ngày).`,
          assumptions: ['Tốc độ tiêu thụ dự kiến duy trì ổn định tương đương chu kỳ quan sát'],
          basis: 'ESTIMATE'
        });
        proposed_actions.push({
          type: 'OPEN_REPLENISHMENT',
          target_id: null,
          label: 'Mở danh sách đề xuất đặt hàng D25'
        });
      }
      if (replenishment.insufficient_data.length > 0) {
        data_gaps.push(
          `Có ${replenishment.insufficient_data.length} mặt hàng (${replenishment.insufficient_data.slice(0, 3).map((x) => x.ingredient_name).join(', ')}) chưa đủ ${replenishment.parameters.min_history_days} ngày lịch sử quan sát; chỉ có thể đề xuất theo mức tồn tối thiểu.`
        );
      }
    }

    if (/thieu hut|shortage|option c/.test(n) || (openShortages.length > 0 && /thieu/.test(n))) {
      if (openShortages.length > 0) {
        recommendations.push({
          text: `Đang có ${openShortages.length} trường hợp thiếu hụt Option C mở. Cần nhập hàng bù hoặc xử lý ghi nhận chi phí ước tính / miễn trừ.`,
          assumptions: ['Hàng bán đã phục vụ khách nhưng kho chưa kịp nhập chứng từ thực tế'],
          basis: 'VERIFIED_FACT'
        });
        proposed_actions.push({
          type: 'OPEN_SHORTAGE',
          target_id: openShortages[0].id,
          label: 'Xem danh sách thiếu hụt Option C'
        });
      }
    }

    // Proxy call to server
    let answerText = '';
    let provider: 'rule_based' | 'external' = 'rule_based';

    try {
      const response = await fetch('/api/assistant/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: question,
          history: history || [],
          contextFacts
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.answer_text && data.answer_text.trim()) {
          answerText = data.answer_text.trim();
          provider = 'external';
        }
      }
    } catch (_err) {
      // Offline fallback
    }

    if (!answerText) {
      answerText = this.askAI(question);
    }

    return {
      answer_text: answerText,
      facts,
      recommendations,
      data_gaps,
      proposed_actions,
      provider,
      request_id: `REQ-${Math.random().toString(36).substring(2, 9)}`
    };
  }

  // ==========================================
  // VIEW 4: THỐNG KÊ (ReportsView)
  // ==========================================

  private computePeriodStats(range?: { from: string; to: string }): PeriodStatsResult {
    const s: PeriodStatsResult = {
      portions: 0,
      saleRev: 0,
      saleCost: 0,
      useCost: 0,
      sellRev: 0,
      sellCost: 0,
      sellN: 0,
      donate: 0,
      donateN: 0,
      waste: 0,
      wasteN: 0,
      adjust: 0,
      inV: 0,
      repRev: 0,
      repCost: 0,
      repN: 0,
      rev: 0,
      cogs: 0,
      profit: 0,
      out: 0,
    };

    const inRange = (d: string) => !range || (d >= range.from && d <= range.to);

    this.state.logs.forEach((l) => {
      if (!inRange(l.date)) return;
      if (l.type === 'in') {
        s.inV += l.value || 0;
      } else if (l.type === 'sale') {
        s.portions += l.portions || 0;
        s.saleRev += l.revenue || 0;
        s.saleCost += l.cost || 0;
        if (l.src === 'repurpose') {
          s.repRev += l.revenue || 0;
          s.repCost += l.cost || 0;
          s.repN += l.portions || 0;
        }
      } else if (l.type === 'use') {
        s.useCost += l.cost || 0;
      } else if (l.type === 'sell') {
        s.sellRev += l.revenue || 0;
        s.sellCost += l.cost || 0;
        s.sellN++;
      } else if (l.type === 'donate') {
        s.donate += l.cost || 0;
        s.donateN++;
      } else if (l.type === 'waste') {
        s.waste += l.cost || 0;
        s.wasteN++;
      } else if (l.type === 'adjust') {
        s.adjust += l.cost || 0;
      }
    });

    s.rev = s.saleRev + s.sellRev;
    s.cogs = s.saleCost + s.useCost + s.sellCost;
    s.profit = s.rev - s.cogs - s.donate - s.waste - s.adjust;
    s.out = s.cogs + s.donate + s.waste + s.adjust;
    return s;
  }

  private getWasteGroups(range?: { from: string; to: string }) {
    const map = new Map<string, { name: string; qty: number; cost: number; count: number; reasons: Record<string, number> }>();
    const inRange = (d: string) => !range || (d >= range.from && d <= range.to);

    this.state.logs.forEach((l) => {
      if (l.type !== 'waste' || !inRange(l.date) || !l.name) return;
      const key = l.name.toLowerCase();
      const existing = map.get(key) || { name: l.name, qty: 0, cost: 0, count: 0, reasons: {} };
      existing.qty += l.qty || 0;
      existing.cost += l.cost || 0;
      existing.count++;
      const reason = l.reason || 'Khác';
      existing.reasons[reason] = (existing.reasons[reason] || 0) + 1;
      map.set(key, existing);
    });

    return Array.from(map.values()).sort((a, b) => b.cost - a.cost);
  }

  getReportStats(
    periodType: 'day' | 'month' | 'quarter' | 'range',
    dayValue: string,
    monthValue: string,
    quarterValue: string,
    fromValue: string,
    toValue: string
  ): PeriodReportFull {
    const today = offsetDays(0);
    let from = '';
    let to = '';
    let label = '';
    let bname = '';
    let prevFrom = '';
    let prevTo = '';
    let prevLabel = '';
    const buckets: Array<{ label: string; from: string; to: string; isSelected?: boolean }> = [];

    if (periodType === 'day') {
      from = to = dayValue;
      label = `Ngày ${dayValue.split('-').reverse().join('/')}`;
      prevFrom = prevTo = offsetDays(-1);
      prevLabel = 'hôm trước';
      bname = '7 ngày gần nhất tính đến ngày này';

      const baseDate = new Date(dayValue);
      for (let i = 6; i >= 0; i--) {
        const d = new Date(baseDate);
        d.setDate(d.getDate() - i);
        const iso = toIsoDate(d);
        buckets.push({
          label: `${pad(d.getDate())}/${pad(d.getMonth() + 1)}`,
          from: iso,
          to: iso,
          isSelected: i === 0,
        });
      }
    } else if (periodType === 'month') {
      const [yStr, mStr] = monthValue.split('-');
      const y = parseInt(yStr, 10);
      const m = parseInt(mStr, 10);
      from = `${y}-${pad(m)}-01`;
      const lastDay = new Date(y, m, 0).getDate();
      to = `${y}-${pad(m)}-${pad(lastDay)}`;
      label = `Tháng ${m}/${y}`;
      bname = 'từng tuần trong tháng';

      const prevYear = m === 1 ? y - 1 : y;
      const prevMonth = m === 1 ? 12 : m - 1;
      const prevLastDay = new Date(prevYear, prevMonth, 0).getDate();
      prevFrom = `${prevYear}-${pad(prevMonth)}-01`;
      prevTo = `${prevYear}-${pad(prevMonth)}-${pad(prevLastDay)}`;
      prevLabel = 'tháng trước';

      [1, 8, 15, 22, 29].forEach((st) => {
        if (st > lastDay) return;
        const e = Math.min(st + 6, lastDay);
        buckets.push({
          label: `Ngày ${st}–${e}`,
          from: `${y}-${pad(m)}-${pad(st)}`,
          to: `${y}-${pad(m)}-${pad(e)}`,
        });
      });
    } else if (periodType === 'quarter') {
      const [yStr, qStr] = quarterValue.split('-');
      const y = parseInt(yStr, 10);
      const q = parseInt(qStr, 10);
      const m1 = (q - 1) * 3 + 1;
      from = `${y}-${pad(m1)}-01`;
      const lastMonth = m1 + 2;
      const lastDay = new Date(y, lastMonth, 0).getDate();
      to = `${y}-${pad(lastMonth)}-${pad(lastDay)}`;
      label = `Quý ${q}/${y} (tháng ${m1}–${lastMonth})`;
      bname = 'từng tháng trong quý';

      const pq = q === 1 ? 4 : q - 1;
      const pqy = q === 1 ? y - 1 : y;
      const pm1 = (pq - 1) * 3 + 1;
      const plastMonth = pm1 + 2;
      const plastDay = new Date(pqy, plastMonth, 0).getDate();
      prevFrom = `${pqy}-${pad(pm1)}-01`;
      prevTo = `${pqy}-${pad(plastMonth)}-${pad(plastDay)}`;
      prevLabel = 'quý trước';

      for (let i = 0; i < 3; i++) {
        const mon = m1 + i;
        const lDay = new Date(y, mon, 0).getDate();
        buckets.push({
          label: `Tháng ${mon}`,
          from: `${y}-${pad(mon)}-01`,
          to: `${y}-${pad(mon)}-${pad(lDay)}`,
        });
      }
    } else {
      let f = fromValue;
      let t = toValue;
      if (f > t) {
        const temp = f;
        f = t;
        t = temp;
      }
      from = f;
      to = t;
      const diffDays = Math.round((new Date(t).getTime() - new Date(f).getTime()) / 86400000) + 1;
      label = `Đợt từ ${f.split('-').reverse().join('/')} đến ${t.split('-').reverse().join('/')} (${diffDays} ngày)`;
      bname = diffDays <= 14 ? 'từng ngày' : 'từng 7 ngày';

      const prevStart = new Date(f);
      prevStart.setDate(prevStart.getDate() - diffDays);
      const prevEnd = new Date(f);
      prevEnd.setDate(prevEnd.getDate() - 1);
      prevFrom = toIsoDate(prevStart);
      prevTo = toIsoDate(prevEnd);
      prevLabel = 'đợt liền trước cùng độ dài';

      if (diffDays <= 14) {
        for (let i = 0; i < diffDays; i++) {
          const d = new Date(f);
          d.setDate(d.getDate() + i);
          const iso = toIsoDate(d);
          buckets.push({
            label: `${pad(d.getDate())}/${pad(d.getMonth() + 1)}`,
            from: iso,
            to: iso,
          });
        }
      } else {
        for (let i = 0; i < diffDays; i += 7) {
          const dA = new Date(f);
          dA.setDate(dA.getDate() + i);
          const dB = new Date(f);
          dB.setDate(dB.getDate() + Math.min(i + 6, diffDays - 1));
          buckets.push({
            label: `${pad(dA.getDate())}/${pad(dA.getMonth() + 1)}–${pad(dB.getDate())}/${pad(dB.getMonth() + 1)}`,
            from: toIsoDate(dA),
            to: toIsoDate(dB),
          });
        }
      }
    }

    const currentStats = this.computePeriodStats({ from, to });
    const previousStats = this.computePeriodStats({ from: prevFrom, to: prevTo });
    const isPartial = to > today && (periodType === 'month' || periodType === 'quarter');

    // So sánh chênh lệch
    const delta = (cur: number, prev: number, targetLabel: string) => {
      if (!prev) return cur ? `Chưa có số liệu ${targetLabel}` : '—';
      const pc = Math.round(((cur - prev) / Math.abs(prev)) * 100);
      return (pc >= 0 ? 'Tăng ' : 'Giảm ') + Math.abs(pc) + `% so với ${targetLabel}`;
    };

    const deltaRevText = isPartial ? 'Kỳ chưa kết thúc, chưa so sánh' : delta(currentStats.rev, previousStats.rev, prevLabel);
    const deltaProfitText = isPartial ? 'Kỳ chưa kết thúc, chưa so sánh' : delta(currentStats.profit, previousStats.profit, prevLabel);

    // Tính doanh thu lớn nhất để vẽ bar chart
    let maxBucketRev = 0;
    const computedBuckets = buckets.map((b) => {
      const bStats = this.computePeriodStats({ from: b.from, to: b.to });
      if (bStats.rev > maxBucketRev) maxBucketRev = bStats.rev;
      return {
        ...b,
        stats: bStats,
        revenuePercent: 0,
      };
    });

    computedBuckets.forEach((b) => {
      b.revenuePercent = maxBucketRev > 0 ? Math.round((b.stats.rev / maxBucketRev) * 100) : 0;
    });

    // Món bán trong kỳ
    const dishMap = new Map<string, { name: string; portions: number; revenue: number; cost: number; profit: number }>();
    this.state.logs.forEach((l) => {
      if (l.type !== 'sale' || l.date < from || l.date > to || !l.dish) return;
      const existing = dishMap.get(l.dish) || { name: l.dish, portions: 0, revenue: 0, cost: 0, profit: 0 };
      existing.portions += l.portions || 0;
      existing.revenue += l.revenue || 0;
      existing.cost += l.cost || 0;
      existing.profit = existing.revenue - existing.cost;
      dishMap.set(l.dish, existing);
    });
    const dishSales = Array.from(dishMap.values()).sort((a, b) => b.profit - a.profit);

    // Logs đã xử lý (quyên góp, bán thu mua, làm món mới)
    const repurposedLogs = this.state.logs
      .filter((l) => l.date >= from && l.date <= to && (l.type === 'donate' || l.type === 'sell' || (l.type === 'sale' && l.src === 'repurpose')))
      .slice()
      .reverse();

    // Logs đã bỏ
    const wasteByReason: Record<string, number> = {};
    const wasteLogs = this.state.logs
      .filter((l) => l.type === 'waste' && l.date >= from && l.date <= to)
      .slice()
      .reverse();

    wasteLogs.forEach((l) => {
      const r = l.reason || 'Khác';
      wasteByReason[r] = (wasteByReason[r] || 0) + (l.cost || 0);
    });

    const wasteByIngredient = this.getWasteGroups({ from, to });

    // AI Period Review logic matching demogiaodien.html
    let aiReview: AIPeriodReview | null = null;
    if (currentStats.rev > 0 || currentStats.out > 0) {
      const summary: string[] = [];
      const causes: string[] = [];
      const anomalies: string[] = [];
      const actions: string[] = [];

      const margin = currentStats.rev ? Math.round((currentStats.profit / currentStats.rev) * 100) : 0;
      summary.push(`${label}: doanh thu ${formatMoney(currentStats.rev)}, lợi nhuận ${formatMoney(currentStats.profit)} (biên ${margin}%).`);

      if (isPartial) {
        summary.push(`Kỳ này chưa kết thúc (mới đến ${today.split('-').reverse().slice(0, 2).join('/')}), nên chưa so sánh công bằng với ${prevLabel}.`);
        if (previousStats.rev > 0) {
          summary.push(`Tính đến hôm nay, doanh thu đã bằng ${Math.round((currentStats.rev / previousStats.rev) * 100)}% cả ${prevLabel} (${formatMoney(previousStats.rev)}).`);
        }
      } else if (previousStats.rev > 0) {
        const dr = Math.round(((currentStats.rev - previousStats.rev) / previousStats.rev) * 100);
        const dp = previousStats.profit ? Math.round(((currentStats.profit - previousStats.profit) / Math.abs(previousStats.profit)) * 100) : 0;
        if (dr >= 0 && dp >= 0) {
          summary.push(`Tốt hơn ${prevLabel}: doanh thu tăng ${dr}%, lợi nhuận tăng ${dp}%${dp < dr ? ' (lợi nhuận tăng chậm hơn doanh thu)' : ''}.`);
        } else if (dr >= 0) {
          summary.push(`Doanh thu tăng ${dr}% nhưng lợi nhuận giảm ${Math.abs(dp)}%: chi phí đang tăng nhanh hơn phần thu.`);
        } else if (dp >= 0) {
          summary.push(`Doanh thu giảm ${Math.abs(dr)}% nhưng lợi nhuận tăng ${dp}%: bán hiệu quả hơn hoặc ít hao hụt hơn.`);
        } else {
          summary.push(`Doanh thu giảm ${Math.abs(dr)}% và lợi nhuận giảm ${Math.abs(dp)}% so với ${prevLabel}.`);
        }
      }

      // Causes
      const cr = currentStats.rev ? currentStats.cogs / currentStats.rev : 0;
      const pcr = previousStats.rev ? previousStats.cogs / previousStats.rev : 0;
      if (Math.abs(cr - pcr) >= 0.03 && pcr > 0) {
        causes.push(`Giá vốn chiếm ${Math.round(cr * 100)}% doanh thu (kỳ trước ${Math.round(pcr * 100)}%), ${cr > pcr ? 'cao hơn nên ăn vào lợi nhuận.' : 'thấp hơn nên giúp lợi nhuận tốt hơn.'}`);
      }

      if (currentStats.waste > 0 && wasteByIngredient.length) {
        const topW = wasteByIngredient[0];
        causes.push(`Hao hụt ${formatMoney(currentStats.waste)}${currentStats.rev ? ` (${Math.round((currentStats.waste / currentStats.rev) * 100)}% doanh thu)` : ''}. Nhiều nhất là ${topW.name} (${formatMoney(topW.cost)}).`);
      }

      if (dishSales.length > 0) {
        const topDish = dishSales[0];
        const totalDishRev = dishSales.reduce((sum, d) => sum + d.revenue, 0);
        if (totalDishRev > 0 && topDish.revenue / totalDishRev >= 0.3) {
          causes.push(`Món ${topDish.name} đóng góp ${Math.round((topDish.revenue / totalDishRev) * 100)}% doanh thu, nên doanh thu phụ thuộc khá nhiều vào món này.`);
        }
      }

      if (currentStats.adjust > 0) {
        causes.push(`Kiểm kho lệch ${formatMoney(currentStats.adjust)} (hao hụt chưa rõ nguyên nhân).`);
      }

      if (!causes.length) {
        causes.push(`Chưa thấy yếu tố chi phí nào thay đổi đột biến so với ${prevLabel}.`);
      }

      // Anomalies
      dishSales.forEach((d) => {
        if (d.profit < 0) {
          anomalies.push(`Món ${d.name} đang lỗ ${formatMoney(-d.profit)}.`);
        } else if (d.revenue > 0 && d.profit / d.revenue < 0.3 && d.portions >= 5) {
          anomalies.push(`Món ${d.name} có biên lãi chỉ ${Math.round((d.profit / d.revenue) * 100)}%, thấp hơn bình quân.`);
        }
      });

      // Actions
      if (wasteByIngredient.length) {
        const topItem = wasteByIngredient[0];
        const master = MASTER_PRODUCTS[topItem.name];
        actions.push(`Lần nhập tới: giữ ${topItem.name}${master?.usual_quantity ? ` ở mức ${master.usual_quantity[0]}–${master.usual_quantity[1]} ${master.unit}` : ' ít hơn lần trước'}${master && master.shelf_life_days <= 4 ? ' và chia 2 lần mỗi tuần vì hạn dùng ngắn' : ''}.`);
      }

      const lowMarginDish = dishSales.filter((d) => d.revenue > 0 && d.profit / d.revenue < 0.3 && d.portions >= 5).sort((a, b) => a.profit / a.revenue - b.profit / b.revenue)[0];
      if (lowMarginDish) {
        actions.push(`Xem lại giá bán ${lowMarginDish.name}: điều chỉnh giá hoặc định lượng để đạt biên lãi tối thiểu 40%.`);
      }

      const highMarginDish = dishSales.filter((d) => d.portions >= 5 && d.profit / d.revenue >= 0.5).sort((a, b) => b.profit / b.revenue - a.profit / a.revenue)[0];
      if (highMarginDish) {
        actions.push(`Đẩy mạnh món có biên lợi nhuận cao: ${highMarginDish.name} (biên ${Math.round((highMarginDish.profit / highMarginDish.revenue) * 100)}%), đưa lên vị trí nổi bật.`);
      }

      const expSoonCount = this.state.batches.filter((b) => {
        const d = calculateDaysLeft(b.expiry_date);
        return d >= 0 && d <= 2 && parseFloat(b.remaining_qty) > 0.0001;
      }).length;
      if (expSoonCount > 0) {
        actions.push(`Hiện có ${expSoonCount} đợt sắp hết hạn trong kho: xử lí ngay ở Trợ lý AI (mục Gợi ý) để tránh hao hụt.`);
      }

      if (!actions.length) {
        actions.push('Chưa có việc cấp bách. Duy trì nhịp nhập kho và kiểm kê hiện tại.');
      }

      aiReview = { summary, causes, anomalies, actions };
    }

    return {
      label,
      bname,
      from,
      to,
      current: currentStats,
      previous: {
        label: prevLabel,
        stats: previousStats,
      },
      isPartial,
      deltaRevText,
      deltaProfitText,
      buckets: computedBuckets,
      aiReview,
      dishSales,
      repurposedLogs,
      wasteByReason,
      wasteByIngredient,
      wasteLogs,
    };
  }

  // ==========================================
  // THÔNG BÁO (Notifications)
  // ==========================================

  getUnreadNotificationsCount(): number {
    let unread = 0;
    const reads = this.state.notification_reads;
    this.state.batches.forEach((b) => {
      const d = calculateDaysLeft(b.expiry_date);
      if (parseFloat(b.remaining_qty) > 0.0001) {
        if (d < 0 && !reads[`expired-${b.id}`]) unread++;
        else if (d <= 2 && !reads[`soon-${b.id}`]) unread++;
      }
    });
    // Add open shortages to unread count
    this.state.shortages.forEach((s) => {
      if (s.status === 'OPEN' && !reads[`shortage-${s.id}`]) {
        unread++;
      }
    });
    return unread;
  }

  getNotificationsList() {
    const list: Array<{
      id: string;
      key: string;
      title: string;
      message: string;
      date: string;
      type: 'expired' | 'soon' | 'shortage';
      severity: 'bad' | 'warn' | 'ok';
      read: boolean;
      batchId?: string;
      shortageId?: string;
      ingredientName?: string;
      qtyText?: string;
    }> = [];

    const reads = this.state.notification_reads;

    // 1. Quá hạn
    this.state.batches.forEach((b) => {
      if (parseFloat(b.remaining_qty) <= 0.0001) return;
      const d = calculateDaysLeft(b.expiry_date);
      if (d < 0) {
        const key = `expired-${b.id}`;
        list.push({
          id: key,
          key,
          title: `Lô đã quá hạn: ${capitalize(b.ingredient_name)}`,
          message: `Còn tồn ${formatQty(parseFloat(b.remaining_qty))} ${b.unit} (${STORAGE_LOCATIONS[b.location] || b.location}). Quá hạn ${Math.abs(d)} ngày (${b.expiry_date?.slice(5)}). Cần xử lý bỏ hoặc hủy để tránh mất an toàn thực phẩm.`,
          date: b.expiry_date || offsetDays(0),
          type: 'expired',
          severity: 'bad',
          read: !!reads[key],
          batchId: b.id,
          ingredientName: b.ingredient_name,
          qtyText: `${formatQty(parseFloat(b.remaining_qty))} ${b.unit}`,
        });
      } else if (d <= 2) {
        const key = `soon-${b.id}`;
        list.push({
          id: key,
          key,
          title: `Sắp hết hạn: ${capitalize(b.ingredient_name)}`,
          message: `Còn tồn ${formatQty(parseFloat(b.remaining_qty))} ${b.unit}. Hạn dùng ${d === 0 ? 'hôm nay' : `còn ${d} ngày`} (${b.expiry_date?.slice(5)}). Ưu tiên nấu món hoặc thanh lý/quyên góp.`,
          date: b.expiry_date || offsetDays(0),
          type: 'soon',
          severity: 'warn',
          read: !!reads[key],
          batchId: b.id,
          ingredientName: b.ingredient_name,
          qtyText: `${formatQty(parseFloat(b.remaining_qty))} ${b.unit}`,
        });
      }
    });

    // 2. Thiếu hụt Option C
    this.state.shortages.forEach((s) => {
      const key = `shortage-${s.id}`;
      list.push({
        id: key,
        key,
        title: s.status === 'OPEN' ? `Thiếu hụt tồn kho: ${capitalize(s.ingredient_name)}` : `Đã giải quyết thiếu hụt: ${capitalize(s.ingredient_name)}`,
        message: s.status === 'OPEN'
          ? `Đơn bán món "${s.dish_name || 'Món'}" thiếu ${formatQty(parseFloat(s.short_qty))} ${s.unit} ${s.ingredient_name}. Đang ghi nhận Option C (chờ bù hàng, ghi nhận chi phí ước tính hoặc miễn trừ).`
          : `Thiếu ${formatQty(parseFloat(s.short_qty))} ${s.unit} đã xử lý theo phương án ${s.resolution === 'CONSUMED_FROM_STOCK' ? 'Trừ bù từ kho' : s.resolution === 'WRITTEN_OFF_ESTIMATED' ? 'Ghi nhận chi phí ước tính' : 'Miễn trừ'}.`,
        date: s.business_date,
        type: 'shortage',
        severity: s.status === 'OPEN' ? 'warn' : 'ok',
        read: !!reads[key] || s.status !== 'OPEN',
        shortageId: s.id,
        ingredientName: s.ingredient_name,
        qtyText: `${formatQty(parseFloat(s.short_qty))} ${s.unit}`,
      });
    });

    // Sort: unread first, then by date desc
    return list.sort((a, b) => {
      if (a.read !== b.read) return a.read ? 1 : -1;
      return b.date.localeCompare(a.date);
    });
  }

  markNotificationRead(key: string) {
    this.state.notification_reads[key] = true;
    this.saveState();
  }

  markAllNotificationsRead() {
    this.state.batches.forEach((b) => {
      this.state.notification_reads[`expired-${b.id}`] = true;
      this.state.notification_reads[`soon-${b.id}`] = true;
    });
    this.state.shortages.forEach((s) => {
      this.state.notification_reads[`shortage-${s.id}`] = true;
    });
    this.saveState();
  }

  // ==========================================
  // OPERATIONAL ENGINE: BATCHES & INVENTORY
  // ==========================================

  getBatchById(batchId: string): Batch | undefined {
    return this.state.batches.find((b) => b.id === batchId);
  }

  getDishById(dishId: string): Dish | undefined {
    return this.state.dishes.find((d) => d.id === dishId);
  }

  getBatchMovements(batchId: string): StockMovement[] {
    return this.state.movements.filter((m) => m.batch_id === batchId);
  }

  getProductMovements(productName: string): StockMovement[] {
    const nameLow = productName.toLowerCase();
    return this.state.movements.filter(
      (m) => m.ingredient_name.toLowerCase() === nameLow
    ).slice().reverse();
  }

  getShortages(statusFilter?: 'OPEN' | 'RESOLVED'): StockShortage[] {
    if (!statusFilter) return this.state.shortages;
    return this.state.shortages.filter((s) => s.status === statusFilter);
  }

  addBatchManual(data: {
    name: string;
    qty: number;
    unit?: string;
    cost: number;
    location: StorageLocation;
    received_on?: string;
    expiry_date?: string;
  }): Batch {
    if (data.qty <= 0) throw new Error('Số lượng nhập phải lớn hơn 0');
    if (data.cost < 0) throw new Error('Đơn giá không được âm');

    const name = data.name.trim().toLowerCase();
    const unit = data.unit || MASTER_PRODUCTS[name]?.unit || 'kg';
    const recOn = data.received_on || offsetDays(0);
    const expDate = data.expiry_date || offsetDays(7);
    const bId = `batch-${this.state.uid++}`;
    const dLeft = calculateDaysLeft(expDate);
    const val = Math.round(data.qty * data.cost);

    const newBatch: Batch = {
      id: bId,
      ingredient_id: `ing-${name}`,
      ingredient_name: name,
      received_on: recOn,
      expiry_date: expDate,
      initial_qty: data.qty.toFixed(3),
      remaining_qty: data.qty.toFixed(3),
      unit,
      unit_cost: data.cost.toFixed(6),
      stock_value_vnd: val,
      location: data.location,
      expiry_status: dLeft < 0 ? 'EXPIRED' : dLeft <= 3 ? 'EXPIRES_SOON' : 'OK',
      days_to_expiry: dLeft,
    };

    this.state.batches.push(newBatch);

    const mId = `m-${this.state.uid++}`;
    this.state.movements.push({
      id: mId,
      occurred_on: recOn,
      type: 'RECEIPT',
      category: 'RECEIPT',
      ingredient_id: `ing-${name}`,
      ingredient_name: name,
      batch_id: bId,
      qty_delta: data.qty.toFixed(3),
      unit,
      unit_cost_snapshot: data.cost.toFixed(6),
      value_vnd: val,
      reference_kind: 'MANUAL_RECEIPT',
      created_at: new Date().toISOString(),
    });

    this.state.logs.push({
      id: this.state.uid++,
      date: recOn,
      type: 'in',
      name,
      qty: data.qty,
      value: val,
      src: 'Nhập thủ công',
    });

    this.saveState();
    return newBatch;
  }

  adjustBatch(
    batchId: string,
    newQty: number,
    reasonCode: string = 'Kiểm kho',
    note?: string
  ): { batch: Batch; delta: number; deltaVal: number } {
    const batch = this.state.batches.find((b) => b.id === batchId);
    if (!batch) throw new Error(`Không tìm thấy lô hàng ${batchId}`);
    if (newQty < 0) throw new Error('Số lượng kiểm kê không được âm');

    const oldQty = parseFloat(batch.remaining_qty);
    const delta = newQty - oldQty;
    const unitCost = parseFloat(batch.unit_cost);
    const deltaVal = Math.round(delta * unitCost);

    batch.remaining_qty = newQty.toFixed(3);
    batch.stock_value_vnd = Math.round(newQty * unitCost);

    if (Math.abs(delta) > 0.0001) {
      const type = delta > 0 ? 'ADJUSTMENT_IN' : 'ADJUSTMENT_OUT';
      this.state.movements.push({
        id: `m-${this.state.uid++}`,
        occurred_on: offsetDays(0),
        type,
        category: 'ADJUSTMENT',
        ingredient_id: batch.ingredient_id,
        ingredient_name: batch.ingredient_name,
        batch_id: batch.id,
        qty_delta: delta.toFixed(3),
        unit: batch.unit,
        unit_cost_snapshot: batch.unit_cost,
        value_vnd: deltaVal,
        reference_kind: 'STOCKTAKE',
        created_at: new Date().toISOString(),
      });

      this.state.logs.push({
        id: this.state.uid++,
        date: offsetDays(0),
        type: 'adjust',
        name: batch.ingredient_name,
        qty: Math.abs(delta),
        cost: Math.abs(deltaVal),
        reason: reasonCode,
        note: note || `Điều chỉnh từ ${formatQty(oldQty)} thành ${formatQty(newQty)}`,
      });
    }

    this.saveState();
    return { batch, delta, deltaVal };
  }

  updateBatchMetadata(
    batchId: string,
    data: {
      location?: StorageLocation;
      expiry_date?: string;
      received_on?: string;
    }
  ): Batch {
    const batch = this.state.batches.find((b) => b.id === batchId);
    if (!batch) throw new Error(`Không tìm thấy lô hàng ${batchId}`);

    if (data.location) batch.location = data.location;
    if (data.received_on) batch.received_on = data.received_on;
    if (data.expiry_date) {
      batch.expiry_date = data.expiry_date;
      const dLeft = calculateDaysLeft(data.expiry_date);
      batch.days_to_expiry = dLeft;
      batch.expiry_status = dLeft < 0 ? 'EXPIRED' : dLeft <= 3 ? 'EXPIRES_SOON' : 'OK';
    }

    this.saveState();
    return batch;
  }

  // ==========================================
  // DISPOSALS: DONATION, SELLOFF, WASTE
  // ==========================================

  processBatchDisposal(
    batchId: string,
    type: 'DONATION' | 'SELLOFF' | 'WASTE',
    qty: number,
    reasonCode?: string,
    note?: string,
    revenueVnd?: number,
    counterparty?: string
  ): { success: boolean; costVnd: number; revenueVnd: number } {
    if (qty <= 0) throw new Error('Số lượng xử lý phải lớn hơn 0');

    const batch = this.state.batches.find((b) => b.id === batchId);
    if (!batch) throw new Error(`Không tìm thấy lô hàng ${batchId}`);

    const avail = parseFloat(batch.remaining_qty);
    if (qty > avail + 0.0001) {
      throw new Error(`Số lượng xử lý (${qty}) vượt quá tồn của lô (${formatQty(avail)})`);
    }

    if (type === 'WASTE') {
      if (!reasonCode) throw new Error('Bỏ hàng bắt buộc phải chọn lý do');
      if (reasonCode === 'OTHER' && (!note || !note.trim())) {
        throw new Error('Lý do khác bắt buộc phải nhập ghi chú giải trình');
      }
    }

    const actualDeduct = Math.min(qty, avail);
    batch.remaining_qty = Math.max(0, avail - actualDeduct).toFixed(3);
    const unitCost = parseFloat(batch.unit_cost);
    batch.stock_value_vnd = Math.round(parseFloat(batch.remaining_qty) * unitCost);

    const costVnd = Math.round(actualDeduct * unitCost);
    const today = offsetDays(0);

    // Movement
    this.state.movements.push({
      id: `m-${this.state.uid++}`,
      occurred_on: today,
      type,
      category: type,
      ingredient_id: batch.ingredient_id,
      ingredient_name: batch.ingredient_name,
      batch_id: batch.id,
      qty_delta: (-actualDeduct).toFixed(3),
      unit: batch.unit,
      unit_cost_snapshot: batch.unit_cost,
      value_vnd: -costVnd,
      reference_kind: type,
      created_at: new Date().toISOString(),
    });

    if (type === 'DONATION') {
      this.state.logs.push({
        id: this.state.uid++,
        date: today,
        type: 'donate',
        name: batch.ingredient_name,
        qty: actualDeduct,
        cost: costVnd,
        note: counterparty ? `Quyên góp cho: ${counterparty}. ${note || ''}` : note,
      });
    } else if (type === 'SELLOFF') {
      const rev = revenueVnd != null && revenueVnd >= 0 ? revenueVnd : Math.round(costVnd * 0.6);
      this.state.logs.push({
        id: this.state.uid++,
        date: today,
        type: 'sell',
        name: batch.ingredient_name,
        qty: actualDeduct,
        cost: costVnd,
        revenue: rev,
        note: counterparty ? `Bán cho: ${counterparty}. ${note || ''}` : note,
      });
    } else {
      // WASTE
      const reasonLabel =
        reasonCode === 'EXPIRED'
          ? 'Hết hạn'
          : reasonCode === 'SPOILED'
          ? 'Hỏng/ôi thiu'
          : reasonCode === 'OVERSTOCK'
          ? 'Nhập dư'
          : note || 'Khác';

      this.state.logs.push({
        id: this.state.uid++,
        date: today,
        type: 'waste',
        name: batch.ingredient_name,
        qty: actualDeduct,
        cost: costVnd,
        reason: reasonLabel,
        note,
      });
    }

    this.saveState();
    return {
      success: true,
      costVnd,
      revenueVnd: type === 'SELLOFF' ? (revenueVnd || 0) : 0,
    };
  }

  // ==========================================
  // COOK ENGINE & OPTION C WITH FEFO
  // ==========================================

  cookDish(
    dishId: string,
    portions: number,
    sourceBatchId?: string
  ): {
    success: boolean;
    dishName: string;
    portions: number;
    totalCost: number;
    hasShortage: boolean;
    shortages: Array<{ ingredient: string; needed: number; available: number; short: number }>;
  } {
    if (portions <= 0) throw new Error('Số phần nấu phải lớn hơn 0');

    const dish = this.state.dishes.find((d) => d.id === dishId);
    if (!dish) throw new Error(`Không tìm thấy món ăn ${dishId}`);

    const isRepurpose = !!sourceBatchId;
    const explicitBatch = sourceBatchId ? this.getBatchById(sourceBatchId) : undefined;
    const today = offsetDays(0);

    let totalCost = 0;
    let hasShortage = false;
    const shortageDetails: Array<{ ingredient: string; needed: number; available: number; short: number }> = [];

    dish.recipe.forEach((item) => {
      const ingName = (item.ingredient_name || '').toLowerCase();
      const needed = parseFloat(item.quantity) * portions;
      let remainingNeed = needed;
      let deductedForIng = 0;

      // 1. If explicit batch matches this ingredient, deduct from it first (3.7)
      if (explicitBatch && explicitBatch.ingredient_name.toLowerCase() === ingName) {
        const availExp = parseFloat(explicitBatch.remaining_qty);
        if (availExp > 0.0001) {
          const deductExp = Math.min(availExp, remainingNeed);
          explicitBatch.remaining_qty = Math.max(0, availExp - deductExp).toFixed(3);
          const uCost = parseFloat(explicitBatch.unit_cost);
          explicitBatch.stock_value_vnd = Math.round(parseFloat(explicitBatch.remaining_qty) * uCost);

          const costLine = Math.round(deductExp * uCost);
          totalCost += costLine;
          deductedForIng += deductExp;
          remainingNeed -= deductExp;

          this.state.movements.push({
            id: `m-${this.state.uid++}`,
            occurred_on: today,
            type: isRepurpose ? 'SALE_CONSUMPTION' : 'USAGE_CONSUMPTION',
            category: isRepurpose ? 'SALE_CONSUMPTION' : 'USAGE_CONSUMPTION',
            ingredient_id: explicitBatch.ingredient_id,
            ingredient_name: explicitBatch.ingredient_name,
            batch_id: explicitBatch.id,
            qty_delta: (-deductExp).toFixed(3),
            unit: explicitBatch.unit,
            unit_cost_snapshot: explicitBatch.unit_cost,
            value_vnd: -costLine,
            reference_kind: 'COOK',
            reference_id: dish.id,
            created_at: new Date().toISOString(),
          });
        }
      }

      // 2. Deduct remaining need through FEFO over usable batches (excluding explicit batch)
      if (remainingNeed > 0.0001) {
        const usableBatches = this.getUsableBatches(ingName).filter(
          (b) => !explicitBatch || b.id !== explicitBatch.id
        );

        for (const b of usableBatches) {
          if (remainingNeed <= 0.0001) break;
          const avail = parseFloat(b.remaining_qty);
          if (avail <= 0.0001) continue;

          const deductAmount = Math.min(avail, remainingNeed);
          b.remaining_qty = Math.max(0, avail - deductAmount).toFixed(3);
          const uCost = parseFloat(b.unit_cost);
          b.stock_value_vnd = Math.round(parseFloat(b.remaining_qty) * uCost);

          const costLine = Math.round(deductAmount * uCost);
          totalCost += costLine;
          deductedForIng += deductAmount;
          remainingNeed -= deductAmount;

          this.state.movements.push({
            id: `m-${this.state.uid++}`,
            occurred_on: today,
            type: isRepurpose ? 'SALE_CONSUMPTION' : 'USAGE_CONSUMPTION',
            category: isRepurpose ? 'SALE_CONSUMPTION' : 'USAGE_CONSUMPTION',
            ingredient_id: b.ingredient_id,
            ingredient_name: b.ingredient_name,
            batch_id: b.id,
            qty_delta: (-deductAmount).toFixed(3),
            unit: b.unit,
            unit_cost_snapshot: b.unit_cost,
            value_vnd: -costLine,
            reference_kind: 'COOK',
            reference_id: dish.id,
            created_at: new Date().toISOString(),
          });
        }
      }

      // 3. Option C: If remaining need > 0, record StockShortage without negative stock
      if (remainingNeed > 0.0001) {
        hasShortage = true;
        const avgCost = this.getAvgUnitCost(ingName);
        const shortId = `shortage-${this.state.uid++}`;
        const shortRec: StockShortage = {
          id: shortId,
          business_date: today,
          dish_name: dish.name,
          ingredient_id: `ing-${ingName}`,
          ingredient_name: item.ingredient_name || ingName,
          short_qty: remainingNeed.toFixed(3),
          unit: item.unit || 'kg',
          status: 'OPEN',
          estimated_unit_cost: avgCost.toFixed(6),
          estimated_cost_vnd: Math.round(remainingNeed * avgCost),
        };
        this.state.shortages.push(shortRec);

        shortageDetails.push({
          ingredient: item.ingredient_name || ingName,
          needed,
          available: deductedForIng,
          short: remainingNeed,
        });
      }
    });

    // Record sale log
    const rev = dish.price_vnd * portions;
    this.state.logs.push({
      id: this.state.uid++,
      date: today,
      type: 'sale',
      dish: dish.name,
      portions,
      revenue: rev,
      cost: totalCost,
      src: isRepurpose ? 'repurpose' : 'menu',
      item: explicitBatch?.ingredient_name,
    });

    this.saveState();
    return {
      success: true,
      dishName: dish.name,
      portions,
      totalCost,
      hasShortage,
      shortages: shortageDetails,
    };
  }

  resolveShortage(
    shortageId: string,
    action: 'CONSUMED_FROM_STOCK' | 'WRITE_OFF_ESTIMATED' | 'WAIVED',
    note?: string
  ): { success: boolean; message: string } {
    const shortage = this.state.shortages.find((s) => s.id === shortageId);
    if (!shortage) throw new Error(`Không tìm thấy bản ghi thiếu hụt ${shortageId}`);
    if (shortage.status !== 'OPEN') throw new Error('Bản ghi thiếu hụt này đã được giải quyết');

    const shortQty = parseFloat(shortage.short_qty);
    const ingName = shortage.ingredient_name.toLowerCase();

    if (action === 'CONSUMED_FROM_STOCK') {
      const avail = this.getAvailableQty(ingName);
      if (avail < shortQty - 0.0001) {
        throw new Error(
          `Kho hiện tại chỉ có ${formatQty(avail)} ${shortage.unit}, chưa đủ để trừ bù ${formatQty(shortQty)} ${shortage.unit}`
        );
      }

      // Deduct via FEFO
      let remaining = shortQty;
      const usable = this.getUsableBatches(ingName);
      let deductedCost = 0;

      for (const b of usable) {
        if (remaining <= 0.0001) break;
        const bAvail = parseFloat(b.remaining_qty);
        const dAmt = Math.min(bAvail, remaining);
        b.remaining_qty = Math.max(0, bAvail - dAmt).toFixed(3);
        const uCost = parseFloat(b.unit_cost);
        b.stock_value_vnd = Math.round(parseFloat(b.remaining_qty) * uCost);

        const lineCost = Math.round(dAmt * uCost);
        deductedCost += lineCost;
        remaining -= dAmt;

        this.state.movements.push({
          id: `m-${this.state.uid++}`,
          occurred_on: offsetDays(0),
          type: 'SALE_CONSUMPTION',
          category: 'SALE_CONSUMPTION',
          ingredient_id: b.ingredient_id,
          ingredient_name: b.ingredient_name,
          batch_id: b.id,
          qty_delta: (-dAmt).toFixed(3),
          unit: b.unit,
          unit_cost_snapshot: b.unit_cost,
          value_vnd: -lineCost,
          reference_kind: 'SHORTAGE_RESOLUTION',
          reference_id: shortage.id,
          created_at: new Date().toISOString(),
        });
      }

      shortage.status = 'RESOLVED';
      shortage.resolution = 'CONSUMED_FROM_STOCK';
      shortage.resolution_note = note || 'Đã trừ bù từ lô hàng có sẵn';
      shortage.resolved_at = new Date().toISOString();

      this.saveState();
      return { success: true, message: `Đã trừ bù ${formatQty(shortQty)} ${shortage.unit} từ kho thành công.` };
    }

    if (action === 'WRITE_OFF_ESTIMATED') {
      shortage.status = 'RESOLVED';
      shortage.resolution = 'WRITTEN_OFF_ESTIMATED';
      shortage.resolution_note = note || 'Ghi nhận chi phí ước tính vào P&L';
      shortage.resolved_at = new Date().toISOString();

      this.saveState();
      return { success: true, message: `Đã ghi nhận chi phí ước tính (${formatMoney(shortage.estimated_cost_vnd || 0)}) vào P&L.` };
    }

    // WAIVED
    shortage.status = 'RESOLVED';
    shortage.resolution = 'WAIVED';
    shortage.resolution_note = note || 'Miễn trừ chênh lệch';
    shortage.resolved_at = new Date().toISOString();

    this.saveState();
    return { success: true, message: `Đã miễn trừ chênh lệch thiếu hụt.` };
  }

  // ==========================================
  // DOCUMENT IMPORTS (SCAN MODAL)
  // ==========================================

  importReceiptDocument(
    lines: Array<{
      name: string;
      qty: number;
      unit?: string;
      cost: number;
      location?: StorageLocation;
      expiry_date?: string;
    }>,
    docDate?: string
  ): { createdCount: number; totalValue: number } {
    let createdCount = 0;
    let totalValue = 0;
    const targetDate = docDate || offsetDays(0);

    lines.forEach((line) => {
      if (line.qty <= 0) return;
      const b = this.addBatchManual({
        name: line.name,
        qty: line.qty,
        unit: line.unit,
        cost: line.cost,
        location: line.location || 'FRIDGE',
        received_on: targetDate,
        expiry_date: line.expiry_date,
      });
      createdCount++;
      totalValue += b.stock_value_vnd;
    });

    return { createdCount, totalValue };
  }

  importSalesReportDocument(
    lines: Array<{
      dish_name: string;
      qty: number;
      unit_price?: number;
    }>,
    docDate?: string
  ): {
    soldCount: number;
    totalRevenue: number;
    hasShortage: boolean;
    shortageCount: number;
  } {
    let soldCount = 0;
    let totalRevenue = 0;
    let hasShortage = false;
    let shortageCount = 0;

    lines.forEach((line) => {
      if (line.qty <= 0) return;
      const normalized = normalizeStr(line.dish_name);
      const dish = this.state.dishes.find(
        (d) => normalizeStr(d.name) === normalized || normalizeStr(d.name).includes(normalized)
      );

      if (dish) {
        const res = this.cookDish(dish.id, line.qty);
        soldCount += line.qty;
        totalRevenue += (line.unit_price || dish.price_vnd) * line.qty;
        if (res.hasShortage) {
          hasShortage = true;
          shortageCount += res.shortages.length;
        }
      }
    });

    return { soldCount, totalRevenue, hasShortage, shortageCount };
  }

  // ==========================================
  // DISH & RECIPE MANAGEMENT (RECIPE MODAL)
  // ==========================================

  saveDish(dishData: {
    id?: string;
    name: string;
    price_vnd: number;
    recipe: Array<{ ingredient_name: string; quantity: string; unit: string }>;
  }): Dish {
    const trimmedName = dishData.name.trim();
    if (!trimmedName) throw new Error('Tên món ăn không được để trống');
    if (dishData.price_vnd < 0) throw new Error('Giá bán không được âm');
    if (!dishData.recipe || dishData.recipe.length === 0) {
      throw new Error('Công thức món ăn cần ít nhất một nguyên liệu');
    }

    let dish = dishData.id ? this.state.dishes.find((d) => d.id === dishData.id) : undefined;

    const formattedRecipe = dishData.recipe.map((r) => ({
      ingredient_id: `ing-${r.ingredient_name.toLowerCase().trim()}`,
      ingredient_name: r.ingredient_name.trim(),
      quantity: r.quantity,
      unit: r.unit || 'kg',
    }));

    if (dish) {
      dish.name = trimmedName;
      dish.price_vnd = dishData.price_vnd;
      dish.recipe = formattedRecipe;
    } else {
      dish = {
        id: `dish-${this.state.uid++}`,
        name: trimmedName,
        price_vnd: dishData.price_vnd,
        recipe: formattedRecipe,
        cost_estimate_vnd: { value: 0, basis: 'ESTIMATE' },
        gross_margin_estimate: { amount_vnd: 0, percent: 0, basis: 'ESTIMATE' },
        max_portions: 0,
        missing_ingredients: [],
        uses_expiring_stock: false,
      };
      this.state.dishes.push(dish);
    }

    this.saveState();
    return dish;
  }

  deleteDish(dishId: string) {
    this.state.dishes = this.state.dishes.filter((d) => d.id !== dishId);
    this.saveState();
  }
}

export const simulationStore = new SimulationStore();
