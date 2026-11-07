# THIẾT KẾ CƠ SỞ DỮ LIỆU (DATABASE SPECIFICATION)

> Phiên bản: Revision 6.3  
> Hệ quản trị CSDL: **PostgreSQL 15+**  
> Quản lý schema: **SQLAlchemy 2.x Models** & **Alembic Migrations**

---

## 1. QUY ƯỚC CHUNG

1. **Khóa chính & Đa người thuê:**
   - Mọi bảng thuộc sở hữu của bếp (Tenant table) có khóa chính `id uuid DEFAULT gen_random_uuid()`.
   - Có trường `kitchen_id uuid NOT NULL`.
   - Ràng buộc duy nhất `UNIQUE (kitchen_id, id)` để các bảng con có thể tạo khóa ngoại kết hợp `(kitchen_id, parent_id)`.
2. **Kiểu dữ liệu số lượng & Tiền tệ:**
   - Số lượng: `numeric(14,3)` (chính xác đến 0.001 đơn vị cơ sở).
   - Đơn giá: `numeric(18,6)` (lưu đơn giá chính xác đến 6 chữ số thập phân trên mỗi đơn vị cơ sở).
   - Tổng tiền VND: `bigint` (luôn làm tròn đến số nguyên đồng VND).
3. **Chuỗi và Enum:**
   - Sử dụng kiểu `text` kết hợp ràng buộc `CHECK (col IN (...))` thay vì `pg_enum` để Alembic quản lý và di trú đơn giản hơn.
4. **Thời gian:**
   - Ngày kinh doanh / ngày hết hạn: Kiểu `date`.
   - Thời điểm kiểm toán: Kiểu `timestamptz`.

---

## 2. DANH SÁCH BẢNG & ĐẶC TẢ CHI TIẾT

### 2.1 Bảng Tài khoản & Cấu hình

#### `user_profiles`
- `id` (uuid, PK, tương ứng ID người dùng)
- `display_name` (text, NOT NULL)
- `created_at` (timestamptz, default now())

#### `kitchens`
- `id` (uuid, PK)
- `owner_user_id` (uuid, NOT NULL, UNIQUE -> user_profiles.id)
- `name` (text, NOT NULL)
- `timezone` (text, NOT NULL, default 'Asia/Ho_Chi_Minh')
- `created_at` (timestamptz, default now())

#### `kitchen_settings`
- `kitchen_id` (uuid, PK -> kitchens.id)
- `expiry_warning_days` (smallint, default 3, CHECK 0..30)
- `target_coverage_days` (smallint, default 3, CHECK 1..60)
- `consumption_window_days` (smallint, default 14, CHECK 7..90)
- `min_history_days` (smallint, default 7, CHECK >= 1)
- `unusual_quantity_ratio` (numeric(6,2), default 2.0)
- `backdate_limit_days` (smallint, default 2)
- `expired_batches_consumable` (boolean, default false)
- `expired_batch_actions` (text[], default '{"WASTE"}', CHECK 'WASTE' = ANY(expired_batch_actions))
- Ràng buộc: `CHECK (min_history_days <= consumption_window_days)`

---

### 2.2 Bảng Danh mục & Nguyên liệu (Catalog)

#### `units` (Bảng tham chiếu toàn cục, không có kitchen_id)
- `code` (text, PK, ví dụ: 'g', 'kg', 'ml', 'l', 'quả', 'hộp', 'bó', 'củ', 'bìa', 'gói', 'chai')
- `label_vi` (text, NOT NULL)
- `dimension` (text, NOT NULL, CHECK IN ('MASS', 'VOLUME', 'COUNT'))
- `factor_to_dimension_base` (numeric(18,6), NULLABLE)
- Ràng buộc:
  ```sql
  CHECK (
    (dimension IN ('MASS', 'VOLUME') AND factor_to_dimension_base > 0)
    OR
    (dimension = 'COUNT' AND factor_to_dimension_base IS NULL)
  )
  ```

