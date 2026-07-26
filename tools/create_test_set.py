import os
import shutil
import random

DATA_DIR = r"D:\Phát hiện bệnh cây lúa\research\data\cleaned_v4"
TEST_DIR = r"D:\Phát hiện bệnh cây lúa\Bo_Test_Tieng_Viet"

DISEASE_NAMES = {
  "bacterial_leaf_blight": "Chay_la_vi_khuan",
  "bacterial_leaf_streak": "Soc_la_vi_khuan",
  "bacterial_panicle_blight": "Chay_gie_vi_khuan",
  "blast": "Benh_Dao_on",
  "brown_spot": "Benh_Dom_nau",
  "dead_heart": "Benh_duc_than",
  "downy_mildew": "Benh_Suong_mai",
  "hispa": "Bo_gai",
  "normal": "Cay_lua_khoe_manh",
  "tungro": "Benh_Tungro_Vang_lui",
  "leaf_smut": "Benh_Than_Den",
  "weeds": "Co_dai",
  "golden_apple_snail": "Oc_buou_vang",
  "stem_borer": "Sau_duc_than",
  "leaf_roller": "Sau_cuon_la_nho",
  "brown_planthopper": "Ray_nau",
  "whitebacked_planthopper": "Ray_phan_trang",
  "southern_black_streaked_dwarf": "Benh_Lun_soc_den",
  "sheath_blight": "Benh_Kho_van"
}

os.makedirs(TEST_DIR, exist_ok=True)

print("Đang tạo bộ Test Tiếng Việt...")
for eng_name, vie_name in DISEASE_NAMES.items():
    eng_path = os.path.join(DATA_DIR, eng_name)
    vie_path = os.path.join(TEST_DIR, vie_name)
    
    if os.path.exists(eng_path):
        os.makedirs(vie_path, exist_ok=True)
        images = os.listdir(eng_path)
        # Randomly select up to 20 images
        random.shuffle(images)
        selected_images = images[:20]
        
        for img in selected_images:
            src = os.path.join(eng_path, img)
            dst = os.path.join(vie_path, img)
            shutil.copy2(src, dst)
        print(f"Đã copy 20 ảnh vào {vie_name}")
    else:
        print(f"Không tìm thấy thư mục {eng_name}")

print(f"Hoàn thành! Vui lòng vào {TEST_DIR} để lấy ảnh test.")
