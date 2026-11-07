# Command: prepare-handoff

## Purpose
Tạo bản bàn giao ngắn gọn để người khác hoặc một AI web khác tiếp tục mà không phải đọc lại toàn bộ lịch sử.

## Inputs
- Task/phase vừa thực hiện: `[task]`
- Người/AI nhận bàn giao: `[recipient]`
- Repo/ZIP hoặc commit: `[identifier/path]`

## Procedure
1. Đọc trạng thái hiện tại và diff; chỉ kiểm tra các file liên quan.
2. Đối chiếu `BUILD_STATUS.md`, `HANDOFF.md`, README và test evidence nếu tồn tại.
3. Ghi rõ thay đổi thực tế, file được tạo/sửa/xóa và điểm chưa hoàn tất.
4. Phân biệt:
   - Đã implement.
   - Đã test tự động.
   - Đã kiểm chứng thủ công trên môi trường cụ thể.
   - Chưa kiểm chứng.
5. Ghi rõ quyết định OPEN, blocker, tài liệu thiếu và giả định không được xác nhận.
6. Đưa ra đúng thứ tự các bước tiếp theo; không giao lại việc đã hoàn thành.
7. Nếu bàn giao qua ZIP, kiểm tra ZIP có đúng source mới nhất, không chứa `.env`, secret, cache, virtualenv hoặc dữ liệu cá nhân.

## Guardrails
- Không nói “chạy được” nếu chỉ tạo source hoặc syntax-check.
- Không nói “đã tích hợp” nếu chỉ tạo các file rời.
- Không tự đóng decision hoặc thay đổi scope.
- Không đưa secret/token/password vào handoff.
- Không che giấu test fail, file thiếu hoặc giới hạn môi trường.

## Output contract
# Handoff
- **Task/phase:**
- **Overall status:** `DONE | PARTIAL | BLOCKED`
- **Repo/commit/ZIP:**
- **Implemented:**
- **Files changed:**
- **Tests executed and evidence:**
- **Manual verification:**
- **Not verified / not run:**
- **Open decisions / blockers:**
- **Next actions (ordered):**
- **Instructions for recipient:**

Giữ handoff đủ ngắn để dán vào một AI web chat; ưu tiên sự thật có thể kiểm chứng hơn mô tả dài.
