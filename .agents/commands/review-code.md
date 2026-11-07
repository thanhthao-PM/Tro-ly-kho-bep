# Command: review-code

## Purpose
Review code hoặc diff để tìm lỗi logic, vi phạm contract, lỗ hổng bảo mật và nguy cơ hồi quy.

## Inputs
- Diff/commit hoặc danh sách file: `[phạm vi review]`
- Contract liên quan: `[tài liệu/mục nếu biết]`
- Review mode: `[read-only mặc định | đề xuất patch]`

## Procedure
1. Đọc `AGENTS.md` và contract liên quan đến phần thay đổi.
2. Xác định phạm vi diff; không review lại toàn repo nếu không cần.
3. Kiểm tra theo thứ tự ưu tiên:
   - Correctness và business invariants.
   - Tenant isolation, authentication, authorization, secret handling.
   - Transaction, concurrency, idempotency và data integrity.
   - API/schema compatibility và error handling.
   - Test coverage và regression.
   - Maintainability/readability.
4. Với database/ledger, kiểm tra dấu `qty_delta`/`value_vnd`, reversal, FEFO, cost snapshot, cache-vs-ledger, stock non-negative và commit-time constraints theo contract liên quan.
5. Kiểm tra mọi tuyên bố test/verification có log hoặc bằng chứng thực tế không.
6. Không sửa code trong read-only mode. Nếu được yêu cầu đề xuất patch, tách rõ findings và patch.

## Severity
- `BLOCKER`: có thể làm sai dữ liệu nghiêm trọng, phá invariant cốt lõi hoặc khiến hệ thống không thể chạy.
- `HIGH`: lỗi bảo mật, tenant leakage, sai nghiệp vụ quan trọng hoặc regression lớn.
- `MEDIUM`: lỗi có phạm vi hạn chế hoặc thiếu xử lý đáng kể.
- `LOW`: vấn đề nhỏ, không chặn tích hợp.

## Guardrails
- Không báo lỗi giả định như sự thật; ghi rõ điều kiện tái hiện và mức độ chắc chắn.
- Không coi việc bật RLS là đủ bảo vệ khi Core Mode dùng owner connection bypass RLS.
- Không yêu cầu D30a hoặc thay đổi kiến trúc nếu chưa được duyệt.
- Không biến style preference thành blocker.
- Không suy diễn contract từ tên hàm hoặc code nếu tài liệu nguồn không quy định.

## Output contract
Findings-first:
1. Findings theo severity, mỗi finding có file/dòng, tác động, bằng chứng và cách khắc phục.
2. Các điểm đã kiểm tra nhưng không phát hiện vấn đề (chỉ nêu nhóm quan trọng).
3. Test/log đã xem; không tự nhận đã chạy nếu chưa chạy.
4. Kết luận: `APPROVE | APPROVE WITH FOLLOW-UP | REQUEST CHANGES | BLOCKED`.
5. Câu hỏi cần owner quyết định (nếu có).

Nếu không có finding, nói rõ phạm vi review và giới hạn của review; không khẳng định code hoàn toàn an toàn.
