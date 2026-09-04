# Kế hoạch bài báo: So sánh sáu CNN cho nhận diện bệnh và đối tượng gây hại trên lúa

Phiên bản kế hoạch: 1.0  
Ngày lập: 25/08/2026  
Trạng thái dữ liệu test: **chưa mở**  
Protocol thực nghiệm chính: `rice_disease_backbone_benchmark_v2`

## 1. Định vị bài báo

### 1.1. Tên bài gợi ý

**Tiếng Việt**

> Đánh giá có kiểm soát độ chính xác và hiệu quả triển khai của sáu mạng nơ-ron tích chập trong nhận diện 19 nhóm bệnh và đối tượng gây hại trên lúa

**Tiếng Anh**

> A Controlled Accuracy–Efficiency Evaluation of Six Convolutional Neural Networks for 19-Class Rice Disease and Pest Recognition

Không dùng từ “detection” nếu đầu vào là một ảnh và đầu ra là một nhãn cho toàn ảnh. Bài này là **single-label image classification**, không phải object detection như YOLO.

### 1.2. Câu hỏi nghiên cứu

- **RQ1 — Chất lượng:** Trong cùng dữ liệu, split, tiền xử lý và quy trình huấn luyện, kiến trúc nào đạt Macro-F1 cao nhất trên 19 lớp?
- **RQ2 — Độ ổn định:** Thứ hạng có ổn định qua ba seed `42`, `123`, `2026` hay chỉ xuất hiện ở một lần train may mắn?
- **RQ3 — Lớp hiếm:** Kiến trúc nào giữ Recall/F1 tốt hơn cho các lớp ít mẫu, thay vì chỉ tốt ở các lớp chiếm đa số?
- **RQ4 — Hiệu quả:** Độ chính xác đổi lấy bao nhiêu tham số, dung lượng model, thời gian train, bộ nhớ GPU và độ trễ thực tế trên OPPO A54?
- **RQ5 — Triển khai:** MobileNetV3Large có nằm trên biên Pareto chất lượng–độ trễ để làm backbone cho RiceAI hay không?

### 1.3. Đóng góp nên tuyên bố

1. So sánh sáu backbone bằng **cùng một framework PyTorch/Torchvision và cùng protocol khóa trước khi mở test**.
2. Đánh giá cả chất lượng tổng thể, 19 lớp riêng biệt, độ bất định và độ biến thiên do seed.
3. Đánh giá chất lượng–hiệu quả, gồm chi phí huấn luyện và benchmark thiết bị thật theo cùng runtime.
4. Phát hành manifest split, hash dữ liệu/protocol, seed, checkpoint và mã tái lập.

Không tuyên bố “mô hình mới” vì sáu backbone là kiến trúc đã công bố. Giá trị khoa học nằm ở **benchmark có kiểm soát trên bài toán lúa**, dữ liệu 19 lớp và phân tích triển khai.

## 2. Sáu mô hình và lý do chọn

| Nhóm | Mô hình | Vai trò trong so sánh | Nguồn gốc |
|---|---|---|---|
| Mobile nhẹ | MobileNetV2 | Baseline mobile dùng inverted residual và linear bottleneck | Sandler et al., CVPR 2018 [R1] |
| Mobile nhẹ | MobileNetV3Large | Backbone đang định hướng triển khai RiceAI; được thiết kế có xét độ trễ phần cứng | Howard et al., ICCV 2019 [R2] |
| Residual | ResNet-18 | Baseline CNN kinh điển, đơn giản và mạnh nhờ residual learning | He et al., CVPR 2016 [R3] |
| Scaling | EfficientNet-B0 | Baseline dùng compound scaling cho độ sâu, rộng và độ phân giải | Tan & Le, ICML 2019 [R4] |
| Mobile nhẹ | ShuffleNetV2 1.0× | Đối chứng mobile nhấn mạnh tốc độ thật, memory access và đặc tính nền tảng | Ma et al., ECCV 2018 [R5] |
| Dense connectivity | DenseNet-121 | Đối chứng mạng sâu với feature reuse và kết nối dày đặc | Huang et al., CVPR 2017 [R6] |

Sáu mô hình đại diện cho các triết lý thiết kế khác nhau nhưng đều là CNN phân loại ảnh. Điều này giúp câu hỏi nghiên cứu tập trung: **kiến trúc backbone nào phù hợp nhất**, thay vì trộn CNN classification với detector như YOLO trong cùng bảng chính.

