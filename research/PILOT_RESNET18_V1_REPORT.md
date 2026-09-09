# Báo cáo pilot ResNet18 v1 (không dùng test)

Ngày chạy: 2026-09-08

## Phạm vi

- Mục đích: kiểm tra pipeline học trên dataset v3, không phải kết quả chính thức của bài báo.
- Mô hình: ResNet18, official ImageNet weights.
- Seed: 42.
- Lịch: 2 epoch head + 3 epoch fine-tune.
- Dữ liệu được đọc: 6.505 train và 1.394 validation.
- Internal test và external test: không đọc, không đánh giá.

## Kết quả tốt nhất

- Epoch: 5 (fine-tune epoch 3).
- Validation accuracy: 0,7740.
- Validation Macro-F1: 0,7672.
- Validation loss: 0,6373.
- Train accuracy: 0,7998.
- Train Macro-F1: 0,7957.
- Thời gian: 288,6 giây.
- Checkpoint SHA-256: `e3d2b0013fac88ec4cebd093d41cd68ea2b425afaed86741db7f2e1f9a0fff85`.

## F1 validation theo lớp

| Nhãn | F1 |
|---|---:|
| bacterial_leaf_blight | 0,4930 |
| blast | 0,6740 |
| brown_planthopper | 0,9673 |
| brown_spot | 0,5427 |
| dead_heart | 0,9202 |
| golden_apple_snail | 0,9947 |
| leaf_roller | 0,9571 |
| normal | 0,6941 |
| stem_borer | 0,9494 |
| tungro | 0,6179 |
| weeds | 0,6292 |

## Nhầm lẫn chính

- normal → weeds: 50/134 (37,3%).
- brown_spot → blast: 35/135 (25,9%).
- tungro → blast: 34/134 (25,4%).
- bacterial_leaf_blight → weeds: 22/90 (24,4%).
- bacterial_leaf_blight → blast: 15/90 (16,7%).

## Diễn giải

Macro-F1 validation tăng theo từng epoch: 0,5533 → 0,5890 → 0,7179 → 0,7575 → 0,7672. Train và validation chỉ lệch khoảng 2,8 điểm Macro-F1, chưa cho thấy overfit nghiêm trọng trong pilot ngắn.

Các lớp côn trùng/ốc rất cao, trong khi các bệnh lá và nhóm normal/weeds thấp hơn rõ rệt. Điều này phù hợp với khác biệt thị giác của đối tượng và cảnh báo về độ khó/nhãn nguồn; không nên dùng accuracy chung để che các lớp yếu. Pilot không chứng minh khả năng tổng quát hóa vì chưa mở internal test và chưa có external test độc lập.
