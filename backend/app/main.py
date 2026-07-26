from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import predict, auth, chat, admin
from app.database import engine, Base
import os

# Tự động tạo bảng trong CSDL nếu chưa có
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Hệ thống Nhận diện bệnh cây lúa API",
    description="API cho mô hình AI phân loại bệnh trên lá lúa.",
    version="1.0.0"
)

# Cấu hình CORS để cho phép Frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Trong thực tế nên giới hạn domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các API routes
app.include_router(predict.router, prefix="/api", tags=["Predict"])
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

# Mount thư mục uploads để Frontend có thể lấy ảnh
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def root():
    return {"message": "Chào mừng đến với API Hệ thống nhận diện bệnh cây lúa!"}
