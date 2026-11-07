/**
 * TypeScript Data Contracts cho Module Reports (Báo cáo P&L, Hao hụt, Bổ sung hàng D25)
 * Ánh xạ 1:1 từ Pydantic reports.py
 */

export interface PeriodRange {
  from_date: string;
  to_date: string;
}

export interface SalesReportSection {
  revenue_vnd: number;
  cogs_actual_vnd: number;
  cogs_estimated_vnd: number;
  gross_profit_excluding_estimates_vnd: number;
  gross_profit_including_estimates_vnd: number;
  portions_sold: number;
}

export interface SelloffReportSection {
  revenue_vnd: number;
  cost_vnd: number;
  margin_vnd: number;
}

export interface TotalsReportSection {
  revenue_vnd: number;
  gross_profit_excluding_estimates_vnd: number;
  gross_profit_including_estimates_vnd: number;
}

export interface ShortageCountSummary {
  open_count: number;
  written_off_estimated_count: number;
  waived_count: number;
}

export interface COGSStatusSummary {
  has_open_shortages: boolean;
  all_actual: boolean;
}

export interface ResultAfterLoss {
  excluding_estimates_vnd: number;
  including_estimates_vnd: number;
  policy_status: string;
}

export interface PeriodReport {
  period: PeriodRange;
  sales: SalesReportSection;
  selloff: SelloffReportSection;
  totals: TotalsReportSection;
  waste_cost_vnd: number;
  donation_cost_vnd: number;
  adjustment_net_vnd: number;
  shortages: ShortageCountSummary;
  cogs_status: COGSStatusSummary;
  result_after_ingredient_loss: ResultAfterLoss;
}

export interface WasteReasonItem {
  reason: string;
  cost_vnd: number;
  count: number;
}

export interface WasteIngredientItem {
  ingredient_name: string;
  quantity: string;
  unit: string;
  cost_vnd: number;
  count: number;
}

export interface WasteReport {
  total_waste_cost_vnd: number;
  waste_count: number;
  by_reason: WasteReasonItem[];
  by_ingredient: WasteIngredientItem[];
}

export interface DishProfitItem {
  dish_id: string;
  dish_name: string;
  portions: number;
  revenue_vnd: number;
  cogs_actual_vnd: number;
  cogs_estimated_vnd: number;
  gross_profit_vnd: number;
  has_open_shortages: boolean;
  all_actual: boolean;
}

export interface DishProfitReport {
  items: DishProfitItem[];
}

export interface ReplenishmentItem {
  ingredient_id: string;
  ingredient_name: string;
  usable_qty: string;
  unit: string;
  avg_daily_consumption?: string | null;
  days_of_cover?: string | null;
  rule: 'COVERAGE' | 'MIN_STOCK_ONLY' | 'BOTH';
  raw_order_qty: string;
  order_step?: string | null;
  suggested_order_qty: string;
  basis: 'ESTIMATE';
  assumptions: string[];
}

export interface ReplenishmentSuggestion {
  as_of: string;
  parameters: Record<string, unknown>;
  items: ReplenishmentItem[];
  insufficient_data: Array<{
    ingredient_name: string;
    reason: string;
    observed_days: number;
  }>;
  no_recent_consumption: Array<{
    ingredient_name: string;
    usable_qty: string;
    unit: string;
  }>;
}
