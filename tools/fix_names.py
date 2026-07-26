import os

def rename_files(folder_path, correct_prefix):
    if not os.path.exists(folder_path):
        return
    files = os.listdir(folder_path)
    count = 1
    for f in files:
        if f.lower().endswith(('.jpg', '.jpeg', '.png')):
            old_path = os.path.join(folder_path, f)
            new_name = f"{correct_prefix}_{count:04d}.jpg"
            new_path = os.path.join(folder_path, new_name)
            os.rename(old_path, new_path)
            count += 1

base_dir = r"D:\Phát hiện bệnh cây lúa\research\data\cleaned_v4"
rename_files(os.path.join(base_dir, "weeds"), "weeds")
rename_files(os.path.join(base_dir, "hispa"), "hispa")
print("Done renaming files!")
