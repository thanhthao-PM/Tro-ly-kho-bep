# KIẾN TRÚC HỆ THỐNG "TRỢ LÝ KHO BẾP" (AI KITCHEN INVENTORY ASSISTANT)

> Tài liệu đặc tả kiến trúc chính thức cho dự án Trợ lý kho bếp.  
> Được đóng băng dựa trên **Architecture Revision 6.3 (FROZEN Core Baseline)**.  
> Áp dụng kiến trúc: **Frontend React + TypeScript**, **Backend Python + FastAPI**, **Database PostgreSQL + SQLAlchemy 2.x + Alembic**.

---

## 1. TỔNG QUAN HỆ THỐNG

### 1.1 Mục tiêu
Hệ thống quản lý kho bếp thông minh dành cho quán ăn/bếp thương mại quy mô vừa và nhỏ:
- **Kiểm soát giá vốn món ăn (COGS):** Tự động bóc tách định lượng món ăn và tính toán giá vốn thực tế dựa trên giá nhập của các lô nguyên liệu đang tồn kho theo phương pháp **FEFO** (First Expired, First Out).
- **Chống lãng phí thực phẩm:** Tự động cảnh báo các lô hàng cận date (<= 3 ngày) và đề xuất các phương án xử lý: nấu món tận dụng (`COOK`), bán thu mua (`SELLOFF`), quyên góp (`DONATION`), hoặc huỷ bỏ có phân loại lý do (`WASTE`).
- **Xử lý thiếu hụt kho Option C:** Bếp vẫn bán được hàng khi quên nhập hoá đơn; hệ thống ghi nhận doanh thu đầy đủ, trừ hết tồn kho khả dụng và đưa lượng thiếu hụt vào danh sách `stock_shortages` để xử lý bù sau.
- **Bổ sung hàng tối ưu (Thuật toán D25):** Tính toán nhu cầu đặt hàng dựa trên tốc độ tiêu thụ bình quân ngày, số ngày bao phủ mục tiêu và làm tròn theo bước đặt hàng (`order_step`).
- **Trợ lý AI Fact-based:** Phân tích dòng tiền hàng hoá, giải đáp thắc mắc kho bằng các sự thật đã được kiểm chứng (`verified facts`), không sinh số liệu giả mạo.

### 1.2 Mô hình Tài khoản & Phạm vi (Scope)
- **Mô hình tài khoản:** Đơn bếp (`single kitchen`), 1 tài khoản quản trị (`owner_user_id`) cho giai đoạn MVP.
- **Đơn vị tiền tệ:** Đồng Việt Nam (VND), lưu trữ kiểu `bigint`.
- **Múi giờ:** `Asia/Ho_Chi_Minh` (UTC+7).

---

## 2. NGUYÊN TẮC THIẾT KẾ CỐT LÕI (FROZEN DECISIONS)

| Mã | Quyết định | Nội dung chi tiết |
|---|---|---|
| **D1** | Frontend | React + TypeScript + Vite + Tailwind CSS v4. Giao diện responsive 100% theo bản thiết kế chuẩn. |
| **D2** | Database & ORM | PostgreSQL 15+; SQLAlchemy 2.x (Synchronous mode) + Alembic. Khóa dòng giao dịch tường minh `SELECT ... FOR UPDATE`. |
| **D3** | Backend | Python FastAPI theo mô hình Modular Monolith phân tầng Service-Repository rõ ràng. |
| **D4** | Tài khoản | 1 bếp duy nhất. Mọi bảng nghiệp vụ mang trường `kitchen_id`. Khóa ngoại kết hợp `(kitchen_id, parent_id)`. |
| **D6** | Giá vốn COGS | Snapshot đơn giá lô hàng vào từng bút toán tiêu thụ. Giá vốn món trên thực đơn là số ước tính (`ESTIMATE`), giá vốn ghi nhận sau khi bán là số thực tế (`ACTUAL`). |
| **D8** | Tồn kho không âm | `batches.remaining_qty >= 0` bảo vệ ở cấp độ cơ sở dữ liệu bằng ràng buộc `CHECK`. Thiếu hàng áp dụng Option C. |
| **D10** | Hạn sử dụng | Không tự động sinh hoặc suy đoán hạn dùng. Bắt buộc người dùng xác nhận hạn dùng cho nguyên liệu có theo dõi hạn (`tracks_expiry = true`). |
| **D11** | Đơn vị & Quy đổi | Đơn vị đếm (`COUNT`) không tự quy đổi. Chỉ `MASS` hoặc `VOLUME` cùng chiều đo mới tự đổi theo factor. Các trường hợp khác bắt buộc có bảng `ingredient_unit_conversions`. |
| **D12** | Khóa đơn vị cơ sở | `base_unit_code` bị khóa bất biến (`BASE_UNIT_LOCKED`) nếu nguyên liệu đã phát sinh bất kỳ dữ liệu nghiệp vụ nào. |
| **D25** | Bổ sung hàng | Công thức xác định lượng đặt hàng từ mức tiêu thụ thực tế `avg_daily_consumption`, số ngày tồn kho `days_of_cover`, và làm tròn theo `order_step`. |
| **D29** | Idempotency | Giao thức chống trùng lặp: Claim khoá và thực thi nghiệp vụ trong cùng một database transaction (`INSERT ... ON CONFLICT DO NOTHING`). |
| **D30** | Trigger Sổ cái | Trigger `AFTER INSERT` trên `stock_movements` tự động cộng trừ `remaining_qty` của lô hàng; trigger kiểm tra tính toàn vẹn tại thời điểm commit. |
| **D32** | Xử lý thiếu hụt | Cung cấp 3 hành động: `CONSUME_FROM_STOCK` (trừ bù), `WRITE_OFF_ESTIMATED` (tính giá vốn ước tính), `WAIVE` (bỏ qua, ghi chú bắt buộc). |

