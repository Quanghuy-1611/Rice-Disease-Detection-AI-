# Báo cáo xác minh thuật toán dữ liệu trước huấn luyện

Ngày cập nhật: 2026-09-08

## Kết quả v3

- Dataset: 9.294 ảnh, 11 nhãn.
- Split: 6.505 train, 1.394 validation, 1.395 internal holdout.
- Split SHA-256: `81c2a913483cf235c6c322c783b28e8b9b7ea14d7d73be2e92259e7e7771b9d9`.
- Dataset content SHA-256: `4aeaf21fbe811d895652f4d39e43c2bff5e4719586468098aa53e6468516e61e`.
- Benchmark manifest SHA-256: `b2d62ff3387e155242427ad089b67ad20adfac7ebe3837ff6cfbf4e55cc19401`.
- 5/5 unit tests đạt, gồm test hồi quy cho trường hợp Hamming=8 mà LSH theo byte có thể bỏ sót.

## Sửa lỗi thuật toán

Phiên bản cũ dùng LSH theo tám band 8-bit. Cách đó không bảo đảm tìm đủ mọi cặp ở Hamming=8: hai hash có thể khác đúng một bit trong mỗi byte và không có band nào giống hệt. V3 thay bằng so sánh chính xác toàn bộ cặp trong từng nhãn rồi lấy connected components. Với tối đa khoảng 900 ảnh/nhãn, chi phí này phù hợp và dễ kiểm toán.

## Audit toàn bộ cặp pHash v3

- Hamming <= 2: 606 cặp; 0 chéo nhãn; 0 chéo split.
- Hamming <= 4: 1.341 cặp; 0 chéo nhãn; 0 chéo split.
- Hamming <= 6: 2.446 cặp; 7 chéo nhãn; 0 chéo split.
- Hamming <= 8: 3.836 cặp; 24 chéo nhãn; 1 chéo split.

Mười chín ảnh thuộc các cảnh ruộng bị gắn chéo blast/tungro/weeds/normal đã được xem trực quan và chuyển vào `quarantine_cross_label_conflicts_phash8_reviewed`. Các cảnh báo côn trùng còn lại là ảnh khác đối tượng nhưng bố cục tương tự, không bị xóa. Cặp duy nhất chéo split ở ngưỡng 8 là `brown_planthopper_0152.jpg` và `leaf_roller_0644.jpg`; xem ảnh xác nhận đây là hai loài và hai ảnh khác nhau, nên là false positive của pHash.

## Giới hạn khoa học còn lại

pHash không chứng minh hai ảnh cùng cây, ruộng hoặc phiên chụp; crop mạnh vẫn có thể lọt. Provenance của dữ liệu cũ không đủ để group chắc chắn theo nguồn/cây/ruộng. Nhãn nguồn được giữ theo lựa chọn phương pháp, vì vậy đây vẫn là một giới hạn cần nêu trong bài báo. Internal holdout không được gọi là external test; kết quả internal và external phải báo cáo riêng.

## Kết luận

Toàn vẹn kỹ thuật của dataset/split v3 đã đạt. Bộ external test độc lập đã được khóa và campaign huấn luyện chính thức được phép bắt đầu.
## Preflight cuối

- Audit release-readiness xác nhận dataset, selection và split đều khớp 9.294/9.294 ảnh.
- Không có bản sao SHA-256 hoặc decoded-pixel SHA đi qua nhiều split.
- Metadata benchmark v3 đã được tái tạo bằng generator theo schema `riceai-image-split/v1` và được `benchmark_common.load_locked_inputs` chấp nhận.
- Preflight chế độ `--verify-images` đã băm lại đủ 9.294/9.294 ảnh và đạt.
- Entry point kiểm tra tính hợp lệ của contract/manifest trước release gate, tránh gate đóng che giấu lỗi cấu hình.
- External test: 1.100 ảnh, 11 nhãn, 100 ảnh mỗi nhãn; không có trùng SHA-256, decoded-pixel SHA hoặc canonical pHash trong bộ cuối; mọi ảnh cách dataset v3 hơn 8 bit pHash.
- Duyệt trực quan đã loại ảnh BPH bẫy dính và tranh minh họa; bản khóa dùng ảnh cận cảnh/hiện trường.
- Audit release-readiness đạt 8/8 kiểm tra; model smoke và training smoke CUDA đạt cho cả sáu backbone ở batch size 32.
- Campaign lock: `model_benchmark/config/campaign_lock_11class_v1.json`; launcher xác nhận `TRAINING_GATE_OK` với ba seed 42, 123 và 2026.