#### `ingredients`
- `id` (uuid, PK)
- `kitchen_id` (uuid, NOT NULL)
- `name` (text, NOT NULL)
- `normalized_name` (text, NOT NULL)
- `search_name` (text, NOT NULL)
- `base_unit_code` (text, NOT NULL -> units.code)
- `default_location` (text, NOT NULL, CHECK IN ('FRIDGE', 'FREEZER', 'PANTRY'))
- `tracks_expiry` (boolean, default true)
- `min_stock_qty` (numeric(14,3), default 0, CHECK >= 0)
- `order_step` (numeric(14,3), NULLABLE, CHECK order_step > 0)
- `expiry_warning_days` (smallint, NULLABLE, CHECK 0..30)
- `deleted_at` (timestamptz, NULLABLE)
- `created_at` (timestamptz, default now())
- `updated_at` (timestamptz, default now())
- Ràng buộc & Chỉ mục:
  - `UNIQUE (kitchen_id, id)`
  - `UNIQUE (kitchen_id, id, base_unit_code)` (phục vụ khóa ngoại quy đổi đơn vị)
  - Partial Unique: `CREATE UNIQUE INDEX uq_ingredients_normalized ON ingredients(kitchen_id, normalized_name) WHERE deleted_at IS NULL`

#### `ingredient_aliases`
- `id` (uuid, PK)
- `kitchen_id` (uuid, NOT NULL)
- `ingredient_id` (uuid, NOT NULL)
- `alias` (text, NOT NULL)
- `normalized_alias` (text, NOT NULL)
- Khóa ngoại: `FOREIGN KEY (kitchen_id, ingredient_id) REFERENCES ingredients(kitchen_id, id)`
- `UNIQUE (kitchen_id, normalized_alias)`

#### `ingredient_unit_conversions`
- `kitchen_id` (uuid, NOT NULL)
- `ingredient_id` (uuid, NOT NULL)
- `base_unit_code` (text, NOT NULL)
- `unit_code` (text, NOT NULL -> units.code)
- `factor_to_base` (numeric(18,6), NOT NULL, CHECK factor_to_base > 0)
- Khóa chính: `PRIMARY KEY (kitchen_id, ingredient_id, unit_code)`
- Khóa ngoại: `FOREIGN KEY (kitchen_id, ingredient_id, base_unit_code) REFERENCES ingredients(kitchen_id, id, base_unit_code)`
- Ràng buộc: `CHECK (unit_code <> base_unit_code)`

---

### 2.3 Bảng Kho hàng & Sổ cái (Inventory & Ledger)

#### `batches` (Lô hàng tồn)
- `id` (uuid, PK)
- `kitchen_id` (uuid, NOT NULL)
- `ingredient_id` (uuid, NOT NULL)
- `received_on` (date, NOT NULL)
- `expiry_date` (date, NULLABLE)
- `initial_qty` (numeric(14,3), NOT NULL, CHECK initial_qty > 0)
- `remaining_qty` (numeric(14,3), NOT NULL, default 0, CHECK remaining_qty >= 0)
- `unit_cost` (numeric(18,6), NOT NULL, CHECK unit_cost >= 0)
- `location` (text, NOT NULL, CHECK IN ('FRIDGE', 'FREEZER', 'PANTRY'))
- `source_document_line_id` (uuid, NULLABLE)
- `created_at` (timestamptz, default now())
- Ràng buộc & Khóa ngoại:
  - `UNIQUE (kitchen_id, id)`
  - `UNIQUE (kitchen_id, ingredient_id, id)`
  - `FOREIGN KEY (kitchen_id, ingredient_id) REFERENCES ingredients(kitchen_id, id)`
  - `CHECK (expiry_date IS NULL OR expiry_date >= received_on)`
