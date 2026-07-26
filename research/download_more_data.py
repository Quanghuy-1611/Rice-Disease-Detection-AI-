import os
from download_images_bing import download_bing_images

if __name__ == "__main__":
    print("Bắt đầu cào ảnh bổ sung từ Bing...")
    
    # 1. Khô Vằn (Sheath Blight)
    out_sheath = r"D:\Phát hiện bệnh cây lúa\research\data\raw\Custom_Bing_Dataset\sheath_blight"
    print("Cào ảnh Khô Vằn (Sheath Blight)...")
    download_bing_images("Rice Sheath Blight disease infected leaf", 1500, out_sheath)
    download_bing_images("Rhizoctonia solani rice", 500, out_sheath)
    
    # 2. Đạo Ôn (Blast)
    out_blast = r"D:\Phát hiện bệnh cây lúa\research\data\raw\Custom_Bing_Dataset\blast"
    print("Cào ảnh Đạo Ôn (Blast)...")
    download_bing_images("Rice Blast disease Pyricularia oryzae leaf", 1000, out_blast)
    download_bing_images("Magnaporthe oryzae rice infection", 1000, out_blast)
    
    # 3. Bạc Lá (Bacterial Leaf Blight)
    out_blight = r"D:\Phát hiện bệnh cây lúa\research\data\raw\Custom_Bing_Dataset\bacterial_leaf_blight"
    print("Cào ảnh Bạc Lá (Bacterial Leaf Blight)...")
    download_bing_images("Rice Bacterial Leaf Blight Xanthomonas oryzae", 1000, out_blight)
    download_bing_images("Bacterial blight rice severe infection", 1000, out_blight)
    
    print("Hoàn tất cào ảnh!")
