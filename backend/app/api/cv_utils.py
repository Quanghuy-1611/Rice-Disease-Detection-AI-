import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
import uuid
import os

def generate_gradcam_heatmap(image_bytes, model, class_index, output_dir="uploads"):
    """
    Sinh bản đồ nhiệt Grad-CAM từ ảnh và model Keras.
    Lưu ảnh vào thư mục uploads và trả về đường dẫn.
    """
    try:
        # 1. Đọc ảnh gốc
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None
            
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # 2. Tiền xử lý ảnh cho model (chuẩn MobileNetV2)
        resized_img = cv2.resize(img_rgb, (224, 224))
        img_array = np.expand_dims(resized_img, axis=0)
        img_array = preprocess_input(img_array.astype(np.float32))

        # 3. Tìm layer Convolutional cuối cùng của MobileNetV2
        # MobileNetV2 có layer cuối cùng thường là 'out_relu' hoặc 'Conv_1'
        last_conv_layer_name = None
        for layer in reversed(model.layers):
            try:
                # Keras 3: layer.output may be a tensor with shape attribute
                if hasattr(layer, 'output') and hasattr(layer.output, 'shape') and len(layer.output.shape) == 4:
                    last_conv_layer_name = layer.name
                    break
            except Exception:
                continue
                
        if last_conv_layer_name is None:
            return None

        # 4. Xây dựng mô hình lấy Gradient (Grad-CAM Model)
        grad_model = Model(
            inputs=[model.inputs],
            outputs=[model.get_layer(last_conv_layer_name).output, model.output]
        )

        # 5. Tính toán Gradient
        with tf.GradientTape() as tape:
            conv_outputs, predictions = grad_model(img_array)
            loss = predictions[:, class_index]

        # Extract gradients
        grads = tape.gradient(loss, conv_outputs)
        
        # Pooled gradients
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
        
        # Nhân weights của gradient với output của layer
        conv_outputs = conv_outputs[0]
        heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)

        # Chuẩn hóa heatmap về [0, 1]
        heatmap = tf.maximum(heatmap, 0) / tf.math.reduce_max(heatmap)
        heatmap = heatmap.numpy()

        # 6. Tạo ảnh overlay
        # Phóng to heatmap bằng kích thước ảnh gốc
        heatmap = cv2.resize(heatmap, (img.shape[1], img.shape[0]))
        heatmap = np.uint8(255 * heatmap)
        heatmap_color = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)

        # Trộn ảnh gốc và heatmap
        superimposed_img = cv2.addWeighted(img, 0.6, heatmap_color, 0.4, 0)

        # 7. Lưu file
        os.makedirs(output_dir, exist_ok=True)
        heatmap_filename = f"{uuid.uuid4()}_heatmap.jpg"
        heatmap_path = os.path.join(output_dir, heatmap_filename)
        cv2.imwrite(heatmap_path, superimposed_img)

        return heatmap_filename

    except Exception as e:
        import traceback
        traceback.print_exc()
        print("Error Grad-CAM:", e)
        raise e



