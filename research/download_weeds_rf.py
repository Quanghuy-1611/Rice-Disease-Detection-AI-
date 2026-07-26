import os
from roboflow import Roboflow

def main():
    target_dir = r"D:\Phát hiện bệnh cây lúa\research\data\raw\Roboflow-Weeds"
    os.makedirs(target_dir, exist_ok=True)
    
    print("Starting Roboflow download for Weeds...")
    rf = Roboflow(api_key="hIuSTvyKjr2uI20yD3fI")
    project = rf.workspace("object-detection-dt-wzpc6").project("weed-detection-isa")
    version = project.version(1)
    
    # Download directly to the specified folder
    dataset = version.download("yolov8", location=target_dir)
    print("Download completed successfully.")

if __name__ == "__main__":
    main()