## 3. Dữ liệu và giới hạn diễn giải

### 3.1. Dữ liệu đã khóa

| Thuộc tính | Giá trị |
|---|---:|
| Tổng số ảnh sau làm sạch | 65.516 |
| Số lớp | 19 |
| Train | 45.858 (70%) |
| Validation | 9.829 (15%) |
| Test | 9.829 (15%) |
| Seed tạo split | 2026 |
| Cấp split | Stratified **theo ảnh** |
| Exact duplicate bị loại | 102 |
| Ảnh thuộc nhóm trùng nhưng khác nhãn bị loại | 1.724 |
| SHA256 manifest | `bc2c7c8c72a14968c402cbb06fc0eebdde57a8b00a5ac5c88962716f06024160` |

Nguồn nội bộ: `research/data/splits/rice_cleaned_v4_exact_cross_label_conflicts_excluded_v1.metadata.json`.

### 3.2. Mức mất cân bằng

- Lớp lớn nhất: `stem_borer`, 19.821 ảnh.
- Lớp nhỏ nhất: `southern_black_streaked_dwarf`, 80 ảnh.
- Tỷ lệ lớn nhất/nhỏ nhất: khoảng **247,8:1**.
- Test support dao động từ 12 đến 2.973 ảnh/lớp.

Vì vậy Accuracy có thể bị chi phối bởi các lớp lớn. Macro-F1 được đặt làm metric chính vì nó tính F1 từng lớp rồi lấy trung bình không trọng số, cho mỗi lớp một tiếng nói ngang nhau [R7, R8]. Loss dùng trọng số theo “effective number of samples”, cùng một cấu hình cho sáu model, dựa trên Cui et al. [R9].

### 3.3. Giới hạn bắt buộc phải ghi

Manifest không có ID ruộng, cây hay phiên chụp, nên đây **không phải group split**. Kết quả chỉ chứng minh khả năng tổng quát trên held-out images trong tập dữ liệu hiện có; chưa chứng minh tổng quát sang ruộng, mùa vụ, thiết bị hoặc địa phương mới. Data leakage có thể làm kết quả ML lạc quan quá mức, do đó bài phải mô tả quy trình loại duplicate và thừa nhận giới hạn split theo ảnh [R10].

Nếu sau này thu được metadata nguồn, làm thêm external/grouped test và trình bày như một thí nghiệm mở rộng; không thay split giữa chiến dịch hiện tại.

## 4. Protocol huấn luyện cố định

### 4.1. Thiết kế công bằng

Mỗi model dùng chính xác:

- PyTorch/Torchvision và official ImageNet-1K weights;
- ảnh RGB `224×224`, chuẩn hóa ImageNet giống nhau;
- batch size 32;
- Adam;
- head tối đa 15 epoch, fine-tune tối đa 30 epoch;
- early stopping patience 5 theo **Validation Macro-F1**;
- head LR `1e-3`, fine-tune LR `1e-5`;
- dropout 0,4;
- cùng augmentation;
- cùng effective-number class weighting: `beta=0.999`, clip `[0.25, 5.0]`;
- BatchNorm bị đóng băng ở cả hai giai đoạn;
- deterministic algorithms, TF32 tắt, `CUBLAS_WORKSPACE_CONFIG=:4096:8`;
- ba seed: `42`, `123`, `2026`.

Tổng số run chính: **6 model × 3 seed = 18 run**. Mỗi run chọn đúng một checkpoint bằng Validation Macro-F1. Test không được dùng để chọn epoch, hyperparameter, quantization hay model.

Protocol v1 và pilot MobileNetV2 cũ không đi vào kết quả chính. Các kết quả Keras/TensorFlow V2/V3 cũ chỉ được ghi ở phụ lục “legacy deployment reference”.

### 4.2. Độ tái lập

- Campaign lock v2 SHA256: `63f9c337986b3d4cfaf20c1745df85e2cfd36a95e7557e894decc781e87646b0`.
- Mỗi run phải giữ contract SHA, split SHA, model SHA, seed, environment và history.
- Không sửa tay bảng kết quả; bảng được sinh từ JSON/CSV.
- Nhiều lần train là cần thiết vì initialization, data order và augmentation tạo biến thiên đáng kể trong benchmark ML [R11]. Ba seed là mức thực dụng để ước lượng biến thiên huấn luyện, không phải chứng minh đã bao phủ toàn bộ nguồn biến thiên.

