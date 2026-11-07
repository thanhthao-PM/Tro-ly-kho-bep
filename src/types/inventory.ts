/**
 * TypeScript Data Contracts cho Module Inventory (Kho hàng, Lô hàng, Sổ cái)
 * Ánh xạ 1:1 từ Pydantic inventory.py
 */
import { StorageLocation } from './catalog';

export type ExpiryStatus = 'EXPIRED' | 'EXPIRES_SOON' | 'OK' | 'NO_EXPIRY';

export type MovementType =
  | 'RECEIPT'
  | 'SALE_CONSUMPTION'
  | 'USAGE_CONSUMPTION'
  | 'DONATION'
  | 'SELLOFF'
  | 'WASTE'
  | 'ADJUSTMENT_IN'
  | 'ADJUSTMENT_OUT'
  | 'REVERSAL';

export interface Batch {
  id: string;
  ingredient_id: string;
  ingredient_name: string;
  received_on: string; // YYYY-MM-DD
  expiry_date?: string | null; // YYYY-MM-DD
  initial_qty: string;
  remaining_qty: string;
  unit: string;
  unit_cost: string;
  stock_value_vnd: number;
  location: StorageLocation;
  expiry_status: ExpiryStatus;
  days_to_expiry?: number | null;
}

export interface BatchCreate {
  ingredient_id: string;
  quantity: string;
  unit?: string;
  unit_price_vnd: string;
  received_on: string;
  expiry_date?: string | null;
  location?: StorageLocation;
}

export interface BatchMetadataUpdate {
  location?: StorageLocation;
  expiry_date?: string | null;
  received_on?: string;
}

export interface StocktakeAdjustmentRequest {
  new_remaining_quantity: string;
  unit?: string;
  reason_code: 'COUNT_CORRECTION' | 'LOSS' | 'FOUND' | 'OTHER';
  note?: string;
}

export interface StockMovement {
  id: string;
  occurred_on: string;
  type: MovementType;
  category: string;
  ingredient_id: string;
  ingredient_name: string;
  batch_id: string;
  qty_delta: string;
  unit: string;
  unit_cost_snapshot: string;
  value_vnd: number;
  reference_kind?: string | null;
  reference_id?: string | null;
  created_at: string;
}

export interface InventoryIngredientSummary {
  ingredient_id: string;
  name: string;
  total_remaining: string;
  unit: string;
  location: StorageLocation;
  batch_count: number;
  nearest_expiry?: string | null;
  expiry_status: ExpiryStatus;
  last_received_on?: string | null;
}

export interface InventorySummary {
  ingredient_count: number;
  batch_count: number;
  stock_value_vnd: number;
  by_status: {
    expired: number;
    expires_soon: number;
    ok: number;
    no_expiry?: number;
  };
  by_location: {
    FRIDGE: number;
    FREEZER: number;
    PANTRY: number;
  };
}
