/**
 * TypeScript Data Contracts cho Module Documents (Chứng từ, Bóc tách dòng, Xác nhận)
 * Ánh xạ 1:1 từ Pydantic documents.py
 */

export type DocumentKind = 'IMPORT_INVOICE' | 'SALES_REPORT' | 'USAGE_SLIP';

export type DocumentSourceFormat = 'CSV' | 'XLSX' | 'IMAGE' | 'PDF' | 'MANUAL';

export type DocumentStatus = 'DRAFT' | 'CONFIRMED' | 'CANCELLED';

export type OCRStatus = 'NOT_APPLICABLE' | 'PENDING' | 'DONE' | 'FAILED';

export interface DocumentLine {
  id: string;
  line_no: number;
  raw_text?: string | null;
  is_selected: boolean;
  ingredient?: { id: string; name: string } | null;
  dish?: { id: string; name: string } | null;
  quantity?: string | null;
  unit?: string | null;
  unit_price_vnd?: string | null;
  line_total_vnd?: number | null;
  expiry_date?: string | null;
  confidence?: Record<string, number> | null;
  flags: string[];
}

export interface DocumentSummary {
  line_count: number;
  total_value_vnd?: number | null;
  blocking_issues: string[];
}

export interface Document {
  id: string;
  kind: DocumentKind;
  source_format: DocumentSourceFormat;
  status: DocumentStatus;
  ocr_status: OCRStatus;
  business_date: string;
  original_filename?: string | null;
  lines: DocumentLine[];
  summary: DocumentSummary;
}

export interface DocumentLineUpdate {
  ingredient_id?: string | null;
  dish_id?: string | null;
  quantity?: string | null;
  unit?: string | null;
  unit_price_vnd?: string | null;
  expiry_date?: string | null;
  is_selected?: boolean;
  parsed_name?: string | null;
}

export interface DocumentConfirmResponse {
  document_id: string;
  status: DocumentStatus;
  batches_created?: number;
  total_value_vnd?: number;
  sales_recorded?: number;
  revenue_vnd?: number;
  shortages?: Array<{
    id: string;
    ingredient: { id: string; name: string };
    short_qty: string;
    unit: string;
    status: string;
  }>;
}
