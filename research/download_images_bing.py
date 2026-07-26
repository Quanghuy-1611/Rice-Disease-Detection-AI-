import requests
import re
import os
import urllib.parse
import sys
import codecs

# Fix print encoding for Windows
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def download_bing_images(query, num_images, save_dir):
    os.makedirs(save_dir, exist_ok=True)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    count = 0
    page = 1
    
    # Track downloaded URLs to avoid duplicates
    downloaded_urls = set()

    while count < num_images and page < 500:
        search_url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}&form=HDRSC2&first={page}"
        
        try:
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()
        except Exception:
            break

        # Extract image URLs
        img_urls = re.findall(r'murl&quot;:&quot;(.*?)&quot;', response.text)
        if not img_urls:
            img_urls = re.findall(r'"murl":"(.*?)"', response.text)
            
        img_urls = list(set(img_urls))
        
        if not img_urls:
            break

        for img_url in img_urls:
            if img_url in downloaded_urls:
                continue
            downloaded_urls.add(img_url)
            
            if count >= num_images:
                break
                
            try:
                img_data = requests.get(img_url, headers=headers, timeout=5).content
                ext = img_url.split(".")[-1].split("?")[0]
                if len(ext) > 4: ext = "jpg"
                filename = os.path.join(save_dir, f"img_{count}.{ext}")
                with open(filename, "wb") as handler:
                    handler.write(img_data)
                count += 1
            except Exception:
                continue
                
        page += len(img_urls)
        
if __name__ == "__main__":
    download_bing_images("Southern rice black-streaked dwarf virus infected plant", 100, r"D:\Phát hiện bệnh cây lúa\research\data\raw\Custom_Bing_Dataset\SRBSDV")
    download_bing_images("Sogatella furcifera Whitebacked planthopper", 100, r"D:\Phát hiện bệnh cây lúa\research\data\raw\Custom_Bing_Dataset\Whitebacked_planthopper")
