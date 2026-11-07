# Command: run-tests

## Purpose
Chạy đúng bộ test liên quan, ghi lại bằng chứng và không làm yếu tiêu chí kiểm thử.

## Inputs
- Phạm vi: `[module | phase | toàn bộ Core]`
- Môi trường: `[local/CI/Windows/other]`
- Lệnh test đã biết (nếu có): `[commands]`

## Procedure
1. Đọc `AGENTS.md`, test configuration và hướng dẫn chạy test liên quan.
2. Xác định test tier: unit, integration, Core DB, Core integration, E2E hoặc Stretch.
3. Kiểm tra prerequisites và environment variables; không in secret ra log.
4. Chỉ dùng lệnh được khai báo trong repo/tài liệu hoặc xác minh từ cấu hình. Nếu chưa biết lệnh, inspect scripts/config trước; không đoán.
5. Chạy test mục tiêu trước. Sau đó chạy các Core tests bị ảnh hưởng và bộ Core bắt buộc theo phase khi phù hợp.
6. Ghi lại exit code, số test pass/fail/skip, lỗi đầu tiên có ý nghĩa và môi trường.
7. Nếu test fail, phân loại: code defect, environment/setup, test defect, missing prerequisite hoặc chưa rõ.
8. Không sửa test để che lỗi. Nếu cần sửa code/test, yêu cầu task triển khai riêng hoặc được ủy quyền rõ ràng.

## Guardrails
- Không giả lập kết quả chạy thật.
- Không đánh đồng syntax check với runtime test.
- Không đánh đồng SQLite với PostgreSQL/Supabase verification.
- Không đánh đồng CI pass với Windows manual verification.
- Không bỏ Core Ledger tests L1-L3, C6 hoặc Core Integration tests để tiết kiệm thời gian.
- Stretch có thể hoãn trước Core tests.
- Không chạy migration phá hủy hoặc reset database production.

## Output contract
| Test suite | Command | Environment | Result | Evidence / limitation |
|---|---|---|---|---|

Kèm:
- Tổng kết `PASS | FAIL | BLOCKED | NOT RUN`.
- Test chưa chạy và lý do.
- Những môi trường/hành vi chưa kiểm chứng.
- Bước tiếp theo để xử lý lỗi.

## Token efficiency
Không dán toàn bộ log. Trích lỗi đầu tiên và phần context cần thiết; lưu log đầy đủ thành artifact nếu môi trường hỗ trợ.
