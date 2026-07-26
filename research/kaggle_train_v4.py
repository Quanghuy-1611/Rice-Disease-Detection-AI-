import os
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import ReduceLROnPlateau, EarlyStopping
import matplotlib.pyplot as plt

# 1. Đường dẫn Dataset trên Kaggle
# (Đổi lại tên thư mục tương ứng khi bạn tải zip lên Kaggle)
DATA_DIR = "/kaggle/input/dataset-v4/cleaned_v4" 

IMG_SIZE = (224, 224)
BATCH_SIZE = 64
EPOCHS = 20
NUM_CLASSES = 19

# 2. Chuẩn bị dữ liệu (Data Generator)
print("Đang tải dữ liệu...")
datagen = ImageDataGenerator(
    rescale=1./255,
    validation_split=0.2, # Chia 80% train, 20% validation
    rotation_range=20,
    width_shift_range=0.2,
    height_shift_range=0.2,
    horizontal_flip=True,
    zoom_range=0.2
)

train_gen = datagen.flow_from_directory(
    DATA_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    subset='training',
    shuffle=True
)

val_gen = datagen.flow_from_directory(
    DATA_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    subset='validation',
    shuffle=False
)

print("\nDanh sách 19 Lớp (Classes):")
print(train_gen.class_indices)

# 3. Xây dựng mô hình MobileNetV2 (Transfer Learning)
print("Đang khởi tạo kiến trúc AI MobileNetV2...")
base_model = MobileNetV2(weights='imagenet', include_top=False, input_shape=(224, 224, 3))

# Đóng băng các lớp của MobileNetV2 để giữ lại tri thức gốc
base_model.trainable = False

x = base_model.output
x = GlobalAveragePooling2D()(x)
x = Dense(512, activation='relu')(x)
x = Dropout(0.5)(x)
predictions = Dense(NUM_CLASSES, activation='softmax')(x)

model = Model(inputs=base_model.input, outputs=predictions)

# Compile mô hình
model.compile(optimizer=Adam(learning_rate=0.001), 
              loss='categorical_crossentropy', 
              metrics=['accuracy'])

# 4. Các Callback (Dừng sớm & Giảm Learning Rate nếu mất phương hướng)
callbacks = [
    EarlyStopping(monitor='val_loss', patience=4, restore_best_weights=True),
    ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=2, min_lr=1e-5)
]

# 5. Bắt đầu Train (Giai đoạn 1)
print("=== BẮT ĐẦU HUẤN LUYỆN (GIAI ĐOẠN 1) ===")
history1 = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=10,
    callbacks=callbacks
)

# 6. Fine-Tuning (Giai đoạn 2 - Rã đông 30 lớp cuối để học sâu hơn về Lá Lúa)
print("=== FINE TUNING (GIAI ĐOẠN 2) ===")
base_model.trainable = True
for layer in base_model.layers[:-30]:
    layer.trainable = False

model.compile(optimizer=Adam(learning_rate=1e-5), # Dùng Learning rate cực nhỏ
              loss='categorical_crossentropy', 
              metrics=['accuracy'])

history2 = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=EPOCHS,
    callbacks=callbacks
)

# 7. Vẽ đồ thị đánh giá
acc = history1.history['accuracy'] + history2.history['accuracy']
val_acc = history1.history['val_accuracy'] + history2.history['val_accuracy']
loss = history1.history['loss'] + history2.history['loss']
val_loss = history1.history['val_loss'] + history2.history['val_loss']

plt.figure(figsize=(12, 4))
plt.subplot(1, 2, 1)
plt.plot(acc, label='Training Accuracy')
plt.plot(val_acc, label='Validation Accuracy')
plt.legend(loc='lower right')
plt.title('Training and Validation Accuracy')

plt.subplot(1, 2, 2)
plt.plot(loss, label='Training Loss')
plt.plot(val_loss, label='Validation Loss')
plt.legend(loc='upper right')
plt.title('Training and Validation Loss')
plt.savefig('training_plot.png')
print("Đã lưu đồ thị vào training_plot.png")

# 8. Lưu mô hình (H5 và TFLite)
print("Đang xuất file mô hình...")
model.save("rice_disease_v4.h5")

# Chuyển đổi sang TFLite
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()
with open("model_quantized.tflite", "wb") as f:
    f.write(tflite_model)

print("HOÀN TẤT! Hãy tải file model_quantized.tflite về và đưa vào Backend của dự án.")
