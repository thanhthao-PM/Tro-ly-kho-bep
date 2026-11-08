# HỢP ĐỒNG GIAO TIẾP API (API CONTRACT SPECIFICATION)

> Phiên bản: Revision 6.3  
> Định dạng: RESTful JSON API  
> Base URL: `/api/v1`  
> Xác thực: `Authorization: Bearer <JWT>`  
> Header kiểm soát trùng lặp: `Idempotency-Key: <UUID hoặc chuỗi duy nhất>`

---

## 1. QUY ƯỚC CHUNG

1. **Định dạng dữ liệu:**
   - JSON keys: `snake_case`.
   - Ngày tháng: `YYYY-MM-DD`.
   - Thời điểm: `ISO-8601` (`YYYY-MM-DDTHH:mm:ss.sssZ`).
   - Số lượng: Chuỗi Decimal (ví dụ: `"2.500"`).
   - Đơn giá: Chuỗi Decimal (ví dụ: `"35000.000000"`).
   - Số tiền VND: Số nguyên `integer` (ví dụ: `70000`).
2. **Quy ước đơn vị:**
   - Trong dữ liệu trả về từ hệ thống, mọi số lượng đều được quy đổi về **đơn vị cơ sở (`base_unit`)** của nguyên liệu đó kèm theo mã `unit`.
   - Trong dữ liệu gửi lên từ người dùng, chấp nhận bất kỳ đơn vị nào có thể quy đổi được (`convertible unit`).
3. **Mã lỗi chuẩn hóa:**
   Tất cả lỗi trả về định dạng `{ "code": string, "message": string, "details": any, "request_id": string }`.
   - `401 UNAUTHENTICATED`: Token không hợp lệ hoặc hết hạn.
   - `403 KITCHEN_NOT_PROVISIONED`: Người dùng chưa được liên kết với bếp.
   - `404 NOT_FOUND`: Không tìm thấy tài nguyên trong phạm vi bếp hiện tại.
   - `409 INSUFFICIENT_STOCK`: Tồn kho không đủ để thực hiện thao tác.
   - `409 DUPLICATE_NAME`: Tên nguyên liệu hoặc món ăn đã tồn tại.
   - `409 DUPLICATE_DOCUMENT`: File hoá đơn đã từng được tải lên và xác nhận.
   - `409 DOCUMENT_ALREADY_CONFIRMED`: Chứng từ đã được xác nhận trước đó.
   - `409 BASE_UNIT_LOCKED`: Không thể đổi đơn vị cơ sở vì đã có dữ liệu vận hành.
   - `409 ACTION_NOT_PERMITTED_FOR_EXPIRED_BATCH`: Hành động không được phép đối với lô hàng đã hết hạn.
   - `422 VALIDATION_ERROR`: Dữ liệu không thỏa mãn ràng buộc schema Pydantic.
   - `422 UNIT_NOT_CONVERTIBLE`: Đơn vị không thể quy đổi về đơn vị cơ sở.
   - `422 EXPIRY_REQUIRED`: Nguyên liệu bắt buộc phải có hạn sử dụng nhưng bị để trống.
   - `422 IDEMPOTENCY_KEY_REUSED`: Trùng lặp khóa Idempotency nhưng nội dung request khác nhau.

---

## 2. DANH MỤC ENDPOINTS

### 2.1 Hệ thống & Tài khoản
- `GET /health`: Liveness probe (không cần auth, trả về `{ "status": "ok" }`).
- `GET /me`: Lấy thông tin user hiện tại và bếp đang quản lý (`{ user_id, display_name, kitchen: { id, name, timezone } }`).
- `GET /settings`: Lấy cấu hình ngưỡng cảnh báo và tham số kho.
- `PUT /settings`: Cập nhật cấu hình ngưỡng cảnh báo (`expiry_warning_days`, `target_coverage_days`,...).

