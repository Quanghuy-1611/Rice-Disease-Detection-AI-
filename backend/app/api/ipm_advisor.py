"""Conservative field-check guidance for the seven supported RiceAI labels.

An image cannot measure pest density, affected area, water state or treatment
threshold. Do not turn a user-selected severity into an automatic spray order.
"""

FIELD_GUIDANCE = {
    "bacterial_leaf_blight": (
        "Kiểm tra thêm nhiều cây trong ruộng và đối chiếu vết bạc lá; ảnh đơn lẻ có thể nhầm với tổn thương khác. "
        "Theo dõi mức lan rộng, bón phân cân đối và hỏi cán bộ bảo vệ thực vật nếu bệnh tăng nhanh.",
        ["Đánh dấu khu vực có triệu chứng để kiểm tra lại.",
         "Tránh bón thừa đạm; đối chiếu lịch bón phân và điều kiện ruộng."],
    ),
    "brown_spot": (
        "Kiểm tra vết đốm trên nhiều lá và tình trạng dinh dưỡng của ruộng. "
        "Đốm nâu có thể giống một số bệnh khác; nên xác nhận ngoài ruộng trước khi xử lý.",
        ["Theo dõi vết bệnh ở các cây lân cận.",
         "Kiểm tra dinh dưỡng đất và bón phân cân đối theo khuyến cáo địa phương."],
    ),
    "golden_apple_snail": (
        "Kiểm tra ốc, ổ trứng và cây mạ bị cắn ở nhiều vị trí. Nếu có ốc, ưu tiên thu gom ốc và ổ trứng; "
        "cách quản lý nước cần phù hợp giai đoạn lúa và điều kiện ruộng.",
        ["Thu gom ốc và ổ trứng khi có thể.",
         "Kiểm tra đường nước vào ruộng và các vị trí ốc tập trung."],
    ),
    "leaf_roller": (
        "Mở vài lá bị cuốn để kiểm tra sâu non và quan sát tỷ lệ lá bị hại trong ruộng. "
        "Không quyết định phun thuốc chỉ dựa vào một ảnh lá cuốn.",
        ["Theo dõi sâu non và thiên địch tại nhiều điểm trong ruộng.",
         "Giữ cân đối phân bón và ghi lại mức độ hại để đối chiếu lần sau."],
    ),
    "tungro": (
        "Kiểm tra thêm cây thấp lùn, lá vàng và sự hiện diện của rầy xanh; triệu chứng có thể giống thiếu dinh dưỡng. "
        "Nếu nghi Tungro, liên hệ cán bộ bảo vệ thực vật để xác nhận và hướng dẫn quản lý nguồn lây.",
        ["Quan sát nhiều cây và chụp thêm ảnh toàn cây, lá và ruộng.",
         "Ghi lại nơi xuất hiện triệu chứng và theo dõi rầy xanh."],
    ),
    "weeds": (
        "Quan sát mật độ và loại cỏ trong ruộng. Nếu cỏ còn ít, ưu tiên nhổ tay hoặc làm cỏ cơ giới; "
        "biện pháp khác phải phù hợp giai đoạn lúa và loại cỏ.",
        ["Nhổ tay hoặc làm cỏ cơ giới tại khu vực có cỏ khi phù hợp.",
         "Theo dõi nơi cỏ tái xuất hiện để xử lý sớm."],
    ),
}


def get_ipm_advice(predicted_class: str, severity: str) -> dict:
    """Return observations and low-risk next steps without inventing severity."""
    if predicted_class == "normal":
        recommendation = ("Ảnh chưa cho thấy dấu hiệu bất thường rõ trong các nhóm RiceAI nhận diện. "
                          "Tiếp tục quan sát cây trực tiếp; nếu vẫn có biểu hiện lạ, hãy chụp thêm hoặc hỏi chuyên gia.")
        methods = ["Theo dõi ruộng định kỳ và chăm sóc theo điều kiện thực tế."]
    elif predicted_class in FIELD_GUIDANCE:
        recommendation, methods = FIELD_GUIDANCE[predicted_class]
    else:
        recommendation = "RiceAI chưa có hướng dẫn cho nhóm này. Hãy hỏi cán bộ bảo vệ thực vật tại địa phương."
        methods = []
    if severity == "high" and predicted_class != "normal":
        recommendation += " Bạn báo triệu chứng nặng; nên kiểm tra trực tiếp sớm."
    return {
        "organic_methods": methods,
        "chemical_methods": [],
        "recommendation": recommendation,
        "threshold_reached": False,
    }
