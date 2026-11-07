# Command: project-check

## Purpose
Kiểm tra trạng thái repo và mức độ phù hợp với tài liệu dự án mà không tự ý sửa code.

## When to use
- Bắt đầu một phiên làm việc mới.
- Nhận repo hoặc ZIP từ AI khác.
- Trước khi chuyển phase hoặc bàn giao.

## Inputs
- Repo hoặc ZIP hiện tại.
- Phạm vi cần kiểm tra (nếu có): `[toàn dự án | phase | module]`.

## Procedure
1. Đọc `AGENTS.md` trước. Chỉ mở thêm tài liệu nguồn liên quan đến phạm vi.
2. Xác định đúng phiên bản Architecture, Implementation Plan và các quyết định đã được owner phê duyệt.
3. Kiểm tra cấu trúc thư mục, file cấu hình, code, migration và test có liên quan; không dump toàn bộ repo.
4. Đối chiếu implementation với contract nguồn. Phân biệt:
   - Đã có trong tài liệu.
   - Đã được implement trong source.
   - Đã được xác minh bằng test thực thi.
   - Chưa có bằng chứng / chưa kiểm chứng.
5. Ghi rõ file hoặc tài liệu bị thiếu. Không tự dựng nội dung Revision 3/4 hoặc contract không có trong bộ tài liệu.
6. Nêu các blocker, sai lệch, rủi ro và việc cần owner quyết định.
7. Không sửa file trong command này, trừ khi người dùng yêu cầu riêng.

## Guardrails
- Architecture Revision 6.3 là Core baseline FROZEN.
- Không tự đóng các quyết định OPEN. D20 có khác biệt trạng thái giữa Revision 6.3 và Implementation Plan; phải báo cáo, không âm thầm hòa giải.
- D30a vẫn PROPOSED / DISABLED. Không triển khai custom roles, ownership transfer hoặc D30a policies.
- Không xem code/migration/test là quyền sửa kiến trúc.
- Core Ledger tests không được đề xuất cắt để tiết kiệm thời gian.

## Output contract
Báo cáo ngắn theo thứ tự:
1. Kết luận tổng quan: `PASS | PASS WITH ISSUES | BLOCKED`.
2. Những phần đã kiểm tra (liệt kê file/phạm vi).
3. Findings theo mức `BLOCKER | HIGH | MEDIUM | LOW`, kèm đường dẫn và dòng nếu xác định được.
4. Những gì đã chạy và kết quả chính xác.
5. Những gì chưa chạy/chưa kiểm chứng.
6. OPEN decisions hoặc tài liệu thiếu.
7. Bước tiếp theo nhỏ nhất, có thể thực hiện an toàn.

## Token efficiency
Chỉ đọc file liên quan; ưu tiên tìm kiếm theo tên/đường dẫn và diff. Không đọc lại file không đổi nếu không cần. Không tạo báo cáo lặp lại; cập nhật báo cáo hiện có khi được yêu cầu.
