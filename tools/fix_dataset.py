import os
import json

# 1. Update class_indices.json
CLASS_MAP_PATH = r"D:\Phát hiện bệnh cây lúa\backend\app\model\class_indices.json"
with open(CLASS_MAP_PATH, "r", encoding="utf-8") as f:
    idx_to_class = json.load(f)

# Find keys for hispa and weeds
hispa_key = next((k for k, v in idx_to_class.items() if v == "hispa"), None)
weeds_key = next((k for k, v in idx_to_class.items() if v == "weeds"), None)

if hispa_key and weeds_key:
    idx_to_class[hispa_key] = "weeds"
    idx_to_class[weeds_key] = "hispa"
    
    with open(CLASS_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(idx_to_class, f, indent=2)
    print("Fixed class_indices.json")

# 2. Swap folders in cleaned_v4
def swap_folders(dir_path, folder1, folder2):
    path1 = os.path.join(dir_path, folder1)
    path2 = os.path.join(dir_path, folder2)
    temp_path = os.path.join(dir_path, "temp_swap_folder")
    
    if os.path.exists(path1) and os.path.exists(path2):
        os.rename(path1, temp_path)
        os.rename(path2, path1)
        os.rename(temp_path, path2)
        print(f"Swapped {folder1} and {folder2} in {dir_path}")

DATA_DIR = r"D:\Phát hiện bệnh cây lúa\research\data\cleaned_v4"
swap_folders(DATA_DIR, "hispa", "weeds")

# 3. Swap folders in Bo_Test_Tieng_Viet
TEST_DIR = r"D:\Phát hiện bệnh cây lúa\Bo_Test_Tieng_Viet"
swap_folders(TEST_DIR, "Bo_gai", "Co_dai")

print("Done fixing dataset and labels!")
