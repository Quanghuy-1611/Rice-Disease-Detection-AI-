import os
from roboflow import Roboflow

def main():
    target_dir = r"D:\Phát hiện bệnh cây lúa\research\data\raw\golden-apple-snail"
    os.makedirs(target_dir, exist_ok=True)
    
    print("Starting Roboflow download...")
    rf = Roboflow(api_key="hIuSTvyKjr2uI20yD3fI")
    project = rf.workspace("thesis-hnauj").project("golden-apple-snail-akceb")
    version = project.version(1)
    
    # Download directly to the specified folder
    dataset = version.download("yolov8", location=target_dir)
    print("Download completed to", target_dir)

if __name__ == "__main__":
    main()