- Chỉ mục tối ưu:
  - FEFO Index: `CREATE INDEX idx_batches_fefo ON batches(kitchen_id, ingredient_id, expiry_date NULLS LAST, received_on, id) WHERE remaining_qty > 0`
  - Expiring Index: `CREATE INDEX idx_batches_expiring ON batches(kitchen_id, expiry_date) WHERE remaining_qty > 0`

#### `stock_movements` (Sổ cái kho bất biến - Append-only)
- `id` (uuid, PK)
- `kitchen_id` (uuid, NOT NULL)
- `ingredient_id` (uuid, NOT NULL)
- `batch_id` (uuid, NOT NULL)
- `type` (text, NOT NULL, CHECK IN ('RECEIPT', 'SALE_CONSUMPTION', 'USAGE_CONSUMPTION', 'DONATION', 'SELLOFF', 'WASTE', 'ADJUSTMENT_IN', 'ADJUSTMENT_OUT', 'REVERSAL'))
- `qty_delta` (numeric(14,3), NOT NULL, CHECK qty_delta <> 0)
- `unit_cost_snapshot` (numeric(18,6), NOT NULL)
- `value_vnd` (bigint, NOT NULL)
- `occurred_on` (date, NOT NULL)
- `created_at` (timestamptz, default now())
- `actor_id` (uuid, NULLABLE -> user_profiles.id)
- `reason_code` (text, NULLABLE)
- `note` (text, NULLABLE)
- `sale_line_id` (uuid, NULLABLE)
- `disposal_id` (uuid, NULLABLE)
- `document_line_id` (uuid, NULLABLE)
- `shortage_id` (uuid, NULLABLE)
- `reverses_movement_id` (uuid, NULLABLE, UNIQUE -> stock_movements.id)
- Ràng buộc:
  - Khóa ngoại kết hợp: `FOREIGN KEY (kitchen_id, ingredient_id, batch_id) REFERENCES batches(kitchen_id, ingredient_id, id)`
  - Cùng dấu: `CHECK (value_vnd = 0 OR sign(value_vnd) = sign(qty_delta))`
  - Dung sai làm tròn: `CHECK (abs(value_vnd - (qty_delta * unit_cost_snapshot)) < 1)`
  - Ràng buộc chiều dấu và liên kết theo từng loại:
    - `RECEIPT`, `ADJUSTMENT_IN`: `qty_delta > 0`
    - `SALE_CONSUMPTION`: `qty_delta < 0 AND sale_line_id IS NOT NULL`
    - `USAGE_CONSUMPTION`: `qty_delta < 0 AND document_line_id IS NOT NULL`
    - `DONATION`, `SELLOFF`, `WASTE`: `qty_delta < 0 AND disposal_id IS NOT NULL`
    - `ADJUSTMENT_OUT`: `qty_delta < 0 AND reason_code IS NOT NULL`
    - `REVERSAL`: `reverses_movement_id IS NOT NULL`

---

### 2.4 Bảng Thực đơn & Bán hàng (Menu & Sales)

#### `dishes`
- `id` (uuid, PK)
- `kitchen_id` (uuid, NOT NULL)
- `name` (text, NOT NULL)
- `normalized_name` (text, NOT NULL)
- `price_vnd` (bigint, NOT NULL, CHECK price_vnd >= 0)
- `deleted_at` (timestamptz, NULLABLE)
- `created_at` (timestamptz, default now())
- `UNIQUE (kitchen_id, id)`
- Partial Unique: `CREATE UNIQUE INDEX uq_dishes_normalized ON dishes(kitchen_id, normalized_name) WHERE deleted_at IS NULL`

#### `recipe_items`
- `kitchen_id` (uuid, NOT NULL)
- `dish_id` (uuid, NOT NULL)
- `ingredient_id` (uuid, NOT NULL)
- `quantity_base` (numeric(14,3), NOT NULL, CHECK quantity_base > 0)
- Khóa chính: `PRIMARY KEY (kitchen_id, dish_id, ingredient_id)`
- Khóa ngoại kết hợp:
  - `FOREIGN KEY (kitchen_id, dish_id) REFERENCES dishes(kitchen_id, id)`
  - `FOREIGN KEY (kitchen_id, ingredient_id) REFERENCES ingredients(kitchen_id, id)`