---

## 3. THIẾT KẾ SỔ CÁI KHO BẤT BIẾN (IMMUTABLE LEDGER)

### 3.1 Quy ước Dấu tiền tệ và Số lượng
Tất cả các dòng chuyển động kho trong `stock_movements` tuân thủ quy ước dấu:
- **`qty_delta` và `value_vnd` luôn cùng dấu:**
  - Nhập kho (`RECEIPT`), Cân chỉnh thừa (`ADJUSTMENT_IN`): `qty_delta > 0`, `value_vnd > 0`.
  - Tiêu thụ bán món (`SALE_CONSUMPTION`), Xuất dùng (`USAGE_CONSUMPTION`), Quyên góp (`DONATION`), Thanh lý (`SELLOFF`), Huỷ bỏ (`WASTE`), Cân chỉnh thiếu (`ADJUSTMENT_OUT`): `qty_delta < 0`, `value_vnd < 0`.
- **Chi phí báo cáo:** Được tính bằng `-Σ value_vnd` (luôn luôn là số dương).
- **Ràng buộc:** `CHECK (cogs_vnd >= 0)`.

### 3.2 Bút toán Đảo (`REVERSAL`)
- Không bao giờ xoá hoặc sửa dòng sổ cái (`stock_movements` cấm `UPDATE` và `DELETE` bằng trigger).
- Muốn sửa thì tạo dòng `REVERSAL`:
  - `reversal.qty_delta = -original.qty_delta`
  - `reversal.value_vnd = -original.value_vnd`
  - `reversal.unit_cost_snapshot = original.unit_cost_snapshot`
  - Sao chép toàn bộ các liên kết tham chiếu (`sale_line_id`, `disposal_id`,...).

### 3.3 View `ledger_effective`
Hệ thống cung cấp một view chỉ đọc `ledger_effective` gom toàn bộ các giao dịch và bút toán đảo, ánh xạ ngày ghi nhận nghiệp vụ (`attribution_date`):
- Bán hàng: Lấy theo `sales.business_date`.
- Xuất dùng: Lấy theo `documents.business_date`.
- Xử lý cận date: Lấy theo `disposals.occurred_on`.
- Bút toán đảo: Mang cùng `attribution_date` với bút toán gốc.

---

## 4. CHÍNH SÁCH ĐÓNG BĂNG VÀ THAM SỐ CẤU HÌNH (OPEN POLICIES CONFIRMED)

Các tham số nghiệp vụ được quản lý tập trung tại `app/core/config.py`:
1. **Số ngày cảnh báo cận date (`expiry_warning_days`):** Mặc định 3 ngày. Lô hàng hết hạn trong vòng `[0..3]` ngày được gắn nhãn `EXPIRES_SOON`.
2. **Cửa sổ tính tiêu thụ bình quân (`consumption_window_days`):** Mặc định 14 ngày.
3. **Số ngày tồn kho mục tiêu (`target_coverage_days`):** Mặc định 3 ngày.
4. **Số ngày lịch sử tối thiểu (`min_history_days`):** Mặc định 7 ngày. Dưới 7 ngày quan sát thì không gợi ý theo công thức độ bao phủ, chỉ áp dụng tồn kho tối thiểu (`MIN_STOCK_ONLY`).
5. **Tỷ lệ nhập bất thường (`unusual_quantity_ratio`):** 2.0x (lớn hơn gấp đôi lần nhập cao nhất lịch sử sẽ cảnh báo).
6. **Xử lý hàng quá hạn:** Mặc định chỉ cho phép huỷ bỏ (`WASTE`), trừ khi cấu hình cho phép nấu tận dụng (`COOK`).
7. **Báo cáo tài chính P&L:** Bắt buộc hiển thị tách bạch 2 dòng lợi nhuận: Lợi nhuận không gồm ước tính và Lợi nhuận có tính giá vốn ước tính; đi kèm 2 cờ `has_open_shortages` và `all_actual`.
