import shutil
import os

source_dir = r"D:\Phát hiện bệnh cây lúa\research\data\cleaned_v4"
output_filename = r"D:\Phát hiện bệnh cây lúa\research\data\dataset_v4"

print("Đang nén thư mục cleaned_v4... Vui lòng chờ vài phút vì có tới 28.000 file ảnh.")
shutil.make_archive(output_filename, 'zip', source_dir)
print(f"Nén hoàn tất! File được lưu tại: {output_filename}.zip")
