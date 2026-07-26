import os
from huggingface_hub import snapshot_download

def main():
    target_dir = r"D:\Phát hiện bệnh cây lúa\research\data\raw\weed-crop-aerial"
    os.makedirs(target_dir, exist_ok=True)
    
    print("Starting download of weeds dataset from Hugging Face...")
    snapshot_download(
        repo_id="Libre-YOLO/weed-crop-aerial", 
        repo_type="dataset", 
        local_dir=target_dir
    )
    print("Download completed successfully!")

if __name__ == "__main__":
    main()