## 5. Thước đo chất lượng và cách diễn giải

Ký hiệu cho lớp `i`: `TP_i`, `FP_i`, `FN_i`; số lớp `K=19`; tổng ảnh test `N`.

| Thước đo | Công thức/cách tính | Vai trò trong bài | Cách đọc | Nguồn |
|---|---|---|---|---|
| Accuracy | `số dự đoán đúng / N` | Phụ | Tỷ lệ ảnh đúng tổng thể; dễ bị lớp lớn chi phối | [R7, R8] |
| Precision lớp i | `TP_i/(TP_i+FP_i)` | Chẩn đoán lớp | Khi model nói là lớp i thì đúng bao nhiêu | [R7, R8] |
| Recall lớp i | `TP_i/(TP_i+FN_i)` | Chẩn đoán lớp, rất quan trọng với bệnh hiếm | Trong ảnh thật của lớp i, bắt được bao nhiêu | [R7, R8] |
| F1 lớp i | `2P_iR_i/(P_i+R_i)` | Cân bằng Precision–Recall | Chỉ cao khi cả Precision và Recall cùng tốt | [R7, R8] |
| **Macro-F1** | `(1/K) Σ F1_i` | **Metric chính** | Mỗi lớp có trọng số ngang nhau, phù hợp dữ liệu 248:1 | [R7, R8] |
| Macro-Precision | Trung bình Precision của 19 lớp | Phụ | Khả năng hạn chế false positive trên toàn bộ lớp | [R7, R8] |
| Macro-Recall | Trung bình Recall của 19 lớp | Phụ | Khả năng bao phủ các lớp, không thiên lớp đông | [R7, R8] |
| Confusion matrix | Ma trận `true class × predicted class` | Phân tích lỗi | Cho biết cặp bệnh nào bị nhầm lẫn | [R7] |
| Mean ± sample SD qua seed | Trung bình và độ lệch chuẩn mẫu của 3 kết quả | Độ ổn định train | Mean là mức điển hình; SD lớn là nhạy seed | [R11] |
| 95% bootstrap CI của Macro-F1 | 2.000 lần resample theo phân phối thực nghiệm, percentile 2,5%–97,5% | Bất định do hữu hạn ảnh test | Khoảng hẹp hơn nghĩa là ước lượng ổn định hơn; không thay thế SD qua seed | [R12] |
| Paired bootstrap ΔMacro-F1 | Resample cùng ảnh và lấy `F1_A−F1_B` | So V3Large với từng model trên cùng seed | CI nằm hoàn toàn trên 0: bằng chứng A tốt hơn B trên tập test; CI cắt 0: chưa kết luận | [R12] |

### 5.1. Quy tắc kết luận model tốt nhất

1. Xếp hạng chính theo **mean Test Macro-F1 qua ba seed**.
2. Kiểm tra sample SD: không gọi một model “ổn định” nếu SD cao hơn rõ rệt.
3. Kiểm tra paired bootstrap `MobileNetV3Large − model khác` trên từng seed.
4. Kiểm tra F1/Recall của 19 lớp, đặc biệt các lớp có test support nhỏ.
5. Chỉ sau đó xét Accuracy và hiệu quả triển khai.

Không biến `probability_delta_gt_zero` thành p-value. Không viết “có ý nghĩa thống kê” chỉ vì điểm trung bình cao hơn; dùng cách diễn đạt “có/không có bằng chứng nhất quán trong bootstrap CI”. Vì có 3 seed và chỉ một dataset, không dùng Friedman/Nemenyi như thể có nhiều dataset độc lập.

### 5.2. Hai loại bất định không được trộn

- **Sample SD qua ba seed:** biến thiên do quá trình train.
- **Bootstrap CI trên test:** bất định do mẫu ảnh test hữu hạn, với model/seed đã cố định.

Bảng phải hiện cả hai; không lấy bootstrap của một seed để thay cho lặp nhiều seed.

## 6. Thước đo hiệu quả

