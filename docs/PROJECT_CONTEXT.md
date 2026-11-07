# PROJECT_CONTEXT.md

# Kitchen Assistant -- Shared Project Context

> **Mục đích:** Tài liệu ngữ cảnh chung dành cho tất cả thành viên và AI
> Agent tham gia dự án Kitchen Assistant.
>
> **Nguồn căn cứ chính:** -
> `docs/architecture/architecture-revision-6.3.md` -
> `docs/implementation/implementation-plan.md`
>
> **Nguyên tắc sử dụng:** Đây là tài liệu tóm tắt ngữ cảnh để AI tiếp
> nhận dự án nhanh. Khi cần chi tiết kỹ thuật, phải đối chiếu tài liệu
> gốc. Tài liệu này không thay thế hoặc sửa đổi hai tài liệu gốc.

------------------------------------------------------------------------

## 1. Thông tin tổng quan

  -----------------------------------------------------------------------
  Thuộc tính                          Nội dung
  ----------------------------------- -----------------------------------
  Tên dự án                           AI Kitchen Inventory Assistant /
                                      Kitchen Assistant

  Loại sản phẩm                       Ứng dụng hỗ trợ quản lý kho nguyên
                                      liệu và nghiệp vụ bếp

  Bối cảnh                            Hackathon MVP

  Đối tượng sử dụng dự kiến           Một tài khoản, một kitchen trong
                                      phạm vi MVP

  Mục tiêu                            Quản lý dữ liệu kho và các nghiệp
                                      vụ liên quan bằng dữ liệu thực;
                                      cung cấp báo cáo và trợ lý dựa trên
                                      dữ liệu kho

  Kiến trúc tham chiếu                Architecture Revision 6.3

  Trạng thái kiến trúc                Core architecture: FROZEN

  Chế độ triển khai                   Core Mode

  D30a                                PROPOSED / DISABLED
  -----------------------------------------------------------------------

**Lưu ý về mức độ xác nhận:** Tài liệu kiến trúc ghi rõ chưa có hành vi
nào được xác minh bằng kiểm thử trên môi trường PostgreSQL/Supabase mục
tiêu. Không được mô tả một thiết kế là đã chạy thành công nếu chưa có
kết quả kiểm thử thực tế.

## 2. Mục tiêu và định hướng sản phẩm

Kitchen Assistant là ứng dụng quản lý kho nguyên liệu và các nghiệp vụ
vận hành bếp. Hệ thống được thiết kế xoay quanh sổ cái biến động kho
(ledger), thay vì xem số lượng tồn kho được lưu riêng là nguồn dữ liệu
gốc.

Các định hướng cốt lõi:

-   Theo dõi biến động nhập và xuất kho bằng các dòng ledger.
-   Tính tồn kho theo dữ liệu biến động; `remaining_qty` là cache được
    duy trì và đối soát với ledger.
-   Hỗ trợ lựa chọn lô theo FEFO (First Expired, First Out).
-   Ghi nhận giá vốn theo snapshot chi phí thực tế của từng lô.
-   Ngăn tồn kho âm.
-   Quản lý đơn vị gốc và quy đổi đơn vị.
-   Theo dõi thiếu hụt khi lượng tồn không đủ cho nghiệp vụ.
-   Cung cấp báo cáo chi phí, giá vốn, tình trạng thiếu hụt và đề xuất
    tái nhập.
-   Có AI Assistant độc lập với nhà cung cấp AI; Rule-based Provider là
    phương án mặc định trong Core MVP.

## 3. Công nghệ và kiến trúc đã ghi nhận

  Thành phần           Công nghệ / định hướng
  -------------------- -----------------------------------------------------------------
  Frontend             React + TypeScript + Vite
  Backend              FastAPI, kiến trúc modular monolith
  ORM                  SQLAlchemy 2.x, chế độ sync
  PostgreSQL driver    psycopg 3
  Database             Supabase PostgreSQL
  Authentication       Supabase Auth
  Database migration   Alembic -- cơ quan duy nhất quản lý schema
  AI                   Provider-independent interface; Rule-based Provider là mặc định
  CI/CD                GitHub Actions
  Hosting Frontend     Firebase Hosting
  Hosting Backend      Google Cloud Run

