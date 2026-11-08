# TRỢ LÝ KHO BẾP (AI KITCHEN INVENTORY ASSISTANT)

> **Hệ thống Quản lý Kho Bếp Thông minh & Bổ sung Hàng Tối ưu hóa Giá vốn (COGS) dành cho Quán ăn / Bếp thương mại vừa và nhỏ.**  
> Đóng băng kiến trúc chuẩn **Architecture Revision 6.3 (FROZEN Core Baseline)**.

[![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)](docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](backend)
[![React](https://img.shields.io/badge/Frontend-React%2019-61DAFB?logo=react)](src)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2016-336791?logo=postgresql)](docs/DATABASE.md)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini%203.8%20Flash-orange?logo=google)](docs/ARCHITECTURE.md)

---

## 1. TỔNG QUAN HỆ THỐNG

Dự án giải quyết triệt để 5 bài toán nhức nhối nhất trong vận hành bếp thương mại:
1. **Kiểm soát giá vốn thực tế (COGS Snapshot)**: Tự động bóc tách định lượng món và tính giá vốn theo phương pháp **FEFO** (First Expired, First Out - Ưu tiên lô cận date nhất).
2. **Xử lý thiếu hụt kho Option C**: Bếp vẫn bán được hàng khi nhân viên quên nhập hóa đơn; hệ thống ghi nhận doanh thu đầy đủ, trừ hết tồn kho khả dụng và tự động tạo bản ghi `stock_shortages` để xử lý trừ bù sau.
3. **Chống lãng phí thực phẩm**: Tự động phát hiện các lô hàng cận date (≤ 3 ngày) và đề xuất các phương án xử lý: nấu món tận dụng (`COOK`), bán thanh lý thu mua (`SELLOFF`), quyên góp (`DONATION`), hoặc hủy bỏ ghi nhận lý do (`WASTE`).
4. **Đề xuất bổ sung hàng tối ưu (Thuật toán D25)**: Tính toán lượng đặt hàng dựa trên tốc độ tiêu thụ bình quân ngày thực tế (`avg_daily_consumption`), số ngày bao phủ mục tiêu (`target_coverage_days`), và làm tròn theo bước đặt hàng (`order_step`).
5. **Trợ lý AI Fact-based Grounding**: Truy xuất dữ liệu thực tế từ sổ cái, trả lời câu hỏi kèm thẻ dẫn chứng `VerifiedFact`, phân biệt minh bạch giữa số liệu thực tế (`VERIFIED_FACT`) và ước tính (`ESTIMATE`), không sinh số liệu giả mạo (zero hallucination).

---

## 2. CÔNG NGHỆ VÀ KIẾN TRÚC

- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, Lucide Icons.
- **Backend**: Python 3.11, FastAPI (Modular Monolith), Pydantic v2, Uvicorn.
- **Cơ sở dữ liệu**: PostgreSQL 16, SQLAlchemy 2.x (Synchronous mode với `psycopg 3`), Alembic migration authority.
- **Dịch vụ AI**: Google GenAI SDK (`@google/genai`) với model `gemini-3.8-flash`, cơ chế Grounding chặt chẽ và dự phòng Rule-based cục bộ.
- **Đóng gói & Triển khai**: Docker & Docker Compose (hỗ trợ lưu trữ bền vững volume).

---

## 3. HƯỚNG DẪN KHỞI CHẠY BẰNG DOCKER COMPOSE (KHUYÊN DÙNG)

Chỉ với **1 câu lệnh duy nhất**, toàn bộ hệ thống gồm PostgreSQL, Migration, Backend API và Frontend sẽ được tự động biên dịch, khởi tạo schema, nạp dữ liệu mẫu và vận hành:

### Bước 1: Sao chép file cấu hình môi trường
```bash
cp .env.example .env
```
Để đọc ảnh/PDF bằng AI, điền `GEMINI_API_KEY` trong file `.env` ở thư mục gốc. CSV/XLSX có thể đọc trực tiếp mà không cần API key.

### Bước 2: Khởi chạy Docker Compose
```bash
docker compose up --build -d
```

### Bước 3: Truy cập ứng dụng
- **Giao diện người dùng (Frontend)**: [http://localhost:3001](http://localhost:3001)
- **Tài liệu API Swagger (Backend)**: [http://localhost:8001/docs](http://localhost:8001/docs)
- **Kiểm tra trạng thái sức khỏe (Health Check)**: [http://localhost:3001/api/health](http://localhost:3001/api/health)

### Quét hóa đơn nhập kho

Trong giao diện **Quét**, chọn một trong các cách:
- **Chọn tệp hóa đơn**: CSV, XLSX, PDF hoặc ảnh JPG/PNG/WebP.
- **Chọn hình ảnh** hoặc **Chụp bằng camera**: ảnh được đọc bằng Gemini.

CSV/XLSX phải có các cột theo thứ tự `Tên nguyên liệu, Số lượng, Đơn vị, Đơn giá` (có thể có dòng tiêu đề; hỗ trợ dấu phẩy/chấm thập phân và phân cách cột bằng dấu phẩy hoặc chấm phẩy). Ảnh/PDF cần có `GEMINI_API_KEY` trong `.env`; nếu thiếu, ứng dụng sẽ báo rõ và vẫn cho nhập dòng thủ công. Sau khi kiểm tra các dòng, chọn nguyên liệu trong danh mục rồi bấm **Xác nhận nhập kho**. Chỉ bước xác nhận mới ghi chứng từ, dòng hàng, lô tồn và biến động kho vào PostgreSQL; tệp gốc được giữ trong Docker volume `invoice_data`. Sau khi thêm API key, khởi động lại backend bằng `docker compose up --build -d backend`.

### Dừng hệ thống:
```bash
docker compose down
# Hoặc dừng và xóa sạch volume dữ liệu:
docker compose down -v
```

---

## 4. HƯỚNG DẪN CÀI ĐẶT & CHẠY THỦ CÔNG (STANDALONE)

Dành cho môi trường phát triển trên máy cá nhân không sử dụng Docker:

### 4.1. Chuẩn bị Cơ sở dữ liệu PostgreSQL
Khởi tạo database PostgreSQL cục bộ:
```sql
CREATE DATABASE kitchen_inventory;
```

### 4.2. Khởi chạy Backend (Python FastAPI)
1. Di chuyển vào thư mục backend:
   ```bash
   cd backend
   ```
2. Tạo môi trường ảo và kích hoạt:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Trên Linux/macOS
   # hoặc: venv\Scripts\activate trên Windows
   ```
3. Cài đặt thư viện dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Cấu hình file `.env`:
   ```bash
   cp .env.example .env
   # Điều chỉnh DATABASE_URL nếu mật khẩu PostgreSQL của bạn khác mặc định
   ```
5. Chạy Migration cập nhật schema Database:
   ```bash
   alembic upgrade head
   ```
6. Nạp dữ liệu danh mục & demo ban đầu:
   ```bash
   python -m app.db.seed --demo
   ```
7. Chạy kiểm thử Backend:
   ```bash
   python -m unittest discover tests
   ```
8. Khởi động Backend API:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### 4.3. Khởi chạy Frontend (React + Vite + Node.js)
1. Mở cửa sổ terminal mới tại thư mục gốc của dự án.
2. Cài đặt các gói npm:
   ```bash
   npm install
   ```
3. Khởi chạy Frontend Dev Server:
   ```bash
   npm run dev
   ```
4. Truy cập giao diện tại: `http://localhost:3000`.

---

## 5. CẤU HÌNH BIẾN MÔI TRƯỜNG (.ENV)

| Tên biến | Mặc định | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `GEMINI_API_KEY` | *(trống)* | Không | API Key Google AI Studio, bắt buộc nếu muốn đọc hóa đơn từ ảnh/PDF. CSV/XLSX và nhập tay không cần key. |
| `PORT` | `3000` | Có | Cổng dịch vụ chạy ứng dụng Web Frontend. |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres_password_123@localhost:5432/kitchen_inventory` | Có | URL kết nối PostgreSQL qua SQLAlchemy 2.x (Sync driver `psycopg 3`). |
| `ADMIN_DATABASE_URL` | `postgresql+psycopg://postgres:postgres_password_123@localhost:5432/kitchen_inventory` | Có | URL dành riêng cho migration Alembic (quyền quản trị DDL). |
| `JWT_SECRET` | `super_secret_jwt_key...` | Có | Khóa bí mật ký xác thực JWT. |
| `APP_ENV` | `development` | Có | Môi trường ứng dụng (`development` / `production`). |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Có | Danh sách domain được phép gọi API Backend. |

---

## 6. CÁC PHÂN HỆ VÀ TÍNH NĂNG CHÍNH

### 1. Phân hệ Kho hàng (`KhoView.tsx`)
- Danh sách nguyên liệu nhóm theo sản phẩm, hiển thị tổng tồn khả dụng, nơi cất giữ (Tủ lạnh, Ngăn đông, Tủ bếp), và trạng thái hạn dùng đợt sớm nhất.
- Hỗ trợ lọc theo vị trí và tìm kiếm tức thì.
- **Sáu (06) Modal tương tác tích hợp đầy đủ**:
  - `ScanModal`: Quét / Nhập chứng từ hóa đơn, kiểm tra bất thường số lượng nhập.
  - `NotificationsModal`: Trung tâm cảnh báo lô hết hạn, cận date và danh sách thiếu hụt Option C cần giải quyết.
  - `ItemDetailModal`: Xem chi tiết từng đợt nhập của nguyên liệu, số lượng và ngày hết hạn.
  - `ProcessBatchModal`: Thực hiện quy trình xử lý lô hàng cận date (Nấu món, Bán thanh lý, Quyên góp, Hủy bỏ).
  - `RecipeModal`: Xem và chỉnh sửa định lượng công thức món ăn.
  - `InventoryEditModal`: Điều chỉnh nhanh vị trí cất giữ và ngày hết hạn của lô hàng.

### 2. Phân hệ Thực đơn & Giá vốn (`MenuView.tsx`)
- Danh sách món ăn với giá bán, giá vốn ước tính (`ESTIMATE`), lãi gộp và số phần tối đa có thể nấu dựa trên tồn kho thực tế.
- Tự động đánh dấu các món tận dụng nguyên liệu cận date để bếp trưởng ưu tiên bán trước.
- Tính năng nấu món (`CookDish`) và ghi nhận bán hàng (`RecordSale`) tự động áp dụng FEFO và bóc tách thiếu hụt Option C.

### 3. Phân hệ Báo cáo P&L & Hao hụt (`ReportsView.tsx`)
- Báo cáo kết quả kinh doanh 2 dòng lãi gộp: Lãi gộp thực tế (loại trừ ước tính) và Lãi gộp đầy đủ (bao gồm chi phí ước tính).
- Phân tích chi tiết giá trị hàng hóa bị bỏ theo lý do (hỏng, quá hạn, cháy xém...) và theo từng nguyên liệu.
- Theo dõi tình trạng thiếu hụt (`COGS Status`: `has_open_shortages`, `all_actual`).

### 4. Phân hệ Trợ lý AI & Bổ sung hàng (`AssistantView.tsx`)
- **Ưu tiên xử lý hôm nay**: Nhận diện tức thì các lô hàng cận date (≤ 3 ngày) và quá hạn.
- **Thuật toán D25**: Đề xuất lượng đặt hàng bù dựa trên chu kỳ bao phủ và tồn tối thiểu, làm tròn theo `order_step`.
- **Hỏi đáp Grounded Chat**: Tương tác hỏi đáp bằng tiếng Việt về tình hình kho, kiểm tra giá trị tồn, phân tích lãi lỗ, hiển thị minh bạch thẻ `VerifiedFact` và lý do thiếu dữ liệu (`data_gaps`).

---

## 7. HƯỚNG DẪN XỬ LÝ LỖI THƯỜNG GẶP (TROUBLESHOOTING)

### Q1: Lỗi xung đột cổng `Port 3000` hoặc `Port 5432` đã bị sử dụng?
**Xử lý**: 
- Kiểm tra các tiến trình đang chiếm cổng:
  ```bash
  lsof -i :3000   # hoặc :5432 trên Linux/macOS
  ```
- Hoặc đổi cổng ánh xạ trong file `docker-compose.yml` (ví dụ `"3001:3000"`).

### Q2: Lỗi kết nối PostgreSQL: `connection to server at "localhost" failed`?
**Xử lý**:
- Đảm bảo service PostgreSQL đang chạy và cổng 5432 sẵn sàng.
- Khi chạy bằng Docker, chuỗi kết nối trong container phải trỏ về hostname của service là `postgres` chứ không phải `localhost`:
  `postgresql+psycopg://postgres:postgres_password_123@postgres:5432/kitchen_inventory`

### Q3: Chạy migration Alembic bị báo lỗi bảng đã tồn tại hoặc revision mismatch?
**Xử lý**:
- Kiểm tra trạng thái migration hiện tại:
  ```bash
  alembic current
  ```
- Đồng bộ lại schema về phiên bản mới nhất:
  ```bash
  alembic upgrade head
  ```

### Q4: Trợ lý AI báo "Cơ sở: rule_based" thay vì LLM bên ngoài?
**Xử lý**:
- Nếu quét ảnh/PDF báo thiếu `GEMINI_API_KEY`, thêm key vào `.env` ở thư mục gốc rồi chạy `docker compose up --build -d backend`. CSV/XLSX không cần key.

---

## 8. TÀI LIỆU KỸ THUẬT CHI TIẾT

- [Đặc tả Kiến trúc Hệ thống (ARCHITECTURE.md)](docs/ARCHITECTURE.md)
- [Thiết kế Cơ sở dữ liệu & Sổ cái (DATABASE.md)](docs/DATABASE.md)
- [Đặc tả Giao diện API (API_SPEC.md)](docs/API_SPEC.md)
- [Cấu trúc Module Monolith (MODULES.md)](docs/MODULES.md)

---
*Dự án hoàn thành toàn bộ 5 Giai đoạn theo đúng tiêu chuẩn kiến trúc Revision 6.3.*
