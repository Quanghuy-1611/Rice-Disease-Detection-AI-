import os
import urllib.request
import pandas as pd
import gzip
from urllib.parse import urlparse, urlunparse

def s3_to_https(s3_url):
    parsed = urlparse(s3_url)
    netloc = f"{parsed.netloc}.s3.ap-south-1.amazonaws.com"
    return urlunparse(parsed._replace(scheme='https', netloc=netloc))

def main():
    print("Downloading metadata from AWS S3...")
    metadata_url = "https://wadhwaniai-agri-opendata.s3.ap-south-1.amazonaws.com/metadata/20230327-1214/dev.csv.gz"
    
    out_dir = r"D:\Phát hiện bệnh cây lúa\research\data\raw\pests"
    os.makedirs(out_dir, exist_ok=True)
    
    csv_path = "dev.csv.gz"
    urllib.request.urlretrieve(metadata_url, csv_path)
    
    print("Metadata downloaded, starting to download images...")
    df = pd.read_csv(csv_path, compression='gzip')
    
    # Tải toàn bộ dữ liệu
    for i, row in df.iterrows():
        url = row['url']
        https_url = s3_to_https(url)
        
        # Tạo thư mục theo nhãn bệnh/sâu
        label = str(row['label'])
        label_dir = os.path.join(out_dir, label)
        os.makedirs(label_dir, exist_ok=True)
        
        filename = os.path.basename(urlparse(url).path)
        save_path = os.path.join(label_dir, filename)
        
        if not os.path.exists(save_path):
            try:
                urllib.request.urlretrieve(https_url, save_path)
                if i % 10 == 0:
                    print(f"Downloaded {i} images...")
            except Exception as e:
                print(f"Error downloading image {i}: {e}")

    print(f"Download completed! Data saved at {out_dir}")

if __name__ == "__main__":
    main()
