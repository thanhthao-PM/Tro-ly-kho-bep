# Command: implement-module

## Purpose
Triển khai một module hoặc lát cắt chức năng nhỏ, có kiểm thử và bàn giao rõ ràng.

## Required inputs
- Task/module: `[tên module]`
- Contract/nguồn được duyệt: `[tài liệu + mục]`
- Acceptance criteria: `[điều kiện hoàn thành]`
- Phase: `[phase hiện tại]`

Nếu thiếu contract hoặc tiêu chí khiến không thể triển khai an toàn, hỏi đúng một câu làm rõ hoặc dừng tại blocker.

## Procedure
1. Đọc `AGENTS.md`; chỉ đọc Agent/Skill liên quan. Chọn một vai trò chính và các vai trò hỗ trợ cần thiết. Nếu nền tảng không hỗ trợ gọi Agent/Skill thật, áp dụng hướng dẫn tương ứng trong ngữ cảnh hiện tại.
2. Chạy `project-check` ở phạm vi module hoặc thực hiện preflight tương đương.
3. Xác nhận phase prerequisites. Phase 0 phải xác minh U1, U10, U12, U13 theo tài liệu và ghi fallback; không giả định đã hoàn tất.
4. Kiểm tra contract, dependencies, code hiện có và test liên quan. Không tự phát minh API/schema/enum/behavior còn thiếu.
5. Nếu gặp quyết định OPEN có ảnh hưởng trực tiếp, dừng phần bị ảnh hưởng và lập câu hỏi/Change Proposal; tiếp tục phần độc lập nếu an toàn.
6. Implement thay đổi nhỏ nhất đáp ứng acceptance criteria; giữ kiến trúc modular monolith và các invariant dữ liệu.
7. Thêm/cập nhật test phù hợp. Không sửa yếu test hoặc bỏ assertion chỉ để làm test xanh.
8. Chạy test mục tiêu trước, sau đó các Core tests bắt buộc bị ảnh hưởng.
9. Cập nhật tài liệu trạng thái/handoff nếu task yêu cầu.

## Guardrails
- Ledger-first; FEFO; snapshot giá vốn theo batch; stock không âm.
- `kitchen_id` phải được áp dụng đúng cho truy vấn tenant; composite FK theo contract.
- Alembic là nguồn duy nhất thay đổi schema.
- Core Mode dùng `ADMIN_DATABASE_URL` theo Implementation Plan. Không tự đổi sang `app_runtime`.
- D30a PROPOSED / DISABLED.
- Không tích hợp OCR hoặc External LLM vào Core MVP.
- Không tự chọn CSS framework khi chưa có quyết định.
- Không triển khai Stretch trước khi Core hoàn tất, trừ khi được owner yêu cầu rõ.

## Output contract
- Tóm tắt thay đổi.
- Danh sách file tạo/sửa.
- Contract và acceptance criteria đã đáp ứng/chưa đáp ứng.
- Test đã chạy: lệnh, kết quả, môi trường.
- Test chưa chạy và lý do.
- OPEN decisions/blockers.
- Hướng dẫn tích hợp/chạy tiếp.
- Không tuyên bố “hoàn tất” nếu chưa có bằng chứng tương ứng.

## Token efficiency
Không viết lại file không liên quan. Ưu tiên patch/diff. Không gửi lại toàn bộ source trong báo cáo; chỉ nêu đường dẫn và phần thay đổi.
