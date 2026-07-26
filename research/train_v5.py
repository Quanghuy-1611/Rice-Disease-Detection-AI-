import os
import json
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import ReduceLROnPlateau, EarlyStopping, ModelCheckpoint
import matplotlib.pyplot as plt

# ===================== CẤU HÌNH =====================
DATA_DIR    = r"D:\Phát hiện bệnh cây lúa\research\data\cleaned_v4"
OUTPUT_DIR  = r"D:\Phát hiện bệnh cây lúa\backend\app\model"
IMG_SIZE    = (224, 224)
BATCH_SIZE  = 32
EPOCHS_S1   = 15  # Tăng lên 15 để feature extraction tốt hơn
EPOCHS_S2   = 15  # Tăng lên 15 để học sâu hơn
# =====================================================


def build_callbacks(checkpoint_path):
    """Tạo callbacks MỚI cho mỗi giai đoạn (tránh state rò rỉ giữa 2 lần fit)."""
    return [
        EarlyStopping(
            monitor='val_loss', patience=4,
            restore_best_weights=True, verbose=1
        ),
        ReduceLROnPlateau(
            monitor='val_loss', factor=0.5,
            patience=2, min_lr=1e-6, verbose=1
        ),
        ModelCheckpoint(
            checkpoint_path, monitor='val_loss',
            save_best_only=True, verbose=1
        ),
    ]


def plot_history(history, title, save_path):
    """Vẽ đồ thị Accuracy & Loss và lưu ảnh."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].plot(history.history['accuracy'],     label='Train Accuracy')
    axes[0].plot(history.history['val_accuracy'], label='Val Accuracy')
    axes[0].set_title(f'{title} — Accuracy')
    axes[0].legend(); axes[0].grid(True)

    axes[1].plot(history.history['loss'],     label='Train Loss')
    axes[1].plot(history.history['val_loss'], label='Val Loss')
    axes[1].set_title(f'{title} — Loss')
    axes[1].legend(); axes[1].grid(True)

    fig.tight_layout()
    fig.savefig(save_path, dpi=120)
    plt.close(fig)
    print(f"Đã lưu đồ thị: {save_path}")


def train():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- 1. Data Generators ---
    print("Đang tải dữ liệu từ máy tính của bạn...")

    # Train: preprocess_input chuẩn MobileNetV2 + CỰC HARDCORE AUGMENTATION
    train_datagen = ImageDataGenerator(
        preprocessing_function=preprocess_input,
        validation_split=0.2,
        rotation_range=40,
        width_shift_range=0.3,
        height_shift_range=0.3,
        shear_range=0.2,
        zoom_range=0.3,
        horizontal_flip=True,
        brightness_range=[0.5, 1.5], # Giả lập ảnh chụp tối mờ hoặc chói lóa ngoài đồng ruộng
        fill_mode='nearest'
    )
    # Val: CHỈ normalize, tuyệt đối KHÔNG augment để đánh giá chính xác
    val_datagen = ImageDataGenerator(
        preprocessing_function=preprocess_input,
        validation_split=0.2
    )

    train_gen = train_datagen.flow_from_directory(
        DATA_DIR, target_size=IMG_SIZE, batch_size=BATCH_SIZE,
        class_mode='categorical', subset='training',
        shuffle=True, seed=42
    )
    val_gen = val_datagen.flow_from_directory(
        DATA_DIR, target_size=IMG_SIZE, batch_size=BATCH_SIZE,
        class_mode='categorical', subset='validation',
        shuffle=False, seed=42
    )

    num_classes = len(train_gen.class_indices)
    print(f"\nPhát hiện {num_classes} lớp bệnh trong dataset.")
    print(train_gen.class_indices)

    # Lưu file JSON ánh xạ index -> tên lớp để Backend dùng lúc inference
    # VD: {"0": "bacterial_leaf_blight", "1": "blast", ...}
    idx_to_class = {str(v): k for k, v in train_gen.class_indices.items()}
    class_map_path = os.path.join(OUTPUT_DIR, "class_indices.json")
    with open(class_map_path, 'w', encoding='utf-8') as f:
        json.dump(idx_to_class, f, ensure_ascii=False, indent=2)
    print(f"Đã lưu class mapping → {class_map_path}")

    # --- 2. Xây dựng Model ---
    print("\nĐang khởi tạo kiến trúc AI MobileNetV2...")
    base_model = MobileNetV2(weights='imagenet', include_top=False, input_shape=(224, 224, 3))
    base_model.trainable = False

    x = GlobalAveragePooling2D()(base_model.output)
    x = Dense(256, activation='relu')(x)   # 256 node vừa đủ, tránh overfit
    x = Dropout(0.4)(x)                    # Dropout 0.4 giữ tốt tính tổng quát
    out = Dense(num_classes, activation='softmax')(x)
    model = Model(inputs=base_model.input, outputs=out)

    model.compile(
        optimizer=Adam(learning_rate=1e-3),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    # --- 3. Giai đoạn 1: Train phần đầu mạng (Feature Extraction) ---
    print("\n=== GIAI ĐOẠN 1: TRAIN HEAD (Feature Extraction) ===")
    print("Cảnh báo: Hãy cắm sạc Laptop! Quá trình này có thể tốn vài tiếng.")
    ckpt_s1 = os.path.join(OUTPUT_DIR, "best_stage1.keras")
    h1 = model.fit(
        train_gen, validation_data=val_gen,
        epochs=EPOCHS_S1,
        callbacks=build_callbacks(ckpt_s1)
    )
    plot_history(h1, "Giai đoạn 1", os.path.join(OUTPUT_DIR, "plot_stage1.png"))

    # --- 4. Giai đoạn 2: Fine-Tuning (Mở đông 60 lớp cuối) ---
    print("\n=== GIAI ĐOẠN 2: FINE-TUNING (60 lớp cuối MobileNetV2) ===")
    base_model.trainable = True
    for layer in base_model.layers[:-60]:
        layer.trainable = False

    # Compile lại với learning rate CỰC NHỎ để không phá hủy kiến thức cũ
    model.compile(
        optimizer=Adam(learning_rate=1e-5),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    ckpt_s2 = os.path.join(OUTPUT_DIR, "best_stage2.keras")
    h2 = model.fit(
        train_gen, validation_data=val_gen,
        epochs=EPOCHS_S2,
        callbacks=build_callbacks(ckpt_s2)
    )
    plot_history(h2, "Giai đoạn 2 (Fine-tune)", os.path.join(OUTPUT_DIR, "plot_stage2.png"))

    # --- 5. Đánh giá cuối cùng ---
    print("\nĐánh giá cuối cùng trên tập Validation:")
    val_loss, val_acc = model.evaluate(val_gen, verbose=1)
    print(f"\n>>> Val Accuracy: {val_acc * 100:.2f}%  |  Val Loss: {val_loss:.4f}")

    # --- 6. Xuất TFLite (Quantized) ---
    print("\nĐang xuất file TFLite Quantized (model siêu nhẹ)...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()

    tflite_path = os.path.join(OUTPUT_DIR, "model_quantized.tflite")
    with open(tflite_path, "wb") as f:
        f.write(tflite_model)

    print(f"\n✅ HOÀN TẤT!")
    print(f"   Model TFLite: {tflite_path}")
    print(f"   Class map:    {class_map_path}")
    print(f"   Đồ thị train: {OUTPUT_DIR}\\plot_stage1.png & plot_stage2.png")
    print("\nBạn có thể dùng ngay model này trên Website!")


if __name__ == "__main__":
    train()