Implementation Plan ghi nhận phương án triển khai Firebase Hosting +
Google Cloud Run + Supabase PostgreSQL qua Pooler + Supabase Auth là đã
được chốt (D20). Tuy nhiên, cần phân biệt quyết định triển khai được ghi
trong Implementation Plan với trạng thái D20 trong tài liệu Architecture
Revision 6.3; khi có cập nhật, Architect cần đồng bộ hai tài liệu.

**Frontend styling:** Architecture Revision 6.3 chỉ xác định React +
TypeScript + Vite, chưa chốt Tailwind CSS, CSS Modules hay component
library. Trạng thái trong Implementation Plan: `NEEDS DECISION`.

## 4. Kiến trúc tổng thể

Hệ thống được tổ chức theo các tầng:

1.  **Frontend:** Giao diện người dùng, gọi API Backend và hiển thị dữ
    liệu.
2.  **Backend API:** FastAPI tiếp nhận request, xác thực người dùng, xác
    định kitchen context và điều phối nghiệp vụ.
3.  **Domain Services:** Xử lý nghiệp vụ kho, đơn vị, công thức, nấu,
    bán hàng, báo cáo và AI.
4.  **Repositories / Data Access:** Truy vấn và ghi dữ liệu có phạm vi
    kitchen; mọi truy vấn tenant phải có điều kiện `kitchen_id`.
5.  **Database:** Supabase PostgreSQL, schema, constraints, triggers,
    views và ledger.
6.  **AI Provider:** Giao diện provider độc lập; Rule-based Provider là
    implementation mặc định trong Core MVP.

Backend là **modular monolith**, không tự ý chuyển thành microservices
trong phạm vi hiện tại.

### 4.1. Luồng triển khai theo Implementation Plan

Thứ tự triển khai chính:

`Database Schema / Constraints / Triggers / Views` →
`Domain Services / Concurrency / FEFO / Costing` → `FastAPI Endpoints` →
`React UI và AI Assistant` → `Integration / E2E Testing / Deployment`

Frontend và AI có thể phát triển song song khi API Backend đã sẵn sàng
theo điều kiện đầu vào của từng phase.

## 5. Các miền chức năng chính

Các nhóm nghiệp vụ dưới đây được tổng hợp từ Architecture Revision 6.3
và Implementation Plan. Không xem danh sách này là API contract đầy đủ.

### 5.1. Kitchen, người dùng và phạm vi dữ liệu

-   MVP giả định một tài khoản và một kitchen.
-   Không có runtime provisioning kitchen trong MVP; môi trường demo
    được tạo bằng seed/reset.
-   Dữ liệu thuộc kitchen phải được cô lập bằng `kitchen_id`, composite
    foreign keys và các bộ lọc ở tầng ứng dụng.
-   Bảng `units` là bảng dùng chung hệ thống, không có `kitchen_id`,
    runtime chỉ đọc theo thiết kế.

### 5.2. Nguyên liệu, đơn vị và quy đổi

-   Quản lý nguyên liệu và đơn vị gốc.
-   Quản lý quy đổi đơn vị.
-   Có quy tắc khóa thay đổi đơn vị gốc khi nguyên liệu đã có dữ liệu
    nghiệp vụ.
-   Điều kiện `has_operational_data(ingredient)` và quy trình khóa đồng
    thời phải tuân thủ Architecture Revision 6.3 mục 3.8.

### 5.3. Nhập kho, lô hàng và ledger

-   Ghi nhận lô hàng (`batches`) và biến động kho (`stock_movements`).
-   Ledger là nguồn dữ liệu gốc cho biến động kho.
-   `qty_delta` và `value_vnd` cùng dấu theo chiều biến động: nhập
    dương, xuất âm.
