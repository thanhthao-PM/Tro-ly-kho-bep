# ĐẶC TẢ MODULES HỆ THỐNG (SYSTEM MODULES SPECIFICATION)

> Phiên bản: Revision 6.3  
> Phân quyền sở hữu dữ liệu và ranh giới nghiệp vụ giữa các module

---

## 1. NGUYÊN TẮC PHÂN CHIA TRÁCH NHIỆM (DATA OWNERSHIP)

Mỗi bảng trong cơ sở dữ liệu chỉ có **DUY NHẤT MỘT** module làm chủ ghi (`Only Writer`). Các module khác muốn can thiệp phải gọi qua Service Interface của module chủ quản:

| Bảng dữ liệu | Module làm chủ ghi (Writer) | Các module được phép đọc (Readers) |
|---|---|---|
| `user_profiles`, `kitchens`, `kitchen_settings` | `identity_access` (seed) / `catalog` | Tất cả |
| `units`, `ingredients`, `ingredient_aliases`, `ingredient_unit_conversions` | `catalog` | Tất cả (thông qua CatalogService) |
| `batches`, `stock_movements` | `inventory` (chỉ qua InventoryService) | `reports`, `assistant`, `sales` |
| `documents`, `document_lines`, `idempotency_keys` | `documents` | `sales`, `inventory` |
| `dishes`, `recipe_items` | `menu` | Tất cả (thông qua MenuService) |
| `sales`, `sale_lines`, `stock_shortages` | `sales` | `reports`, `assistant` |
| `disposals` | `dispositions` | `reports`, `assistant` |
| `notification_reads` | `notifications` | UI clients |
| `audit_log` | `core.audit` helper | Admin / Audit services |

---

## 2. CHI TIẾT CÁC MODULE

### 2.1 Module `catalog`
- **Trách nhiệm:** Quản lý nguyên liệu, đơn vị đo, quy đổi đơn vị, chuẩn hoá tên tìm kiếm (NFC, lowercase, accent-stripped).
- **Ràng buộc nghiệp vụ:**
  - Ngăn chặn xoá nguyên liệu nếu đang nằm trong công thức của bất kỳ món ăn nào đang hoạt động.
  - Ngăn chặn thay đổi `base_unit_code` nếu nguyên liệu đã phát sinh bất kỳ dòng dữ liệu nào trong kho, chứng từ, hoặc công thức (`BASE_UNIT_LOCKED`).

### 2.2 Module `inventory`
- **Trách nhiệm:** Quản lý các lô hàng vật lý và sổ cái kho bất biến.
- **Thuật toán FEFO:**
  - Khóa các dòng lô hàng `FOR UPDATE` theo thứ tự: `expiry_date ASC NULLS LAST`, `received_on ASC`, `id ASC`.
  - Khóa các nguyên liệu theo thứ tự ID tăng dần (`ORDER BY ingredient_id ASC`) để triệt tiêu nguy cơ Deadlock khi nhiều đơn hàng chạy song song.
- **Ràng buộc nghiệp vụ:**
  - Không bao giờ để tồn kho âm. Nếu không đủ, đẩy phần thiếu hụt sang module `sales` để ghi nhận `stock_shortages`.
  - Cập nhật tự động tồn kho `remaining_qty` thông qua Trigger `AFTER INSERT` trên `stock_movements`.

### 2.3 Module `menu`
- **Trách nhiệm:** Quản lý thực đơn và định lượng công thức.
- **Tính toán động:**
  - `cost_estimate_vnd`: Lấy đơn giá trung bình của các lô hàng còn dùng được (`usable`) nhân với định lượng công thức.
  - `max_portions`: Tìm giá trị nhỏ nhất của `floor(avail(ingredient) / quantity_base)` cho tất cả nguyên liệu trong món.

### 2.4 Module `documents`
- **Trách nhiệm:** Tiếp nhận, bóc tách và chuyển đổi hoá đơn/báo cáo thành chứng từ nháp (`DRAFT`).
- **Xác nhận chứng từ (`confirm`):**
  - Nếu là `IMPORT_INVOICE`: Tạo các lô hàng mới qua `InventoryService.receive_batch`.
  - Nếu là `SALES_REPORT`: Chuyển sang `SalesService.record_sales_report` để thực hiện tiêu thụ FEFO.

### 2.5 Module `sales`
- **Trách nhiệm:** Ghi nhận doanh thu, trừ kho FEFO, và quản lý thiếu hụt kho Option C.
- **Quy trình Option C:**
  - Khi kho thiếu nguyên liệu, ghi nhận toàn bộ doanh thu, trừ hết tồn khả dụng, và tạo bản ghi `stock_shortages` trạng thái `OPEN`.
  - Cung cấp hàm `settle_sale_lines` là nguồn chân lý duy nhất tính toán và cập nhật `sale_lines.cogs_vnd` và `consumption_status`.

### 2.6 Module `dispositions`
- **Trách nhiệm:** Thực hiện các hành động giải cứu hoặc huỷ bỏ hàng cận date.
- **Ràng buộc:**
  - Lô hàng quá hạn chỉ cho phép hành động `WASTE`, trừ khi cấu hình cho phép `COOK`.
  - Hành động `COOK` tạo bản ghi bán hàng `origin: REPURPOSE`, ưu tiên trừ lô được chỉ định trước rồi mới FEFO các lô khác.

### 2.7 Module `reports`
- **Trách nhiệm:** Cung cấp số liệu tài chính kỳ kinh doanh và gợi ý bổ sung hàng D25.
- **Nguyên tắc:** Toàn bộ báo cáo tài chính đọc từ view `ledger_effective`, đảm bảo tính toán giá vốn chính xác, minh bạch, tách biệt số liệu thực tế và ước tính.

### 2.8 Module `assistant`
- **Trách nhiệm:** Trả lời tự nhiên các câu hỏi của người dùng về kho bếp.
- **Nguyên tắc:** Sử dụng **RuleBasedProvider** làm mặc định; toàn bộ con số đều trích xuất từ dữ liệu thực (`verified facts`) thông qua placeholders `{{fact:ID}}`. AI không bao giờ được tự sinh số liệu giả mạo.