### 2.2 Danh mục & Nguyên liệu (Catalog)
- `GET /units`: Lấy danh sách toàn bộ đơn vị tính chuẩn.
- `GET /ingredients`: Danh sách nguyên liệu (Query: `q`, `include_deleted`, `limit`, `cursor`).
- `POST /ingredients`: Tạo nguyên liệu mới (Header: `Idempotency-Key` khuyến nghị).
- `GET /ingredients/{id}`: Chi tiết nguyên liệu kèm danh sách quy đổi và bí danh.
- `PATCH /ingredients/{id}`: Cập nhật nguyên liệu (tên, vị trí, cảnh báo, quy đổi, bí danh). Nếu đổi `base_unit` khi đã có dữ liệu sẽ trả lỗi `409 BASE_UNIT_LOCKED`.
- `DELETE /ingredients/{id}`: Xóa mềm nguyên liệu (chỉ cho phép nếu không có công thức món đang hoạt động).

### 2.3 Kho hàng & Lô hàng (Inventory)
- `GET /inventory/ingredients`: Tổng quan kho theo nguyên liệu (Query: `q`, `location`, `received`, `sort=exp|imp|name`).
- `GET /inventory/ingredients/{id}/batches`: Chi tiết các lô hàng của một nguyên liệu.
- `GET /batches/{id}`: Chi tiết một lô hàng cụ thể.
- `POST /batches`: Nhập thủ công một lô hàng mới (Header: `Idempotency-Key` bắt buộc).
- `PATCH /batches/{id}`: Sửa metadata lô hàng (vị trí `location`, ngày nhận `received_on`, hạn dùng `expiry_date`).
- `POST /batches/{id}/adjustments`: Cân chỉnh số lượng kiểm kê kho (Header: `Idempotency-Key` bắt buộc; Body: `new_remaining_quantity`, `reason_code`, `note`).
- `GET /inventory/summary`: Thống kê tổng số mặt hàng, số lô tồn, giá trị tồn kho, tỷ lệ theo nơi cất và hạn dùng.
- `GET /stock-movements`: Lịch sử biến động sổ cái kho (Query: `from`, `to`, `type`, `ingredient_id`, `cursor`).

### 2.4 Chứng từ Nhập & Xuất (Documents)
- `POST /documents/scan-invoice-image`: Quét ảnh JPEG/PNG/WebP hoặc PDF hóa đơn nhập (tối đa 10 MB); cần cấu hình `GEMINI_API_KEY` trong biến môi trường hoặc `.env` ở thư mục gốc/backend.
- `POST /documents/parse-invoice-file`: Đọc CSV/XLSX (tối đa 10 MB) có cột tên, số lượng, đơn vị và đơn giá.
- `POST /documents/receipts/upload`: Xác nhận nhập kho bằng multipart gồm `file` và `payload` (metadata JSON); giữ tệp gốc để tải lại.
- `GET /documents/{id}/file`: Tải tệp hóa đơn gốc (`kitchen_id` query bắt buộc).
- `POST /documents/receipts`: Xác nhận nhập kho thủ công hoặc không kèm tệp; mỗi dòng có thể gửi `ingredient_id` hoặc chỉ gửi `name`, khi đó backend tự tìm theo tên chuẩn hóa hoặc tạo nguyên liệu mới theo đơn vị tính.
- Xác nhận hóa đơn tạo chứng từ, dòng chứng từ, lô hàng và bút toán `RECEIPT` trong cùng transaction; lỗi ở bất kỳ dòng nào sẽ rollback toàn bộ.
- `GET /documents`: Danh sách chứng từ.
- `GET /documents/{id}`: Chi tiết chứng từ và các dòng chi tiết (`document_lines`).
- `POST /documents/{id}/lines`: Thêm dòng mới vào chứng từ nháp (`DRAFT`).
- `PATCH /documents/{id}/lines/{line_id}`: Sửa dòng (tên, số lượng, đơn vị, đơn giá, hạn dùng, cờ chọn dòng `is_selected`).
- `DELETE /documents/{id}/lines/{line_id}`: Xóa một dòng khỏi chứng từ nháp.
- `POST /documents/{id}/confirm`: Xác nhận chứng từ (Header: `Idempotency-Key` bắt buộc). Tạo các lô hàng (nếu là hoá đơn nhập) hoặc trừ kho ghi nhận bán hàng (nếu là báo cáo xuất).
- `POST /documents/{id}/cancel`: Hủy chứng từ nháp.