| Nhóm | Thước đo | Thu ở đâu | Ý nghĩa | Nguồn/phương pháp |
|---|---|---|---|---|
| Độ phức tạp | Số tham số | Model PyTorch sau thay classifier | Chi phí lưu trữ và tính toán tiềm năng | Paper kiến trúc [R1–R6], đo trực tiếp bằng code |
| Độ phức tạp | Dung lượng checkpoint/export (MB) | File artifact | Chi phí phân phối/cập nhật model | Đo byte file, không suy từ tham số |
| Huấn luyện | Tổng thời gian train | Run manifest | Chi phí thực nghiệm | Cùng GPU/môi trường; báo riêng từng seed |
| Huấn luyện | Peak CUDA memory (MB) | PyTorch CUDA peak statistic | Khả năng train trên GPU giới hạn RAM | Cùng batch 32 và input 224 |
| Thiết bị | P50 latency (ms) | OPPO A54, batch 1 | Độ trễ điển hình | Android dùng median cho mức điển hình [R13] |
| Thiết bị | P95 latency (ms) | OPPO A54, batch 1 | Đuôi chậm, trải nghiệm trong trường hợp xấu | Android cũng báo các percentile cao để thấy lượt chậm [R13] |
| Thiết bị | Mean latency (ms) | OPPO A54, batch 1 | Trung bình số học, giữ để đối chiếu | Báo cùng P50/P95, không dùng riêng lẻ |
| Thiết bị | Initialization time (ms) | Lúc mở interpreter/model | Độ trễ trước suy luận đầu tiên | Đo riêng, không trộn inference latency |
| Thiết bị | PSS (MB) | `dumpsys meminfo` | Trọng lượng RAM vật lý có phân bổ trang chia sẻ | Android Developers [R14] |

Paper ShuffleNetV2 chỉ ra FLOPs không đủ để đại diện tốc độ thật vì còn memory access cost và đặc tính nền tảng [R5]. Do đó:

- **không xếp hạng tốc độ chỉ bằng FLOPs**;
- benchmark cả sáu model trên **cùng OPPO A54, cùng runtime, cùng precision/quantization, 4 CPU threads, batch 1**;
- 50 warm-up;
- 3 vòng × 300 lượt/model;
- cố định nguồn điện, tắt ứng dụng nền, để máy nguội về cùng khoảng nhiệt độ trước mỗi model;
- đảo hoặc random hóa thứ tự model giữa các vòng để giảm thiên lệch nhiệt;
- ghi Android version, SoC, runtime version và temperature/battery state nếu lấy được.

Số V2/V3 đã đo trước đây không được ghép với bốn model mới nếu runtime, build hoặc quantization khác. Chúng chỉ là số tham khảo legacy cho đến khi chạy lại cả sáu dưới cùng protocol.

### 6.1. Không tạo “điểm tổng hợp” tùy ý

Không cộng Macro-F1, latency và dung lượng thành một score tự đặt vì trọng số sẽ chủ quan. Dùng **Pareto frontier**:

- một model bị dominated nếu có model khác vừa Macro-F1 cao hơn hoặc bằng, vừa latency thấp hơn hoặc bằng, và ít nhất một tiêu chí tốt hơn nghiêm ngặt;
- model triển khai được chọn trong nhóm không bị dominated;
- nếu MobileNetV3Large đạt chất lượng tốt nhất nhưng chậm hơn, báo rõ trade-off thay vì che bằng điểm tổng hợp.

## 7. Quy trình phân tích sau khi 18 run hoàn tất

### Giai đoạn A — Chỉ validation, test vẫn khóa

1. Xác nhận đủ 18 `run_manifest.json` có `status=complete`.
2. Xác nhận contract/split/class-map/preprocessing hash giống nhau.
3. Vẽ learning curves train/validation loss và Macro-F1.
4. Kiểm tra early stopping, best epoch, lỗi NaN và run bất thường.
5. Không loại một seed chỉ vì điểm thấp; chỉ loại khi có lỗi kỹ thuật có log và phải chạy lại cùng seed.

### Giai đoạn B — Mở test đúng một lần

Chỉ chạy khi 18 run sạch và bản Methods/Statistical Analysis Plan đã được đóng băng:

```powershell
cd "D:\Phát hiện bệnh cây lúa"
& ".\model_benchmark\.venv\Scripts\python.exe" ".\model_benchmark\src\final_evaluate_v2.py" --unlock-test I_UNDERSTAND_TEST_IS_FINAL
```

Script phải tạo:

