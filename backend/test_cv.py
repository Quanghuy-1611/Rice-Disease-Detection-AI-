import asyncio
from app.api.cv_utils import get_lesion_bbox
import numpy as np
import cv2

# Tạo một ảnh dummy xanh lá cây có một đốm nâu
img = np.full((500, 500, 3), (0, 255, 0), dtype=np.uint8)
cv2.circle(img, (250, 250), 50, (0, 100, 150), -1)

success, buffer = cv2.imencode(".jpg", img)
image_bytes = buffer.tobytes()

bbox = get_lesion_bbox(image_bytes)
print("BBox result:", bbox)