### 2.5 Thực đơn & Bán hàng (Menu & Sales)
- `GET /dishes`: Danh sách món ăn kèm giá vốn ước tính, biên lãi %, số phần tối đa nấu được và nguyên liệu thiếu.
- `POST /dishes`: Tạo món mới kèm công thức định lượng (Header: `Idempotency-Key`).
- `GET /dishes/{id}`: Chi tiết món ăn và công thức.
- `PATCH /dishes/{id}`: Cập nhật thông tin món hoặc ghi đè toàn bộ công thức định lượng.
- `DELETE /dishes/{id}`: Xóa mềm món ăn.
- `GET /sales`: Danh sách các đợt bán hàng.
- `GET /sales/{id}`: Chi tiết đợt bán hàng và các dòng món đã bán.
- `GET /shortages`: Danh sách các trường hợp thiếu hụt tồn kho (Query: `status=OPEN|RESOLVED`).
- `POST /shortages/{id}/resolve`: Giải quyết thiếu hụt tồn kho (Header: `Idempotency-Key` bắt buộc; Body: `action=CONSUME_FROM_STOCK|WRITE_OFF_ESTIMATED|WAIVE`, `note`).

### 2.6 Xử lý hàng cận date & quá hạn (Dispositions)
- `GET /expiring-batches`: Danh sách các lô hàng cận date hoặc đã quá hạn, kèm gợi ý món ăn nấu được theo định nghĩa `usable(batch)`.
- `POST /batches/{id}/disposals`: Xử lý lô hàng cận date (Header: `Idempotency-Key` bắt buộc; Body: `type=DONATION|SELLOFF|WASTE`, `quantity`, `revenue_vnd` nếu bán, `reason_code` nếu huỷ).
- `POST /batches/{id}/cook`: Nấu món tận dụng từ lô hàng chỉ định (Header: `Idempotency-Key` bắt buộc; Body: `dish_id`, `portions`, `business_date`).

### 2.7 Thông báo (Notifications)
- `GET /notifications`: Danh sách cảnh báo động (Query: `state=unread|all`, `date`).
- `POST /notifications/read`: Đánh dấu đã đọc các thông báo (Body: `{ "keys": string[], "all": boolean }`).

### 2.8 Báo cáo & Bổ sung hàng (Reports & Replenishment)
- `GET /reports/daily-invoices`: Tổng số hóa đơn, dòng nguyên liệu và tổng tiền nhập kho theo ngày (`kitchen_id`, `business_date`); trả kèm danh sách và đường dẫn tải tệp đã lưu.
- `GET /reports/summary`: Báo cáo tài chính kỳ kinh doanh (Query: `from`, `to`). Trả về Doanh thu bán, Doanh thu thanh lý, Giá vốn thực tế, Giá vốn ước tính, Chi phí huỷ, Chi phí quyên góp, Lãi gộp tách 2 dòng, cùng 2 cờ `has_open_shortages` và `all_actual`.
- `GET /reports/waste`: Báo cáo phân tích hao hụt theo lý do và mặt hàng.
- `GET /reports/dishes`: Báo cáo hiệu quả sinh lời chi tiết từng món ăn.
- `GET /replenishment-suggestions`: Gợi ý đặt hàng thông minh theo thuật toán D25 (Query: các tham số tuỳ chọn hoặc lấy theo settings).

### 2.9 Trợ lý AI (Assistant)
- `POST /assistant/messages`: Gửi câu hỏi cho Trợ lý AI (Body: `{ "message": string, "history": [{ "role": "user"|"assistant", "text": string }] }`).
- Trả về: `{ "answer_text": string, "facts": [...], "recommendations": [...], "data_gaps": [...], "proposed_actions": [...] }`.