- metric của từng model/seed;
- per-class Precision/Recall/F1/support;
- confusion matrix;
- prediction probability cho từng ảnh;
- mean và sample SD qua seed;
- 95% bootstrap CI Macro-F1;
- paired bootstrap V3Large so với năm model còn lại;
- audit thời điểm mở test.

Không sửa hyperparameter hoặc retrain dựa trên test sau bước này. Nếu tìm thấy bug, phải công khai lỗi, phiên bản protocol mới và lý do; không âm thầm thay kết quả.

### Giai đoạn C — Hiệu quả trên thiết bị

1. Khóa định dạng export và runtime chung cho cả sáu.
2. Xác nhận sai lệch dự đoán sau export so với PyTorch FP32 trên validation.
3. Chọn quantization bằng validation, không test.
4. Benchmark OPPO A54 theo protocol ở Mục 6.
5. Sinh bảng tự động từ JSON benchmark.

## 8. Bảng và hình bắt buộc

### Bảng chính

1. **Bảng 1 — Dataset:** 19 lớp, số mẫu train/validation/test và imbalance ratio.
2. **Bảng 2 — Protocol:** input, pretrained weights, optimizer, LR, epoch, augmentation, class weighting, seed.
3. **Bảng 3 — Kết quả chính:** từng model với Accuracy, Macro-P/R/F1 `mean ± SD`; tô đậm mean Macro-F1 cao nhất nhưng không dùng màu để ám chỉ significance.
4. **Bảng 4 — Theo lớp:** Precision/Recall/F1/support của 19 lớp; dùng mean qua seed hoặc đưa đầy đủ vào phụ lục.
5. **Bảng 5 — Hiệu quả:** params, model MB, train time, peak VRAM, P50/P95/mean/init/PSS trên OPPO A54.
6. **Bảng 6 — Paired comparison:** ΔMacro-F1 V3Large trừ từng model, CI95 theo seed.

### Hình chính

1. Histogram số ảnh của 19 lớp theo log scale.
2. Learning curve Macro-F1 theo epoch cho từng model/seed.
3. Confusion matrix chuẩn hóa theo hàng cho mỗi model, hoặc top-3 model ở bài chính và đủ sáu ở phụ lục.
4. Forest plot ΔMacro-F1 và CI95 so với V3Large.
5. Scatter/Pareto plot: trục X P50 latency, trục Y mean Macro-F1, kích thước điểm là model size.
6. Bar/point plot F1 theo lớp cho top-3 model, đánh dấu support lớp.

Mọi figure phải ghi rõ là validation hay test, seed nào hoặc đã aggregate thế nào.

## 9. Khung bài báo chi tiết

### Abstract — 200–250 từ

1. Bối cảnh nhận diện bệnh lúa trên thiết bị tài nguyên hạn chế.
2. Khoảng trống: nhiều nghiên cứu báo Accuracy của một model hoặc dùng protocol không đồng nhất.
3. Phương pháp: 65.516 ảnh, 19 lớp, 6 CNN, 3 seed, cùng protocol, test khóa, benchmark OPPO A54.
4. Kết quả: chỉ điền sau test; báo Macro-F1 `mean±SD`, CI và latency của model nổi bật.
5. Kết luận: nêu trade-off, không viết “vượt trội” nếu CI không hỗ trợ.

### 1. Introduction — khoảng 900–1.100 từ

- Tác hại của bệnh/sâu hại lúa và nhu cầu chẩn đoán ảnh.
- Ràng buộc mobile: accuracy chưa đủ, cần latency, RAM, dung lượng.
- Nhược điểm thường gặp: lệch lớp, một seed, chỉ Accuracy, FLOPs thay tốc độ thật.
- Research questions RQ1–RQ5.
- Tóm tắt bốn đóng góp.

### 2. Related Work — khoảng 1.000–1.300 từ

- CNN/transfer learning cho plant/rice disease; phần này cần systematic literature search riêng.
- Nhóm mobile CNN: V2, V3Large, ShuffleNetV2.
- Nhóm general-purpose: ResNet18, EfficientNetB0, DenseNet121.
- Khoảng trống mà benchmark hiện tại giải quyết.

Không dùng paper gốc ImageNet để chứng minh hiệu quả trên bệnh lúa; chúng chỉ chứng minh nguồn gốc và nguyên lý kiến trúc. Claims rice-specific phải đến từ kết quả của mình hoặc literature rice-disease phù hợp.

