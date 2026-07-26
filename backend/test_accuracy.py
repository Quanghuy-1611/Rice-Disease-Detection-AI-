import os
import json
import random
import numpy as np
from PIL import Image
from tensorflow.keras.models import load_model
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

MODEL_PATH = "D:/Phát hiện bệnh cây lúa/backend/app/model/best_stage2.keras"
CLASS_MAP_PATH = "D:/Phát hiện bệnh cây lúa/backend/app/model/class_indices.json"
DATA_DIR = "D:/Phát hiện bệnh cây lúa/research/data/cleaned_v4"

keras_model = load_model(MODEL_PATH)

with open(CLASS_MAP_PATH, "r", encoding="utf-8") as f:
    idx_to_class = json.load(f)
    idx_to_class = {int(k): v for k, v in idx_to_class.items()}

def predict_image(img_path):
    img = Image.open(img_path).convert('RGB')
    img_resized = img.resize((224, 224))
    img_array = np.array(img_resized)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = preprocess_input(img_array.astype(np.float32))

    preds = keras_model.predict(img_array, verbose=0)[0]
    predicted_idx = int(np.argmax(preds))
    return idx_to_class[predicted_idx]

# Test 10 random hispa images
hispa_dir = os.path.join(DATA_DIR, "hispa")
if os.path.exists(hispa_dir):
    images = os.listdir(hispa_dir)
    random.shuffle(images)
    correct = 0
    for i in range(min(20, len(images))):
        img_path = os.path.join(hispa_dir, images[i])
        pred = predict_image(img_path)
        if pred == "hispa":
            correct += 1
        print(f"Hispa {i}: predicted {pred}")
    print(f"Accuracy on 20 random hispa images: {correct}/20")
else:
    print("hispa dir not found")
