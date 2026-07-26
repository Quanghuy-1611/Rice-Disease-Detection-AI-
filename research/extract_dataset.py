import os
import io
import pyarrow.parquet as pq
from PIL import Image

parquet_dir = r"C:\Users\Quang Huy\Downloads\New folder"
out_dir = r"D:\Phát hiện bệnh cây lúa\research\data\raw"
os.makedirs(out_dir, exist_ok=True)

class_names = [
    "bacterial_leaf_blight", "bacterial_leaf_streak", 
    "bacterial_panicle_blight", "blast", "brown_spot", 
    "dead_heart", "downy_mildew", "hispa", "normal", "tungro"
]

for label_name in class_names:
    os.makedirs(os.path.join(out_dir, label_name), exist_ok=True)

for file in os.listdir(parquet_dir):
    if file.endswith(".parquet"):
        print(f"Processing {file}...")
        path = os.path.join(parquet_dir, file)
        table = pq.read_table(path)
        
        images = table['image'].to_pylist()
        labels = table['label'].to_pylist()
        
        for i, (img_struct, label_idx) in enumerate(zip(images, labels)):
            try:
                img_bytes = img_struct['bytes']
                label_name = class_names[label_idx]
                
                img_path_name = img_struct.get('path')
                if img_path_name:
                    filename = os.path.basename(img_path_name)
                else:
                    filename = f"{file.split('.')[0]}_{i}.jpg"
                    
                save_path = os.path.join(out_dir, label_name, filename)
                
                image = Image.open(io.BytesIO(img_bytes))
                image.save(save_path)
            except Exception as e:
                print(f"Error processing image {i} in {file}: {e}")
        print(f"Finished processing {file}")

print("Extraction completed successfully!")
