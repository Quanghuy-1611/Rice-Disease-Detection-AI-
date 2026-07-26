import os
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, models, transforms
from torch.utils.data import DataLoader, random_split

# Cấu hình đường dẫn
DATA_DIR = r"D:\Phát hiện bệnh cây lúa\research\data\raw\kaggle_paddy\train_images"
MODEL_SAVE_PATH = r"D:\Phát hiện bệnh cây lúa\backend\model_weights\best_model.pth"

BATCH_SIZE = 32
NUM_EPOCHS = 10
LEARNING_RATE = 0.001

def main():
    print("Khởi tạo tiến trình huấn luyện AI...")
    
    # 1. Data Augmentation và Tiền xử lý
    data_transforms = {
        'train': transforms.Compose([
            transforms.RandomResizedCrop(224),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
        'val': transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
    }

    if not os.path.exists(DATA_DIR):
        print(f"Lỗi: Không tìm thấy thư mục dữ liệu tại {DATA_DIR}.")
        print("Vui lòng đảm bảo bạn đã giải nén file ZIP từ Kaggle vào đúng thư mục `kaggle_paddy` nhé!")
        return

    # 2. Tải dữ liệu
    print("Đang đọc dữ liệu từ thư mục...")
    full_dataset = datasets.ImageFolder(DATA_DIR)
    
    # Chia 80% Train, 20% Validation
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size])
    
    # Áp dụng Transform
    train_dataset.dataset.transform = data_transforms['train']
    # Lưu ý: Ở đây ta gán transform trực tiếp, trong thực tế có thể dùng class bọc (Wrapper Class) để linh hoạt hơn
    # nhưng để dễ hiểu và chạy được ngay thì cách này vẫn hoạt động tốt.

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    
    class_names = full_dataset.classes
    print(f"Tìm thấy {len(class_names)} loại (classes): {class_names}")
    print(f"Số lượng ảnh để huấn luyện (Train): {train_size}")
    print(f"Số lượng ảnh để kiểm thử (Validation): {val_size}")

    # 3. Khởi tạo Mô hình (Transfer Learning với ResNet18)
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"\nĐang sử dụng thiết bị tính toán: {device}")
    if device.type == 'cpu':
        print("Cảnh báo: Bạn đang dùng CPU, quá trình huấn luyện sẽ khá lâu. Nếu máy có Card màn hình rời (NVIDIA), hãy cài đặt CUDA.")
    
    model = models.resnet18(pretrained=True)
    num_ftrs = model.fc.in_features
    # Thay đổi lớp cuối cùng để output ra đúng số lượng bệnh của chúng ta (10 loại)
    model.fc = nn.Linear(num_ftrs, len(class_names))
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

    # 4. Huấn luyện Mô hình
    best_acc = 0.0
    
    for epoch in range(NUM_EPOCHS):
        print(f"\nEpoch {epoch+1}/{NUM_EPOCHS}")
        print("-" * 10)
        
        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()
                dataloader = train_loader
            else:
                model.eval()
                dataloader = val_loader

            running_loss = 0.0
            running_corrects = 0

            for inputs, labels in dataloader:
                inputs = inputs.to(device)
                labels = labels.to(device)

                optimizer.zero_grad()

                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)

                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)

            epoch_loss = running_loss / len(dataloader.dataset)
            epoch_acc = running_corrects.double() / len(dataloader.dataset)

            print(f"{phase.capitalize()} | Loss: {epoch_loss:.4f} | Accuracy: {epoch_acc:.4f}")

            # Lưu lại model có độ chính xác trên tập Validation tốt nhất
            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)
                torch.save(model.state_dict(), MODEL_SAVE_PATH)
                print(f"--> Đã lưu mô hình tốt nhất mới (Val Acc: {best_acc:.4f})")

    print(f"\nHuấn luyện hoàn tất! Độ chính xác cao nhất đạt được: {best_acc:.4f}")
    print(f"Mô hình đã được lưu tại: {MODEL_SAVE_PATH}")

if __name__ == '__main__':
    main()
