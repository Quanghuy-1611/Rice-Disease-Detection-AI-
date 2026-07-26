# ipm_advisor.py
# Module tư vấn quản lý dịch hại theo chuẩn IPM/IPHM và canh tác hữu cơ

def get_ipm_advice(predicted_class: str, severity: str) -> dict:
    """
    Trả về lời khuyên xử lý dựa trên nguyên tắc IPM/IPHM.
    severity: 'low' (Thấp), 'medium' (Trung bình), 'high' (Cao)
    """
    advice = {
        "organic_methods": [],
        "chemical_methods": [],
        "recommendation": "",
        "threshold_reached": False
    }

    if predicted_class == "normal":
        advice["recommendation"] = "Tuyệt vời! Lúa đang phát triển khỏe mạnh. Tiếp tục duy trì mực nước luân phiên (AWD) để rễ khỏe và giảm phát thải khí nhà kính."
        return advice

    # Ngưỡng chung: Nếu severity là 'high', ngưỡng hành động bằng thuốc đã bị vượt qua.
    threshold_reached = (severity == "high")
    advice["threshold_reached"] = threshold_reached

    # Lời khuyên Hữu cơ/Sinh học chung (IPHM)
    general_organic = [
        "Vệ sinh đồng ruộng, dọn sạch cỏ dại ven bờ.",
        "Bón phân cân đối N-P-K, không lạm dụng đạm (Nitơ) để tránh lốp đổ và sâu bệnh.",
        "Sử dụng thiên địch tự nhiên (nhện bắt mồi, kiến ba khoang)."
    ]

    # Xử lý theo từng nhóm dịch hại
    if predicted_class in ["hispa", "stem_borer", "leaf_roller", "brown_planthopper", "whitebacked_planthopper"]:
        advice["organic_methods"] = general_organic + [
            "Áp dụng nấm xanh (Metarhizium) hoặc nấm trắng (Beauveria) để phun trừ sâu sinh học.",
            "Dùng bẫy đèn lồng để thu hút bướm và rầy trưởng thành vào ban đêm.",
            "Đối với Sâu cuốn lá/Sâu đục thân: Thả ong ký sinh (Trichogramma) ngay từ khi thấy bướm bay." if predicted_class in ["stem_borer", "leaf_roller"] else "Bảo vệ các loài nhện bắt mồi và bọ rùa."
        ]
        advice["chemical_methods"] = [
            "Chỉ sử dụng thuốc nội hấp (VD: Pymetrozine, Dinotefuran) khi mật độ rầy/sâu vượt ngưỡng.",
            "Tuân thủ nguyên tắc 4 đúng, phun vào sáng sớm hoặc chiều mát."
        ]
        if not threshold_reached:
            advice["recommendation"] = "Mật độ sâu hại hiện tại vẫn dưới ngưỡng kinh tế. Khuyến cáo KHÔNG phun thuốc hóa học để bảo vệ thiên địch. Hãy sử dụng biện pháp sinh học (Nấm xanh) và theo dõi thêm."
        else:
            advice["recommendation"] = "CẢNH BÁO: Mật độ sâu/rầy đã vượt ngưỡng an toàn. Cần áp dụng ngay thuốc đặc trị (ưu tiên nhóm sinh học gốc Kurstaki hoặc hóa học phổ hẹp) để dập dịch."

    elif predicted_class == "southern_black_streaked_dwarf":
        advice["organic_methods"] = [
            "Nhổ bỏ và tiêu hủy ngay những cây bị bệnh để tránh lây lan (bệnh do virus gây ra, không có thuốc chữa).",
            "Vệ sinh đồng ruộng, diệt sạch cỏ dại ven bờ vì đó có thể là nơi cư trú của rầy.",
            "Khuyến khích luân canh cây trồng khác họ ở vụ sau để cắt đứt mầm bệnh."
        ]
        advice["chemical_methods"] = [
            "Phun thuốc hóa học đặc trị để tiêu diệt ngay RẦY LƯNG TRẮNG (môi giới truyền bệnh) trên ruộng và khu vực lân cận."
        ]
        if not threshold_reached:
            advice["recommendation"] = "Bệnh Lùn sọc đen là bệnh Virus cực kỳ nguy hiểm, lây qua rầy lưng trắng. Khi phát hiện bệnh ở mức độ nhẹ, BẮT BUỘC phải nhổ bỏ và tiêu hủy ngay cây bệnh, đồng thời kiểm tra mật độ rầy lưng trắng để xử lý."
        else:
            advice["recommendation"] = "CẢNH BÁO ĐỎ: Ruộng lúa đã bị nhiễm Lùn sọc đen rất nặng. Nguy cơ mất trắng là rất cao. Cần khẩn trương phun thuốc diệt rầy lưng trắng để bảo vệ các ruộng xung quanh, báo cáo ngay cho cán bộ nông nghiệp địa phương để có hướng xử lý triệt để."

    elif predicted_class == "weeds":
        advice["organic_methods"] = [
            "Nhổ cỏ bằng tay hoặc sử dụng máy làm cỏ cơ giới.",
            "Giữ mực nước ruộng khoảng 3-5cm để ém cỏ không cho mọc lên.",
            "Sử dụng vịt thả đồng (nếu lúa đã cứng cây) để diệt cỏ dại."
        ]
        advice["chemical_methods"] = [
            "Sử dụng thuốc trừ cỏ tiền nảy mầm hoặc hậu nảy mầm (ưu tiên loại phân hủy nhanh).",
            "Phun điểm (spot treatment) ở những vệt cỏ dày thay vì phun toàn bộ ruộng."
        ]
        if not threshold_reached:
            advice["recommendation"] = "Cỏ dại mọc rải rác. Hãy dùng biện pháp cơ giới (làm cỏ bằng tay/máy) và giữ nước để ém cỏ. Hạn chế thuốc diệt cỏ để bảo vệ đất hữu cơ."
        else:
            advice["recommendation"] = "Cỏ dại phát triển quá mạnh, lấn át cây lúa. Có thể cân nhắc phun thuốc trừ cỏ hậu nảy mầm có chọn lọc, kết hợp làm cỏ tay những khu vực gần nguồn nước."

    elif predicted_class == "golden_apple_snail":
        advice["organic_methods"] = [
            "Bắt ốc thủ công vào sáng sớm hoặc chiều mát.",
            "Cắm cọc tre/tràm rải rác trên ruộng để ốc leo lên đẻ trứng, sau đó thu gom ổ trứng đem tiêu hủy.",
            "Thả vịt vào ruộng cày bừa để vịt ăn ốc non."
        ]
        advice["chemical_methods"] = [
            "Sử dụng bả mồi sinh học hoặc thuốc trị ốc (hoạt chất Niclosamide) ở các vũng nước đọng."
        ]
        if not threshold_reached:
            advice["recommendation"] = "Số lượng ốc bươu vàng chưa đáng lo ngại. Hãy ưu tiên bắt tay và cắm cọc thu gom trứng để bảo vệ môi trường sinh thái."
        else:
            advice["recommendation"] = "Ốc bươu vàng đang cắn phá mạnh. Cần rút cạn nước (chỉ để lại các rãnh nhỏ) và rải bả diệt ốc tập trung tại rãnh nước để đạt hiệu quả cao nhất mà không tồn dư thuốc trên diện rộng."

    elif predicted_class == "sheath_blight":
        advice["organic_methods"] = general_organic + [
            "Làm sạch cỏ dại ở bờ ruộng, vớt bỏ các hạch nấm (sclerotia) trôi nổi trên mặt nước.",
            "Phun chế phẩm sinh học chứa nấm Trichoderma hoặc vi khuẩn Bacillus subtilis để ức chế nấm Rhizoctonia solani."
        ]
        advice["chemical_methods"] = [
            "Phun thuốc đặc trị nấm (nhóm Validamycin, Hexaconazole, Pencycuron, Difenoconazole) khi tỷ lệ dảnh bị bệnh >20%."
        ]
        if not threshold_reached:
            advice["recommendation"] = "Bệnh Khô Vằn mới chớm xuất hiện ở bẹ lá dưới gốc. Cần lập tức ngừng bón đạm, rút cạn nước phơi ruộng để giảm độ ẩm chân lúa, phun chế phẩm sinh học Trichoderma."
        else:
            advice["recommendation"] = "CẢNH BÁO: Bệnh Khô Vằn đã lan lên các lá phía trên hoặc có nguy cơ ăn vào bông. Cần phun ngay thuốc hóa học đặc trị (Validamycin, Hexaconazole) theo đúng liều lượng khuyến cáo. Phun vào phần gốc và thân lúa."

    else:
        # Nhóm Bệnh do nấm / vi khuẩn (blast, brown_spot, bacterial_leaf_blight...)
        advice["organic_methods"] = general_organic + [
            "Cắt tỉa lá bệnh đem tiêu hủy xa đồng ruộng.",
            "Phun chế phẩm sinh học Trichoderma hoặc Pseudomonas để đối kháng nấm bệnh."
        ]
        advice["chemical_methods"] = [
            "Phun thuốc đặc trị (nhóm Hexaconazole, Tricyclazole cho nấm; Kasugamycin cho vi khuẩn).",
            "Phun phòng trước khi trổ bông nếu thời tiết sương mù, độ ẩm cao."
        ]
        if not threshold_reached:
            advice["recommendation"] = "Bệnh mới chớm xuất hiện. Khuyến cáo ngừng bón phân đạm ngay lập tức, tháo nước phơi ruộng (nếu có thể) và phun chế phẩm sinh học đối kháng."
        else:
            advice["recommendation"] = "Vết bệnh đã lan rộng. Nguy cơ thất thu cao. Cần tiến hành phun thuốc hóa học đặc trị theo liều lượng hướng dẫn. Phun 2 lần cách nhau 7 ngày."

    return advice
