import os
import glob
import sys
import codecs
from PIL import Image
from tqdm import tqdm
import torch
import torchvision.transforms as transforms
import torchvision.models as models

# Fix print encoding
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

print("Loading MobileNetV3...")
# Use mobilenet_v3_small instead of transformers
model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.IMAGENET1K_V1)
model.eval()

preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# ImageNet classes to filter out:
# People, dogs, cats, cars, maps (comic book), screens, memes (web site), safes, etc.
# Dogs/cats/animals: 151-293
# People/clothing: 400-900 (has lots of random things like safe, comic book, web site, suit, bikini, etc.)
# It's easier to define "keep" classes or just a broad "delete" range.
# Let's delete if the top prediction is inside some specific ranges.
# Cats/Dogs/Animals: 151-398
# People/clothes/screens/comic/website/safe: 
# comic book=917, web site=916, menu=925, safe=770, television=862, monitor=668, envelope=549, jigsaw puzzle=611

BAD_CLASSES = list(range(151, 399)) + [917, 916, 925, 770, 862, 668, 549, 611, 834, 483, 892, 413, 831, 842, 608]

def scan_and_delete(target_dir):
    deleted_count = 0
    total_scanned = 0
    all_images = glob.glob(os.path.join(target_dir, "*", "*.jpg"))
    print(f"Scanning {len(all_images)} in {target_dir}...")
    
    for img_path in tqdm(all_images):
        try:
            total_scanned += 1
            img = Image.open(img_path).convert('RGB')
            input_tensor = preprocess(img)
            input_batch = input_tensor.unsqueeze(0)
            
            with torch.no_grad():
                output = model(input_batch)
                
            probs = torch.nn.functional.softmax(output[0], dim=0)
            top_prob, top_catid = torch.max(probs, 0)
            
            if top_catid.item() in BAD_CLASSES and top_prob.item() > 0.1:
                os.remove(img_path)
                deleted_count += 1
        except Exception:
            pass
            
    return total_scanned, deleted_count

if __name__ == "__main__":
    dirs_to_clean = [
        r"D:\Phát hiện bệnh cây lúa\Bo_Test_Tieng_Viet\Ray_phan_trang",
        r"D:\Phát hiện bệnh cây lúa\research\data\cleaned_v4\sheath_blight",
        r"D:\Phát hiện bệnh cây lúa\research\data\cleaned_v4\whitebacked_planthopper",
        r"D:\Phát hiện bệnh cây lúa\research\data\cleaned_v4\southern_black_streaked_dwarf",
        r"D:\Phát hiện bệnh cây lúa\research\data\cleaned_v4\bacterial_leaf_blight",
        r"D:\Phát hiện bệnh cây lúa\research\data\cleaned_v4\blast"
    ]
    
    total_deleted = 0
    for d in dirs_to_clean:
        if os.path.exists(d):
            scanned, deleted = scan_and_delete(d)
            total_deleted += deleted
            print(f"-> {d}: Deleted {deleted} / {scanned}")
        
    print(f"\n[DONE] Total deleted: {total_deleted}")
