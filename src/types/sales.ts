/**
 * TypeScript Data Contracts cho Module Sales & Shortages (Bán hàng & Thiếu hụt Option C)
 * Ánh xạ 1:1 từ Pydantic sales.py
 */

export type SaleOrigin = 'NORMAL' | 'REPURPOSE';

export type ConsumptionStatus = 'FULL' | 'PARTIAL' | 'RESOLVED';

export type ShortageStatus = 'OPEN' | 'RESOLVED';

export type ShortageResolution =
  | 'CONSUMED_FROM_STOCK'
  | 'WRITTEN_OFF_ESTIMATED'
  | 'WAIVED';

export interface SaleLine {
  id: string;
  dish_id: string;
  dish_name: string;
  quantity: number;
  unit_price_vnd: number;
  revenue_vnd: number;
  cogs_vnd: number;
  estimated_cogs_vnd?: number | null;
  consumption_status: ConsumptionStatus;
  origin: SaleOrigin;
  source_batch_id?: string | null;
}

export interface Sale {
  id: string;
  business_date: string;
  revenue_vnd: number;
  line_count: number;
  has_open_shortage: boolean;
  lines?: SaleLine[];
}

export interface StockShortage {
  id: string;
  sale_line_id?: string | null;
  document_line_id?: string | null;
  business_date: string;
  dish_name?: string | null;
  ingredient_id: string;
  ingredient_name: string;
  short_qty: string;
  unit: string;
  status: ShortageStatus;
  resolution?: ShortageResolution | null;
  estimated_unit_cost?: string | null;
  estimated_cost_vnd?: number | null;
  resolution_note?: string | null;
  resolved_at?: string | null;
}

export interface ShortageResolveRequest {
  action: ShortageResolution;
  note?: string;
}
