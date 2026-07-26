import os
import hashlib

def get_file_hash(filepath):
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()
    except Exception as e:
        return None

def check_overlaps(dir1, dir2):
    with open('D:/Phát hiện bệnh cây lúa/duplicates.txt', 'w', encoding='utf-8') as out:
        hashes1 = {}
        out.write(f"Scanning {dir1}...\n")
        for root, _, files in os.walk(dir1):
            for file in files:
                filepath = os.path.join(root, file)
                h = get_file_hash(filepath)
                if h:
                    hashes1[h] = filepath
                    
        overlaps = []
        out.write(f"Scanning {dir2}...\n")
        for root, _, files in os.walk(dir2):
            for file in files:
                filepath = os.path.join(root, file)
                h = get_file_hash(filepath)
                if h and h in hashes1:
                    overlaps.append((hashes1[h], filepath))
                    
        out.write(f"\nFound {len(overlaps)} overlapping images!\n")
        for i, (f1, f2) in enumerate(overlaps[:20]):
            out.write(f"Overlap {i+1}:\n  - {f1}\n  - {f2}\n")
        if len(overlaps) > 20:
            out.write("... (and more)\n")

if __name__ == "__main__":
    dir_hispa = r"D:\Phát hiện bệnh cây lúa\research\data\cleaned_v4\hispa"
    dir_weeds = r"D:\Phát hiện bệnh cây lúa\research\data\cleaned_v4\weeds"
    check_overlaps(dir_hispa, dir_weeds)