### 3. Materials and Methods — khoảng 1.800–2.300 từ

- Nguồn dữ liệu, 19 nhãn, quy trình làm sạch và duplicate policy.
- Split 70/15/15, seed 2026, giới hạn image-level.
- Sáu kiến trúc và official weights.
- Tiền xử lý, augmentation và class-balanced weighting.
- Hai giai đoạn huấn luyện, optimizer, LR, stopping, BN policy.
- Ba seed và deterministic settings.
- Metric/công thức, bootstrap, paired comparison.
- Protocol benchmark thiết bị.
- Hardware/software và hash tái lập.

### 4. Results — khoảng 1.300–1.700 từ

- Chất lượng tổng thể (Bảng 3), không giải thích nguyên nhân quá sớm.
- Độ ổn định qua seed.
- Theo lớp và confusion matrix.
- Paired bootstrap.
- Chi phí huấn luyện và mobile benchmark.
- Pareto quality–efficiency.

### 5. Discussion — khoảng 1.200–1.600 từ

- Trả lời lần lượt RQ1–RQ5.
- Vì sao một số kiến trúc có trade-off quan sát được; ghi là giả thuyết nếu chưa có ablation.
- Ý nghĩa cho RiceAI Basic/Plus.
- So sánh với literature nhưng phải cân nhắc khác dataset/split/classes; không so trực tiếp % như cùng benchmark.
- Hạn chế: image-level split, long-tail cực mạnh, 3 seed, một thiết bị, chưa external field test, nhãn có thể nhiễu.
- Future work: grouped/external dataset, calibration, Grad-CAM/Hybrid-CAM, detection/segmentation là study riêng.

### 6. Conclusion — khoảng 250–350 từ

- Một câu cho kết quả chất lượng.
- Một câu cho độ ổn định/bất định.
- Một câu cho trade-off triển khai.
- Một câu về giới hạn và hướng external validation.

### Supplementary material

- Full class distribution và mapping 19 lớp.
- Full hyperparameters/config JSON.
- Kết quả từng seed.
- 6 confusion matrices.
- 19-class metrics từng seed.
- Hash manifest/checkpoint/code.
- Legacy V2/V3 Keras/OPPO benchmark, ghi rõ không thuộc primary comparison.

## 10. Dự kiến kết quả và nguyên tắc không “đoán trước kết quả”

Trước khi test chỉ được phát biểu **giả thuyết**, không điền số dự kiến:

- V3Large/EfficientNetB0 có thể cho chất lượng tốt nhưng chưa chắc thắng trên lớp hiếm.
- ShuffleNetV2/V2 có thể có lợi thế latency/dung lượng nhưng phải đo thật vì FLOPs không đủ.
- DenseNet121 có thể tiêu tốn train VRAM cao hơn; smoke test chỉ là bằng chứng feasibility, không phải kết quả bài báo.
- ResNet18 có thể là baseline cân bằng; phải để Macro-F1, CI và mobile benchmark quyết định.

Không đưa smoke-test VRAM vào bảng kết quả cuối; phải lấy số từ các run chính. Không đưa pilot validation Macro-F1 0,950145 của V2 vào primary result.

## 11. Tiêu chí hoàn thành và lịch triển khai

### Mốc 1 — Training

- [ ] Đủ 18 run v2, không test access.
- [ ] Audit artifact và learning curves.
- [ ] Đóng băng bản Methods và Statistical Analysis Plan.

### Mốc 2 — Final evaluation

- [ ] Mở test đúng một lần.
- [ ] Sinh bảng chất lượng và paired bootstrap tự động.
- [ ] Kiểm tra per-class, CI, seed variability.

### Mốc 3 — Deployment benchmark

- [ ] Khóa export/runtime/precision chung.
- [ ] Benchmark đủ sáu model trên OPPO A54.
- [ ] Vẽ Pareto quality–latency.

### Mốc 4 — Viết

- [ ] Viết Methods trước Results.
- [ ] Điền Results từ artifact, không chép tay.
- [ ] Viết Discussion sau khi đã trả lời RQ1–RQ5.
- [ ] Hoàn thiện supplementary/reproducibility package.
- [ ] Internal review: kiểm tra mọi con số có đường dẫn đến JSON/CSV nguồn.

