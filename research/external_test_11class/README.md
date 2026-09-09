# External test set — không dùng để huấn luyện

Thư mục này chỉ nhận ảnh test ngoại bộ cho 11 nhãn đã khóa.

## Quy tắc bắt buộc

- Ảnh phải đến từ nguồn khác với `dataset_11_curated`, ưu tiên cây/ruộng/thiết bị/phiên chụp khác.
- Không sao chép ảnh từ `dataset_v4` hoặc các thư mục nguồn hiện có trong dự án.
- Không augmentation, crop hàng loạt hoặc nhân bản để tăng số lượng test.
- Giữ thông tin nguồn, ngày thu thập và người xác nhận nhãn trong manifest riêng.
- Trước khi mở test, phải so SHA-256, decoded-pixel hash và perceptual hash với toàn bộ train/validation.
- Test không được dùng để chọn epoch, kiến trúc, threshold hoặc siêu tham số.
- Sau lần đánh giá chính thức đầu tiên, không chỉnh mô hình rồi báo lại điểm trên cùng test như một phép thử mới.

## Số lượng mục tiêu

- Khuyến nghị: 150–300 ảnh độc lập mỗi nhãn.
- Tối thiểu tạm chấp nhận: 50–100 ảnh mỗi nhãn, kèm khoảng tin cậy và cảnh báo support thấp.

Hiện trạng: thư mục chỉ có cấu trúc nhãn, chưa có ảnh và chưa được mở bởi quy trình đánh giá.