#### `sales`
- `id` (uuid, PK)
- `kitchen_id` (uuid, NOT NULL)
- `business_date` (date, NOT NULL)
- `source_document_id` (uuid, NULLABLE)
- `created_by` (uuid, NULLABLE)
- `created_at` (timestamptz, default now())
- `UNIQUE (kitchen_id, id)`
- Partial Unique: `CREATE UNIQUE INDEX uq_sales_source_doc ON sales(source_document_id) WHERE source_document_id IS NOT NULL`

#### `sale_lines`
- `id` (uuid, PK)
- `kitchen_id` (uuid, NOT NULL)
- `sale_id` (uuid, NOT NULL)
- `dish_id` (uuid, NOT NULL)
- `dish_name_snapshot` (text, NOT NULL)
- `quantity` (integer, NOT NULL, CHECK quantity > 0)
- `unit_price_snapshot_vnd` (bigint, NOT NULL)
- `revenue_vnd` (bigint, NOT NULL)
- `cogs_vnd` (bigint, NOT NULL, default 0, CHECK cogs_vnd >= 0)
- `consumption_status` (text, NOT NULL, default 'FULL', CHECK IN ('FULL', 'PARTIAL', 'RESOLVED'))
- `origin` (text, NOT NULL, default 'NORMAL', CHECK IN ('NORMAL', 'REPURPOSE'))
- `source_batch_id` (uuid, NULLABLE)
- Khóa ngoại & Ràng buộc:
  - `UNIQUE (kitchen_id, id)`
  - `FOREIGN KEY (kitchen_id, sale_id) REFERENCES sales(kitchen_id, id)`
  - `FOREIGN KEY (kitchen_id, dish_id) REFERENCES dishes(kitchen_id, id)`
  - Ràng buộc nguồn gốc:
    ```sql
    CHECK (
      (origin = 'REPURPOSE' AND source_batch_id IS NOT NULL)
      OR
      (origin = 'NORMAL' AND source_batch_id IS NULL)
    )
    ```

#### `stock_shortages` (Thiếu hụt tồn kho Option C)
- `id` (uuid, PK)
- `kitchen_id` (uuid, NOT NULL)
- `sale_line_id` (uuid, NULLABLE)
- `document_line_id` (uuid, NULLABLE)
- `ingredient_id` (uuid, NOT NULL)
- `short_qty` (numeric(14,3), NOT NULL, CHECK short_qty > 0)
- `status` (text, NOT NULL, default 'OPEN', CHECK IN ('OPEN', 'RESOLVED'))
- `resolution` (text, NULLABLE, CHECK IN ('CONSUMED_FROM_STOCK', 'WRITTEN_OFF_ESTIMATED', 'WAIVED'))
- `estimated_unit_cost` (numeric(18,6), NULLABLE)
- `estimated_cost_vnd` (bigint, NULLABLE)
- `estimate_batch_id` (uuid, NULLABLE)
- `resolution_note` (text, NULLABLE)
- `resolved_at` (timestamptz, NULLABLE)
- `resolved_by` (uuid, NULLABLE)
- Ràng buộc:
  - `CHECK ( (sale_line_id IS NOT NULL AND document_line_id IS NULL) OR (sale_line_id IS NULL AND document_line_id IS NOT NULL) )`
  - `CHECK (status = 'RESOLVED' = (resolution IS NOT NULL AND resolved_at IS NOT NULL))`
  - `CHECK (resolution = 'WAIVED' = (resolution_note IS NOT NULL))`
  - `CHECK (resolution = 'WRITTEN_OFF_ESTIMATED' = (estimated_cost_vnd IS NOT NULL))`
  - `CHECK (resolution = 'CONSUMED_FROM_STOCK' = (estimated_cost_vnd IS NULL AND estimated_unit_cost IS NULL))`

