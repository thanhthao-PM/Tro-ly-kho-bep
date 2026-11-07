/**
 * TypeScript Data Contracts cho Module Catalog (Nguyên liệu, Đơn vị, Quy đổi)
 * Ánh xạ 1:1 từ Pydantic catalog.py
 */

export type UnitDimension = 'MASS' | 'VOLUME' | 'COUNT';

export type StorageLocation = 'FRIDGE' | 'FREEZER' | 'PANTRY';

export interface Unit {
  code: string;
  label_vi: string;
  dimension: UnitDimension;
  factor_to_dimension_base?: string | null;
}

export interface UnitConversion {
  unit_code: string;
  factor_to_base: string;
}

export interface Ingredient {
  id: string;
  name: string;
  normalized_name: string;
  search_name: string;
  base_unit: Unit;
  default_location: StorageLocation;
  tracks_expiry: boolean;
  min_stock_qty: string;
  order_step?: string | null;
  expiry_warning_days?: number | null;
  aliases: string[];
  conversions: UnitConversion[];
  deleted?: boolean;
}

export interface IngredientCreate {
  name: string;
  base_unit_code: string;
  default_location?: StorageLocation;
  tracks_expiry?: boolean;
  min_stock_qty?: string;
  order_step?: string | null;
  expiry_warning_days?: number | null;
  aliases?: string[];
  conversions?: UnitConversion[];
}

export interface IngredientUpdate {
  name?: string;
  default_location?: StorageLocation;
  tracks_expiry?: boolean;
  min_stock_qty?: string;
  order_step?: string | null;
  expiry_warning_days?: number | null;
  aliases?: string[];
  conversions?: UnitConversion[];
}
