# Nhật ký hiệu chỉnh nhãn dataset_v4

Ngày hiệu chỉnh: 2026-09-07

## Hispa và weeds

- Kiểm tra trực quan mẫu cho thấy thư mục `hispa` chứa ảnh cỏ dại, còn thư mục `weeds` chứa ảnh bọ hispa.
- 10 ảnh bọ hispa còn lại trong thư mục `weeds` được chuyển, không xóa vĩnh viễn, sang `research/quarantine_manual_review/removed_hispa_mislabeled_as_weeds`.
- Thư mục `research/dataset_v4/hispa` được đổi thành `research/dataset_v4/weeds`.
- 1.592 tên tệp có tiền tố `hispa_` được đổi sang tiền tố `weeds_`.
- Sau hiệu chỉnh, `research/dataset_v4` không còn thư mục nhãn `hispa`.

## Lưu ý tái lập

- Người dùng đã loại thủ công một số ảnh không liên quan trước khi lập nhật ký này; danh sách đường dẫn và số lượng ban đầu của các ảnh đó không còn để phục hồi từ thư mục hiện tại.
- Các ảnh trong khu cách ly không được đưa vào bước làm sạch, chia tập hoặc huấn luyện tiếp theo.
