import os
import json
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model

MODEL_PATH = "D:/Phát hiện bệnh cây lúa/backend/app/model/best_stage2.keras"

print("Loading model...")
model = load_model(MODEL_PATH)
print("Model loaded.")

# find last conv layer
last_conv_layer_name = None
for layer in reversed(model.layers):
    if len(layer.output_shape) == 4:
        last_conv_layer_name = layer.name
        break

print("Last conv layer:", last_conv_layer_name)

# test generate_gradcam
from PIL import Image
import io
import cv2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

# dummy image bytes
img = Image.new('RGB', (224, 224), color = 'green')
buf = io.BytesIO()
img.save(buf, format='JPEG')
image_bytes = buf.getvalue()

nparr = np.frombuffer(image_bytes, np.uint8)
img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
resized_img = cv2.resize(img_rgb, (224, 224))
img_array = np.expand_dims(resized_img, axis=0)
img_array = preprocess_input(img_array.astype(np.float32))

print("Creating grad model...")
grad_model = tf.keras.models.Model(
    inputs=[model.inputs],
    outputs=[model.get_layer(last_conv_layer_name).output, model.output]
)

print("Running gradtape...")
with tf.GradientTape() as tape:
    conv_outputs, predictions = grad_model(img_array)
    loss = predictions[:, 0]

grads = tape.gradient(loss, conv_outputs)
print("Grads shape:", grads.shape)
