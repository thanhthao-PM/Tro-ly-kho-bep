/**
 * TypeScript Data Contracts cho Module Menu (Món ăn, Định lượng, Giá vốn)
 * Ánh xạ 1:1 từ Pydantic menu.py
 */
import { Labeled } from './common';

export interface RecipeItem {
  ingredient_id: string;
  ingredient_name?: string | null;
  quantity: string;
  unit?: string | null;
}

export interface DishMarginEstimate {
  amount_vnd: number;
  percent: number;
  basis: 'ESTIMATE';
}

export interface Dish {
  id: string;
  name: string;
  price_vnd: number;
  recipe: RecipeItem[];
  cost_estimate_vnd: Labeled<number>;
  gross_margin_estimate: DishMarginEstimate;
  max_portions: number;
  missing_ingredients: string[];
  uses_expiring_stock: boolean;
}

export interface DishCreate {
  name: string;
  price_vnd: number;
  recipe: RecipeItem[];
}

export interface DishUpdate {
  name?: string;
  price_vnd?: number;
  recipe?: RecipeItem[];
}