-   Reversal có giá trị đối dấu với dòng gốc và giữ snapshot/quan hệ
    tham chiếu theo quy định.
-   Tồn kho không được âm.
-   `batches.remaining_qty` là cache, phải được đối soát với tổng
    `qty_delta` của ledger.
-   Không được cập nhật cache tồn kho bằng đường ghi tùy tiện ngoài cơ
    chế được kiến trúc quy định.

### 5.4. FEFO và hạn sử dụng

-   FEFO là nguyên tắc chọn lô tự động.
-   Định nghĩa `usable(batch)` trong Architecture Revision 6.3 mục 3.7
    là định nghĩa dùng chung cho các nghiệp vụ được nêu trong tài liệu.
-   Trường hợp người dùng chỉ định lô khi COOK có quy tắc ngoại lệ
    riêng.
-   Các giá trị mặc định liên quan đến hạn sử dụng còn có
    placeholder/OPEN policy; không tự biến chúng thành chính sách an
    toàn thực phẩm đã được phê duyệt.

### 5.5. Công thức, nấu và bán hàng

-   Quản lý món ăn/công thức và nguyên liệu cần dùng.
-   Tính số phần có thể thực hiện dựa trên lượng nguyên liệu khả dụng.
-   Nghiệp vụ COOK và bán hàng có thể phát sinh tiêu hao từ nhiều lô
    theo FEFO.
-   Khi không đủ tồn, hệ thống ghi nhận thiếu hụt theo Option C và các
    trạng thái/giải pháp được mô tả trong tài liệu gốc.
-   `settle_sale_lines(line_ids)` là hàm duy nhất cập nhật cache
    `cogs_vnd` và `consumption_status` theo thiết kế.

### 5.6. Báo cáo và tái nhập

-   `ledger_effective` là view đọc dữ liệu ledger đã được quy kết ngày.
-   Báo cáo R1 và R3 sử dụng dữ liệu ledger theo quy tắc đã định nghĩa.
-   Đề xuất tái nhập RS1 dùng `attribution_date` làm cơ sở lịch sử.
-   Các trường/giá trị ước tính phải được gắn nhãn `ESTIMATE` trên giao
    diện.
-   Khi có thiếu hụt đang mở, giao diện cần thể hiện trạng thái chi phí
    chưa hoàn chỉnh theo thiết kế.

### 5.7. AI Assistant

-   Kiến trúc AI phải độc lập với nhà cung cấp.
-   Rule-based Provider là implementation mặc định trong Core MVP.
-   Assistant sử dụng dữ liệu kho thật thông qua các công cụ/đường truy
    cập được Backend cho phép.
-   AI không được tự bịa dữ liệu kho, giá, số lượng hoặc trạng thái
    nghiệp vụ.
-   External LLM được xếp vào phạm vi Deferred trong Implementation
    Plan; không tự ý tích hợp vào Core MVP.

## 6. Phạm vi triển khai

### 6.1. CORE -- Bắt buộc cho MVP

Theo Implementation Plan:

-   9 loại movement ledger, quy ước dấu và snapshot giá vốn.
-   Alembic migrations 0001--0011 theo Core Mode, không tạo role tùy
    biến theo D30a.
-   Trigger-depth guard và deferred consistency triggers.
-   View `ledger_effective` (`security_invoker`).
-   FEFO tự động và khóa bất biến đơn vị gốc theo share-lock protocol.
-   `settle_sale_lines` và shortage Option C (`CONSUME_FROM_STOCK`,
    `WAIVE`).
-   Báo cáo R1, R3 và tái nhập RS1.
-   Frontend Dashboard, Inventory, Cook, Sales, Reports.
-   Rule-based AI Assistant.
-   Core DB Tests và Core Integration Tests theo tài liệu.

### 6.2. STRETCH -- Chỉ làm sau khi Core hoàn tất

-   D30a và T2 tests.
-   Các workflow `ADJUSTMENT`, `WASTE`, `SELL_OFF`, `DONATION`.
-   Ma trận kiểm thử COOK mở rộng.
-   `WRITE_OFF_ESTIMATED`.
-   Báo cáo nâng cao R2.
-   Notifications.