## 12. Bản đồ nguồn dẫn chứng

### Paper gốc kiến trúc

- **[R1]** Sandler, M. et al. (2018). *MobileNetV2: Inverted Residuals and Linear Bottlenecks*. CVPR. https://openaccess.thecvf.com/content_cvpr_2018/html/Sandler_MobileNetV2_Inverted_Residuals_CVPR_2018_paper.html
- **[R2]** Howard, A. et al. (2019). *Searching for MobileNetV3*. ICCV. https://openaccess.thecvf.com/content_ICCV_2019/papers/Howard_Searching_for_MobileNetV3_ICCV_2019_paper.pdf
- **[R3]** He, K. et al. (2016). *Deep Residual Learning for Image Recognition*. CVPR. https://openaccess.thecvf.com/content_cvpr_2016/html/He_Deep_Residual_Learning_CVPR_2016_paper.html
- **[R4]** Tan, M. & Le, Q. V. (2019). *EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks*. ICML/PMLR. https://proceedings.mlr.press/v97/tan19a.html
- **[R5]** Ma, N. et al. (2018). *ShuffleNet V2: Practical Guidelines for Efficient CNN Architecture Design*. ECCV. https://www.ecva.net/papers/eccv_2018/papers_ECCV/html/Ningning_Light-weight_CNN_Architecture_ECCV_2018_paper.php
- **[R6]** Huang, G. et al. (2017). *Densely Connected Convolutional Networks*. CVPR. https://openaccess.thecvf.com/content_cvpr_2017/html/Huang_Densely_Connected_Convolutional_CVPR_2017_paper.html

### Metric, bất định và độ tái lập

- **[R7]** Sokolova, M. & Lapalme, G. (2009). *A systematic analysis of performance measures for classification tasks*. Information Processing & Management, 45(4), 427–437. https://doi.org/10.1016/j.ipm.2009.03.002
- **[R8]** scikit-learn. *Metrics and scoring: quantifying the quality of predictions* — định nghĩa Precision, Recall, F1 và macro averaging. https://scikit-learn.org/stable/modules/model_evaluation.html
- **[R9]** Cui, Y. et al. (2019). *Class-Balanced Loss Based on Effective Number of Samples*. CVPR. https://openaccess.thecvf.com/content_CVPR_2019/html/Cui_Class-Balanced_Loss_Based_on_Effective_Number_of_Samples_CVPR_2019_paper.html
- **[R10]** Kapoor, S. & Narayanan, A. (2023). *Leakage and the reproducibility crisis in machine-learning-based science*. Patterns, 4(9), 100804. https://doi.org/10.1016/j.patter.2023.100804
- **[R11]** Bouthillier, X. et al. (2021). *Accounting for Variance in Machine Learning Benchmarks*. MLSys. https://proceedings.mlsys.org/paper_files/paper/2021/file/0184b0cd3cfb185989f858a1d9f5c1eb-Paper.pdf
- **[R12]** Efron, B. (1979). *Bootstrap Methods: Another Look at the Jackknife*. The Annals of Statistics, 7(1), 1–26. https://doi.org/10.1214/aos/1176344552

### Benchmark mobile

- **[R13]** Android Developers. *Capture Macrobenchmark metrics* — median và các percentile cao trong phân tích latency. https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics
- **[R14]** Android Developers. *dumpsys* — định nghĩa và cách đo PSS/RSS/USS. https://developer.android.com/tools/dumpsys

## 13. Câu mẫu để viết đúng mức bằng chứng

**Đúng:**

> MobileNetV3Large đạt mean Macro-F1 cao hơn ResNet-18 trong ba seed. Paired bootstrap CI của chênh lệch nằm [điền khoảng], cho thấy [có/chưa có] bằng chứng nhất quán về ưu thế trên test set khóa.

> Kết quả được đo trên split theo ảnh; vì không có metadata ruộng/cây/phiên chụp, khả năng tổng quát ngoài miền cần được xác nhận bằng external field test.

**Tránh:**

> MobileNetV3Large chắc chắn tốt nhất cho mọi bệnh lúa.

> Accuracy cao chứng minh model nhận diện tốt tất cả 19 lớp.

> FLOPs thấp nên chắc chắn chạy nhanh nhất trên điện thoại.

> CI của hai model chồng lấn nên chúng hoàn toàn giống nhau.

