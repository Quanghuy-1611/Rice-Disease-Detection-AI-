# Cổng phát hành dữ liệu trước huấn luyện

Trạng thái: **CHƯA ĐƯỢC PHÉP TRAIN CHÍNH THỨC**

## Các kiểm tra kỹ thuật đã đạt

- [x] Đúng 11 nhãn mục tiêu; 9.294 ảnh sau cách ly.
- [x] Không có ảnh hỏng trong tập đã chọn.
- [x] Đã cách ly 17 ảnh xung đột ở vòng pHash <= 4 và thêm 19 ảnh cùng/gần cùng cảnh ở vòng rà soát pHash <= 8.
- [x] Split v3 dùng connected components theo so sánh toàn bộ cặp pHash trong từng nhãn, Hamming <= 8.
- [x] 6.505 train, 1.394 validation, 1.395 internal holdout; không nhóm nào đi qua nhiều split.
- [x] Audit toàn bộ cặp cho thấy 0 cặp cùng nhãn pHash <= 8 đi qua split.
- [x] Một va chạm chéo nhãn pHash=8 còn lại đã xem trực quan: BPH và bướm leaf roller là hai ảnh/đối tượng khác nhau, nên giữ lại.
- [x] Dataset, split và benchmark manifest v3 đã khóa SHA-256.
- [x] Bộ kiểm thử thuật toán đạt 5/5.

## Các mục còn chặn huấn luyện chính thức

- [ ] Chuyên gia xác nhận bảy nhãn rủi ro: bacterial leaf blight, blast, brown spot, dead heart, normal, tungro, weeds.
- [ ] Chốt ontology: dead heart/white head; weeds/cây lúa; golden apple snail có bao gồm trứng hay không.
- [ ] Khóa bộ test ngoại bộ độc lập, không tham gia làm sạch, chọn ảnh, cân bằng hay tinh chỉnh mô hình.
- [ ] Đăng ký trước metric và quy tắc chọn checkpoint trước khi mở test.

## Protocol bắt buộc

- Macro-F1 là tiêu chí chính; accuracy chỉ là phụ.
- Báo cáo balanced accuracy, từng lớp precision/recall/F1, confusion matrix, ECE, Brier và CI bootstrap.
- Augmentation động chỉ áp dụng cho train sau khi split; validation/test chỉ tiền xử lý xác định.
- Không dùng test để chọn epoch, augmentation, siêu tham số hoặc kiến trúc.
- Internal holdout và external test phải báo cáo riêng.