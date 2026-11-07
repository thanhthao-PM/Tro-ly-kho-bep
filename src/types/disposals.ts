/**
 * TypeScript Data Contracts cho Module Disposals (Xử lý hàng cận date & quá hạn)
 * Ánh xạ 1:1 từ Pydantic disposals.py
 */
import { Batch, ExpiryStatus } from './inventory';

export type DisposalType = 'DONATION' | 'SELLOFF' | 'WASTE';

export type WasteReason = 'EXPIRED' | 'SPOILED' | 'OVERSTOCK' | 'OTHER';

export interface SuggestedDish {
  dish_id: string;
  name: string;
  portions_possible: number;
  gross_margin_estimate_vnd: number;
}

export interface ExpiringBatch {
  batch: Batch;
  status: ExpiryStatus;
  suggested_dishes: SuggestedDish[];
  available_actions: string[];
}

export interface DisposalCreate {
  type: DisposalType;
  quantity: string;
  unit?: string;
  occurred_on?: string;
  note?: string;
  counterparty_name?: string;
  revenue_vnd?: number;
  reason_code?: WasteReason;
}

export interface CookRequest {
  dish_id: string;
  portions: number;
  business_date?: string;
  note?: string;
}
