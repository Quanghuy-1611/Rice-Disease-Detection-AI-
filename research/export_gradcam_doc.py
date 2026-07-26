import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

def add_heading(doc, text, level=1):
    heading = doc.add_heading(text, level=level)
    for run in heading.runs:
        run.font.name = 'Arial'
        run.font.color.rgb = None # default color

def add_paragraph(doc, text, bold=False, italic=False, style=None):
    if style:
        p = doc.add_paragraph(style=style)
    else:
        p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = Pt(11)
    if bold:
        run.bold = True
    if italic:
        run.italic = True
    return p

doc = Document()

# Tiêu đề chính
title = doc.add_heading('BÁO CÁO PHÂN TÍCH VÀ ĐÁNH GIÁ THUẬT TOÁN GRAD-CAM\n(Baseline 540 Ảnh Thực Tế)', 0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER

add_heading(doc, 'PHẦN I: TÌM HIỂU VÀ PHÂN TÍCH THUẬT TOÁN GRAD-CAM', level=1)

add_heading(doc, '1. Grad-CAM là gì?', level=2)
add_paragraph(doc, 
    "Grad-CAM (Gradient-weighted Class Activation Mapping) là một kỹ thuật nội soi mạng nơ-ron tích chập (CNN). "
    "Mục đích của nó là giải thích 'Tại sao AI lại đưa ra quyết định dự đoán như vậy?' bằng cách tạo ra một bản đồ nhiệt (Heatmap) "
    "chỉ ra các vùng trọng điểm trên ảnh mà AI đã tập trung vào để nhận diện bệnh."
)

add_heading(doc, '2. Cơ chế hoạt động & Toán học của Grad-CAM', level=2)
add_paragraph(doc, 
    "Về mặt toán học, Grad-CAM dựa vào đạo hàm (Gradient) của điểm số dự đoán lớp c (y_c) đối với các bản đồ đặc trưng (Feature Maps) "
    "A^k của lớp tích chập cuối cùng."
)
add_paragraph(doc, "Các bước thực hiện:")
add_paragraph(doc, "Bước 1: Tính toán trọng số alpha_k^c (tầm quan trọng của kênh đặc trưng thứ k đối với lớp c) bằng công thức Global Average Pooling (GAP) trên đạo hàm:", style='List Bullet')
add_paragraph(doc, "alpha_k^c = (1/Z) * Σ Σ (∂y_c / ∂A_ij^k)", style='List Bullet')
add_paragraph(doc, "Bước 2: Tính tổng có trọng số của các bản đồ đặc trưng, sau đó đi qua hàm ReLU để loại bỏ các ảnh hưởng tiêu cực (những vùng không thuộc lớp c):", style='List Bullet')
add_paragraph(doc, "L_Grad-CAM^c = ReLU( Σ alpha_k^c * A^k )", style='List Bullet')

add_heading(doc, '3. Ưu điểm và Nhược điểm của Grad-CAM (Phiên bản hiện tại)', level=2)
add_paragraph(doc, "Ưu điểm:", style='List Bullet')
add_paragraph(doc, "- Tính toán trực tiếp, tốc độ nhanh.\n- Hoạt động được với mọi kiến trúc CNN (MobileNetV2, ResNet, VGG...).", style='List Continue')

add_paragraph(doc, "Nhược điểm (Lý do cần Nâng cấp):", style='List Bullet')
add_paragraph(doc, 
    "- Hiện tượng lan truyền và nhiễu (Heatmap Loang): Do Grad-CAM chỉ tính trọng số trung bình toàn cục (GAP), "
    "nó thường không sắc nét nếu đối tượng (vết bệnh) nhỏ bé.\n"
    "- Bỏ sót đa mục tiêu: Nếu trên lá có nhiều vết bệnh đốm nhỏ phân tán, Grad-CAM thường chỉ tô đỏ một vùng to nhất và bỏ lỡ các vết nhỏ.\n"
    "- Vùng ranh giới mờ nhạt: Grad-CAM có độ phân giải thấp, khi upscale lên kích thước ảnh gốc dễ bị bao trùm cả những vùng lá khỏe mạnh.", 
    style='List Continue'
)

doc.add_page_break()

add_heading(doc, 'PHẦN II: BÁO CÁO KẾT QUẢ ĐÁNH GIÁ (BASELINE THỰC TẾ)', level=1)

add_paragraph(doc, "Phương pháp kiểm thử:")
add_paragraph(doc, "- Tập dữ liệu: 18 lớp bệnh (bỏ qua lùn sọc đen), bốc ngẫu nhiên 30 ảnh/lớp = 540 ảnh.", style='List Bullet')
add_paragraph(doc, "- Model: best_stage2.keras (MobileNetV2 Fine-tuned)", style='List Bullet')
add_paragraph(doc, "- Tiêu chí: Accuracy (Đúng/Sai), Confidence (Độ tự tin), Activation Area (Độ nhiễu/tập trung của Heatmap)", style='List Bullet')

add_heading(doc, '1. Kết quả Định Lượng', level=2)

table = doc.add_table(rows=1, cols=4)
table.style = 'Table Grid'
hdr_cells = table.rows[0].cells
hdr_cells[0].text = 'Lớp bệnh'
hdr_cells[1].text = 'Acc %'
hdr_cells[2].text = 'Conf TB %'
hdr_cells[3].text = 'ActivArea %'

data = [
    ("bacterial_leaf_blight", "86.7", "86.1", "25.9"),
    ("bacterial_leaf_streak", "76.7", "71.0", "24.2"),
    ("bacterial_panicle_blight", "76.7", "78.1", "16.8"),
    ("blast (Đạo ôn)", "83.3", "70.2", "19.7"),
    ("brown_planthopper", "93.3", "94.3", "21.7"),
    ("brown_spot (Đốm nâu)", "90.0", "90.7", "19.0"),
    ("dead_heart", "86.7", "89.9", "23.1"),
    ("downy_mildew", "70.0", "61.9", "21.6"),
    ("golden_apple_snail", "93.3", "96.2", "16.4"),
    ("hispa", "96.7", "97.3", "23.6"),
    ("leaf_roller (Sâu cuốn lá)", "100.0", "99.8", "21.3"),
    ("leaf_smut", "16.7", "54.9", "14.1"),
    ("normal (Bình thường)", "96.7", "85.6", "34.6"),
    ("sheath_blight", "100.0", "99.4", "23.5"),
    ("stem_borer", "96.7", "96.8", "21.8"),
    ("tungro", "83.3", "72.7", "25.2"),
    ("weeds (Cỏ dại)", "83.3", "68.2", "21.0"),
    ("whitebacked_planthopper", "96.7", "97.3", "26.3"),
]

for item in data:
    row_cells = table.add_row().cells
    row_cells[0].text = item[0]
    row_cells[1].text = item[1]
    row_cells[2].text = item[2]
    row_cells[3].text = item[3]

doc.add_paragraph("\n")
p = doc.add_paragraph()
p.add_run("TỔNG HỢP: ").bold = True
p.add_run("Accuracy Trung Bình: 84.8% | Confidence Trung Bình: 83.9% | Activation Area Trung Bình: 22.2%")

add_heading(doc, '2. Phân tích kết quả và Lộ trình Nâng cấp', level=2)
add_paragraph(doc, "Nhóm Hoàn Hảo (Acc > 95%): Sâu cuốn lá, Hispa, Rầy... AI nhận diện hoàn hảo và cực kỳ tự tin.")
add_paragraph(doc, "Nhóm Cần Nâng Cấp Gấp (Sẽ được giải quyết bằng Grad-CAM++):")
add_paragraph(doc, "- Bệnh leaf_smut: Accuracy chỉ 16.7%.", style='List Bullet')
add_paragraph(doc, "- Bệnh downy_mildew: Đoán đúng 70% nhưng độ tự tin quá thấp (61.9%).", style='List Bullet')
add_paragraph(doc, "- Nhòe/Nhiễu Heatmap: Các lớp như normal có ActivArea lên tới 34.6%, bôi đỏ loang lổ.", style='List Bullet')

add_paragraph(doc, "\nĐịnh Hướng Nâng Cấp:", bold=True)
add_paragraph(doc, 
    "Nâng cấp thuật toán hiện tại lên Grad-CAM++ (sử dụng thêm đạo hàm bậc 2 và bậc 3 để tính trọng số pixel-wise). "
    "Điều này sẽ giúp AI Focus chính xác hơn vào các vết bệnh cực nhỏ, giảm tỷ lệ lan vùng màu đỏ (giảm ActivArea), "
    "từ đó giúp model tránh nhầm lẫn giữa các bệnh có đặc điểm na ná nhau (như Blast và Brown Spot)."
)

output_path = r"D:\Phát hiện bệnh cây lúa\research\Bao_Cao_Phan_Tich_Va_Danh_Gia_Grad_CAM.docx"
doc.save(output_path)
print(f"Đã xuất file Word thành công tại: {output_path}")
