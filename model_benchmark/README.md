# RiceAI backbone benchmark

Thư mục này là mã nguồn độc lập cho bài so sánh 6 backbone phân loại 19 lớp:
MobileNetV2, MobileNetV3Large, ResNet-18, EfficientNet-B0, ShuffleNetV2 1.0x
và DenseNet-121. Cả sáu model được train mới bằng cùng PyTorch/Torchvision và
ba seed `42`, `123`, `2026`. Dữ liệu, split và artifact lịch sử vẫn nằm trong
`research/`, nhưng kết quả TensorFlow V2/V3 cũ không đi vào bảng chính.

## Quy chuẩn không được thay đổi giữa model

- Một split CSV khóa cứng, seed `2026`, 70/15/15, stratified theo **ảnh**.
- 19 lớp và chính sách loại exact/cross-label duplicate lấy trực tiếp từ metadata.
- Ảnh RGB 224×224; checkpoint chỉ chọn theo Validation Macro-F1.
- Không đọc test khi tune, chọn checkpoint, chọn TFLite hoặc thay hyperparameter.
- Mỗi artifact bắt buộc mang SHA256 của contract, CSV split và model.
- Bảng tổng hợp tự từ chối artifact có contract/split/class-map/preprocessing khác nhau.

Lưu ý khoa học: đây là image-level split; không được gọi là split theo cây, thửa
ruộng hoặc phiên chụp.

## Bước 1: khóa đầu vào

Chạy trước mỗi chiến dịch train (không dùng test để đánh giá model):

```powershell
python model_benchmark/src/preflight.py
```

Trước **lần train đầu tiên**, chạy kiểm tra chậm nhưng triệt để để hash toàn bộ
65.516 ảnh đã khóa:

```powershell
python model_benchmark/src/preflight.py --verify-images
```

Nếu in `PREFLIGHT PASSED`, artifact được tạo tại
`model_benchmark/runs/preflight/preflight_latest.json`. Nếu thất bại, tuyệt đối
không chạy train cho đến khi tìm và sửa nguyên nhân dữ liệu/protocol bị lệch.

## Bước 2: train từng model, không mở test

Toàn bộ sáu kiến trúc dùng implementation và ImageNet weights chính thức từ
`torchvision`. Runner không có tùy chọn test và chỉ tạo dataset từ hai split
`train`/`validation`.

Máy hiện có RTX 4050 nhưng môi trường TensorFlow cũ dùng NumPy 2.x, không tương
thích với Torch 2.2.1 đang có. Vì vậy benchmark mới bắt buộc dùng virtual
environment riêng `model_benchmark/.venv`; không cài đè môi trường nghiên cứu cũ.

Ví dụ run đầu tiên:

```powershell
python model_benchmark/src/train_backbone.py --model resnet18 --seed 42
```

Giá trị hợp lệ của `--model` và `--seed` nằm trong contract. Thư mục run đã có
artifact sẽ không bị ghi đè. Checkpoint được chọn duy nhất theo Validation
Macro-F1 và lưu dưới dạng `best_model.pt`.

Không bắt đầu cả 18 run cho đến khi một run smoke-test hoàn tất, artifacts được
kiểm tra và script đánh giá cuối đã được khóa.

Trước khi khóa campaign, tải weights và forward-check cả sáu kiến trúc trên GPU:

```powershell
& ".\model_benchmark\.venv\Scripts\python.exe" ".\model_benchmark\src\prefetch_weights.py"
& ".\model_benchmark\.venv\Scripts\python.exe" ".\model_benchmark\src\smoke_models.py"
& ".\model_benchmark\.venv\Scripts\python.exe" ".\model_benchmark\src\smoke_training.py"
```

Sau khi cả sáu đều pass, tạo khóa bất biến. Từ thời điểm này, sửa contract hoặc
một file code đã khóa sẽ khiến runner train từ chối chạy:

```powershell
& ".\model_benchmark\.venv\Scripts\python.exe" ".\model_benchmark\src\lock_campaign.py"
```

Chạy thử đúng một run đầu tiên trước khi giao toàn bộ campaign:

```powershell
& ".\model_benchmark\.venv\Scripts\python.exe" ".\model_benchmark\src\run_campaign.py" --only-model mobilenetv2 --only-seed 42
```

Sau khi kiểm tra artifact run đầu, chạy/resume toàn bộ 18 run:

```powershell
& ".\model_benchmark\.venv\Scripts\python.exe" ".\model_benchmark\src\run_campaign.py"
```