---

### 2.5 Bảng Chứng từ & Xử lý cận date

#### `documents`
- `id` (uuid, PK)
- `kitchen_id` (uuid, NOT NULL)
- `kind` (text, NOT NULL, CHECK IN ('IMPORT_INVOICE', 'SALES_REPORT', 'USAGE_SLIP'))
- `source_format` (text, NOT NULL, CHECK IN ('CSV', 'XLSX', 'IMAGE', 'PDF', 'MANUAL'))
- `status` (text, NOT NULL, default 'DRAFT', CHECK IN ('DRAFT', 'CONFIRMED', 'CANCELLED'))
- `business_date` (date, NOT NULL)
- `original_filename` (text, NULLABLE)
- `file_sha256` (text, NULLABLE)
- `storage_key` (text, NULLABLE)
- `ocr_status` (text, NOT NULL, default 'NOT_APPLICABLE', CHECK IN ('NOT_APPLICABLE', 'PENDING', 'DONE', 'FAILED'))
- `created_by` (uuid, NULLABLE)
- `created_at` (timestamptz, default now())
- `confirmed_at` (timestamptz, NULLABLE)
- `UNIQUE (kitchen_id, id)`
- Partial Unique chống trùng file: `CREATE UNIQUE INDEX uq_documents_hash ON documents(kitchen_id, kind, file_sha256) WHERE status <> 'CANCELLED' AND file_sha256 IS NOT NULL`

#### `document_lines`
- `id` (uuid, PK)
- `kitchen_id` (uuid, NOT NULL)
- `document_id` (uuid, NOT NULL)
- `line_no` (integer, NOT NULL)
- `raw_text` (text, NULLABLE)
- `parsed_name` (text, NULLABLE)
- `ingredient_id` (uuid, NULLABLE)
- `dish_id` (uuid, NULLABLE)
- `quantity` (numeric(14,3), NULLABLE)
- `unit_code` (text, NULLABLE -> units.code)
- `unit_price_vnd` (numeric(18,2), NULLABLE)
- `line_total_vnd` (bigint, NULLABLE)
- `expiry_date` (date, NULLABLE)
- `confidence` (jsonb, NULLABLE)
- `flags` (text[], default '{}')
- `is_selected` (boolean, default true)
- `UNIQUE (kitchen_id, id)`
- `UNIQUE (document_id, line_no)`
- Ràng buộc: `CHECK (NOT (ingredient_id IS NOT NULL AND dish_id IS NOT NULL))`

#### `disposals` (Xử lý hàng cận date / quá hạn)
- `id` (uuid, PK)
- `kitchen_id` (uuid, NOT NULL)
- `batch_id` (uuid, NOT NULL)
- `type` (text, NOT NULL, CHECK IN ('DONATION', 'SELLOFF', 'WASTE'))
- `quantity` (numeric(14,3), NOT NULL, CHECK quantity > 0)
- `occurred_on` (date, NOT NULL)
- `reason_code` (text, NULLABLE, CHECK reason_code IN ('EXPIRED', 'SPOILED', 'OVERSTOCK', 'OTHER'))
- `note` (text, NULLABLE)
- `counterparty_name` (text, NULLABLE)
- `revenue_vnd` (bigint, NULLABLE)
- `created_by` (uuid, NULLABLE)
- `created_at` (timestamptz, default now())
- Ràng buộc:
  - `CHECK (type = 'WASTE' = (reason_code IS NOT NULL))`
  - `CHECK (reason_code = 'OTHER' = (note IS NOT NULL))`
  - `CHECK (type = 'SELLOFF' = (revenue_vnd IS NOT NULL))`
  - `CHECK (type <> 'SELLOFF' = (revenue_vnd IS NULL))`

