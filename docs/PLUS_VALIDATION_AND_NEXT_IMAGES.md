# RiceAI Plus: kiểm định hiện tại và ảnh cần bổ sung

## Phạm vi đang chạy

Basic phân loại một ảnh bằng MobileNetV3-Large. Plus phân loại tối đa năm ảnh bằng MobileNetV3-Large và Swin-Tiny; hai mô hình phải cùng nhãn và từng mô hình phải đạt ngưỡng 0,95. Grad-CAM của MobileNetV3-Large được giới hạn bằng vùng DeepLabV3+ dự đoán **chỉ với ba nhóm bệnh lá**. Vùng này là dấu hiệu mô hình học được, chưa phải chú giải tổn thương do chuyên gia xác nhận trên từng ảnh. Plus không kết luận chung khi số ảnh được chấp nhận chưa đủ hoặc nhãn xung đột.

## Kiểm định đang có

Bộ đánh giá ngoài gồm 100 ảnh cho mỗi nhóm trong bảy nhóm đã huấn luyện và bốn nhóm chưa huấn luyện (1.100 ảnh). Với quy tắc Plus hiện tại, 404/700 ảnh thuộc bảy nhóm được chấp nhận; 401/404 ảnh được chấp nhận phân loại đúng; 382/400 ảnh ngoài phạm vi bị từ chối. Riêng Tungro chỉ 16/100 ảnh được chấp nhận, trong đó 14 ảnh đúng; bạc lá vi khuẩn được chấp nhận 35/100. Dice của DeepLabV3+ trên tập validation RiceSeg-5932 là 0,776. Các con số này là số đo trên dữ liệu kiểm thử và không bảo đảm hiệu quả trên ruộng thực tế. Ngưỡng Plus đã được siết sau một lượt xem bộ đánh giá ngoài, nên cần một tập kiểm thử độc lập mới trước khi tuyên bố độ chính xác cuối cùng.

## Ưu tiên tìm và gán nhãn ảnh

1. **Tungro**: thêm ảnh từ nhiều giống lúa, giai đoạn và thiết bị chụp; gồm cả lá dễ nhầm với thiếu dinh dưỡng, cháy lá và cây khỏe. Đây là điểm yếu lớn nhất về tỷ lệ kết luận.
2. **Bạc lá vi khuẩn**: thêm ảnh ở các mức độ bệnh, ánh sáng và góc chụp khác nhau; xác nhận nhãn với người có chuyên môn.
3. **Cây khỏe và ảnh ngoài phạm vi**: thêm ảnh cây khỏe thật và các bệnh/sâu hại chưa nằm trong bảy nhóm để đo khả năng từ chối. Basic đang nhận sai nhiều ảnh ngoài phạm vi hơn Plus.
4. **Ảnh có vùng bệnh được khoanh bằng mask**: cần để huấn luyện và kiểm tra riêng DeepLabV3+. Ảnh chỉ có nhãn tên bệnh giúp huấn luyện bộ phân loại nhưng không chứng minh bản đồ nhiệt tô đúng chỗ bệnh.

Giữ nguồn, quyền sử dụng, tên bệnh, người xác nhận nhãn và thời điểm/địa điểm chụp của mỗi ảnh. Loại ảnh trùng hoặc gần trùng **trước khi chia tập**; ảnh từ cùng một cây/đợt chụp phải nằm cùng một tập. Giữ nguyên bộ kiểm thử khóa hiện tại, và tạo một bộ ảnh thực địa mới chưa dùng để chọn ngưỡng hay huấn luyện. Sau khi thêm ảnh, train lại các mô hình chịu ảnh hưởng, kiểm tra nhầm lẫn và độ bao phủ từng lớp, kiểm tra mask với chuyên gia, tạo manifest phát hành mới rồi khởi động lại backend. Backend tự tắt Plus khi trọng số thay đổi mà chưa được kiểm định lại.