### 6.3. DEFERRED -- Không triển khai trong Core MVP

-   Workflow `USAGE_CONSUMPTION`.
-   Workflow reversal và un-resolve phức tạp ở mức API/UI.
-   OCR nhập liệu hóa đơn.
-   Tích hợp External LLM (OpenAI, Gemini Live, v.v.).

**Quy tắc áp lực thời gian:** Nếu thiếu thời gian hackathon, cắt Stretch
trước. Không cắt bộ Core Ledger tests (L1--L3, C6 và Core Integration
tests) theo Implementation Plan.

## 7. Chế độ Database và bảo mật dữ liệu

### 7.1. Core Mode

-   Core Mode là chế độ đang được chọn cho Core MVP.
-   Backend dùng tài khoản admin/migration owner theo tài liệu; kết nối
    này bypass RLS vì không dùng `FORCE ROW LEVEL SECURITY`.
-   Vì vậy, cô lập tenant trong Core Mode phụ thuộc vào
    application-level kitchen filters, composite FKs và commit-time
    triggers.
-   Mọi truy vấn tenant ở tầng Repository phải lọc `kitchen_id`.
-   Không được tuyên bố RLS tự nó bảo vệ khỏi lỗi truy vấn khi ứng dụng
    đang dùng owner role.

### 7.2. D30a

-   D30a có trạng thái `PROPOSED / DISABLED`.
-   Không tạo hoặc chuyển sang dùng `app_runtime`, `ledger_owner`,
    ownership transfer hay policy theo D30a trong Core MVP nếu chưa có
    phê duyệt chính thức.
-   D30a bị gate bởi FU-1, C2 policy tests và các xác minh U2--U9.
-   Core Mode độc lập với FU-1 và không cần D30a để triển khai Core
    features.

### 7.3. Secrets

-   Database credentials, Supabase secrets, JWT secrets, API keys và
    thông tin xác thực không được commit vào Git.
-   Không đưa secret vào Frontend hoặc biến môi trường có tiền tố
    `VITE_`.
-   Chỉ dùng `.env.example` với placeholder; mỗi máy/môi trường tự cấu
    hình `.env` riêng.
-   Không yêu cầu người dùng gửi secret vào prompt, tài liệu công khai
    hoặc hội thoại nhóm.

## 8. Kế hoạch triển khai và trạng thái

Implementation Plan chia dự án thành các phase:

  -----------------------------------------------------------------------
  Phase                   Nội dung                Điều kiện/đầu ra chính
  ----------------------- ----------------------- -----------------------
  Phase 0                 Xác minh trước triển    Xác minh U1, U10, U12,
                          khai                    U13 và các điều kiện
                                                  liên quan trước
                                                  migration/code

  Phase 1                 Database foundation     Schema, bảng,
                                                  constraints và
                                                  migrations nền

  Phase 2                 Ledger engine           Ledger, triggers, view
                                                  và kiểm thử lõi

  Phase 3                 Domain services         FEFO, costing,
                                                  concurrency, nghiệp vụ

  Phase 4                 FastAPI                 API, auth, cấu hình và
                                                  seed/reset

  Phase 5                 Frontend                UI tích hợp API thật

  Phase 6                 AI Assistant            Rule-based provider
                                                  dùng dữ liệu kho thật

  Phase 7                 Integration /           Core tests, E2E, CI/CD
                          deployment              và demo runbook
  -----------------------------------------------------------------------

**Điểm bắt buộc:** Phase 0 phải được thực hiện trước khi tạo migration
hoặc dựng service. Không được giả định Phase 0 đã hoàn tất nếu chưa có
bằng chứng xác minh.

## 9. Các điểm đang mở hoặc cần xác minh

AI phải nhận diện những nội dung sau là chưa được chốt hoặc chưa được
xác minh, không tự quyết định thay nhóm:

1.  **D7:** Chính sách kế toán và cách trình bày lợi nhuận/chi phí, kỳ
    báo cáo và estimate.