---

### 2.6 Bảng Tiện ích: Idempotency, Cảnh báo & Kiểm toán

#### `idempotency_keys`
- `kitchen_id` (uuid, NOT NULL)
- `endpoint` (text, NOT NULL)
- `key` (text, NOT NULL)
- `request_hash` (text, NOT NULL)
- `actor_id` (uuid, NULLABLE)
- `status` (text, NOT NULL, CHECK IN ('CLAIMED', 'COMPLETED'))
- `response_status` (integer, NULLABLE)
- `response_body` (jsonb, NULLABLE)
- `created_at` (timestamptz, default now())
- `completed_at` (timestamptz, NULLABLE)
- `PRIMARY KEY (kitchen_id, endpoint, key)`

#### `notification_reads`
- `kitchen_id` (uuid, NOT NULL)
- `notification_key` (text, NOT NULL)
- `read_at` (timestamptz, default now())
- `PRIMARY KEY (kitchen_id, notification_key)`

#### `audit_log`
- `id` (bigserial, PK)
- `kitchen_id` (uuid, NOT NULL)
- `actor_id` (uuid, NULLABLE)
- `action` (text, NOT NULL)
- `entity_type` (text, NOT NULL)
- `entity_id` (uuid, NOT NULL)
- `before` (jsonb, NULLABLE)
- `after` (jsonb, NULLABLE)
- `request_id` (text, NULLABLE)
- `created_at` (timestamptz, default now())

---

## 3. VIEW ĐẶC TẢ SỔ CÁI: `ledger_effective`

```sql
CREATE OR REPLACE VIEW ledger_effective WITH (security_invoker = true) AS
SELECT
  sm.id AS movement_id,
  sm.kitchen_id,
  sm.batch_id,
  sm.ingredient_id,
  COALESCE(orig.type, sm.type) AS category,
  sm.type AS original_type,
  CASE
    WHEN sm.sale_line_id IS NOT NULL THEN s.business_date
    WHEN sm.type = 'USAGE_CONSUMPTION' AND sm.document_line_id IS NOT NULL THEN doc.business_date
    WHEN sm.disposal_id IS NOT NULL THEN d.occurred_on
    WHEN sm.type = 'REVERSAL' THEN (
      CASE
        WHEN orig.sale_line_id IS NOT NULL THEN orig_s.business_date
        WHEN orig.type = 'USAGE_CONSUMPTION' AND orig.document_line_id IS NOT NULL THEN orig_doc.business_date
        WHEN orig.disposal_id IS NOT NULL THEN orig_d.occurred_on
        ELSE orig.occurred_on
      END
    )
    ELSE sm.occurred_on
  END AS attribution_date,
  sm.qty_delta,
  sm.unit_cost_snapshot,
  sm.value_vnd,
  sm.sale_line_id,
  sm.disposal_id,
  sm.document_line_id,
  sm.shortage_id,
  sm.reverses_movement_id,
  sm.created_at
FROM stock_movements sm
LEFT JOIN stock_movements orig ON sm.reverses_movement_id = orig.id
LEFT JOIN sale_lines sl ON sm.sale_line_id = sl.id
LEFT JOIN sales s ON sl.sale_id = s.id
LEFT JOIN disposals d ON sm.disposal_id = d.id
LEFT JOIN document_lines dl ON sm.document_line_id = dl.id
LEFT JOIN documents doc ON dl.document_id = doc.id
LEFT JOIN sale_lines orig_sl ON orig.sale_line_id = orig_sl.id
LEFT JOIN sales orig_s ON orig_sl.sale_id = orig_s.id
LEFT JOIN disposals orig_d ON orig.disposal_id = orig_d.id
LEFT JOIN document_lines orig_dl ON orig.document_line_id = orig_dl.id
LEFT JOIN documents orig_doc ON orig_dl.document_id = orig_doc.id;
```