2.  **D9/D9a/D9b:** Chính sách an toàn thực phẩm, xử lý hàng hết hạn,
    nguyên liệu cần theo dõi hạn dùng và các tham số liên quan.
3.  **CSS styling:** Tailwind CSS, CSS Modules hay component library.
4.  **Alembic version table:** Cách xử lý bảng `alembic_version` đối với
    Core DB Catalog Test C6 -- phương án A/B vẫn `NEEDS DECISION`.
5.  **U1:** PostgreSQL version và `security_invoker` compatibility.
6.  **U10:** Hành vi thực tế của `pg_trigger_depth()`.
7.  **U12:** Thuật toán ký JWT và claims thực tế cần xác minh.
8.  **U13:** Khả năng kết nối Pooler/network từ môi trường dev và CI/CD.
9.  **Kết nối database:** Cần đối chiếu cách đặt tên `DATABASE_URL`,
    `ADMIN_DATABASE_URL`, `MIGRATION_DATABASE_URL` giữa tài liệu và cấu
    hình triển khai; không tự suy đoán mapping cuối cùng.
10. **Các placeholder:** warning days, coverage days, history window,
    minimum history, unusual-quantity ratio, back-date limit, upload
    limits, lock timeout, idempotency retention.

Ngoài ra, Architecture Revision 6.3 tham chiếu các hợp đồng chi tiết từ
Revision 3, 4 và 5. Nếu các tài liệu đó không được cung cấp trong phiên
làm việc, AI phải ghi nhận là thiếu nguồn chi tiết, không tự dựng lại
ERD/API/formula rồi khẳng định đó là nội dung đã duyệt.

## 10. Từ điển thuật ngữ nhanh

  -----------------------------------------------------------------------
  Thuật ngữ                           Ý nghĩa trong dự án
  ----------------------------------- -----------------------------------
  Ledger-first                        Ledger là nguồn dữ liệu gốc cho
                                      biến động kho

  FEFO                                First Expired, First Out -- ưu tiên
                                      lô hết hạn sớm hơn

  Batch                               Lô nguyên liệu nhập kho

  Stock movement                      Một dòng biến động tăng/giảm kho

  `remaining_qty`                     Cache số lượng còn lại của batch,
                                      phải khớp ledger

  `ledger_effective`                  View đọc movement với category và
                                      attribution date đã chuẩn hóa

  `kitchen_id`                        Khóa phạm vi dữ liệu của từng
                                      kitchen

  COGS                                Cost of Goods Sold -- giá vốn hàng
                                      bán

  `all_actual`                        Cờ thể hiện dữ liệu chi phí có hoàn
                                      toàn là actual theo định nghĩa của
                                      kiến trúc

  `has_open_shortages`                Cờ có ít nhất một shortage đang mở

  Core Mode                           Chế độ triển khai Core hiện tại
                                      dùng owner/admin connection

  D30a                                Thiết kế runtime role/policy được
                                      đề xuất nhưng đang disabled
  -----------------------------------------------------------------------

## 11. Hướng dẫn cho AI khi sử dụng tài liệu này

-   Đọc tài liệu gốc trước khi làm thay đổi kỹ thuật.
-   Dùng tài liệu này để hiểu tổng quan; dùng Architecture Revision 6.3
    cho quyết định kiến trúc và Implementation Plan cho thứ tự/phạm vi
    triển khai.
-   Khi trả lời, phân biệt `CONFIRMED`, `PROPOSED`, `OPEN`,
    `NEEDS VERIFICATION`.
-   Nếu thiếu tài liệu Revision 3/4/5 hoặc contract cụ thể, hãy yêu cầu
    bổ sung thay vì bịa nội dung.
-   Khi một thay đổi ảnh hưởng module khác, phải nêu rõ dependency và
    yêu cầu phối hợp.
-   Không coi nội dung do AI tự đề xuất là quyết định của nhóm cho đến
    khi được Architect/nhóm phê duyệt và ghi nhận.
