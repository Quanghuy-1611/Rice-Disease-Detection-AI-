from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import predict, auth, chat, admin, disease_library
from app.database import engine, Base
import os
from dotenv import load_dotenv

load_dotenv()

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
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(disease_library.router, prefix="/api/disease-library", tags=["Disease Library"])

# Mount thư mục uploads để Frontend có thể lấy ảnh
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def root():
    return {"message": "Chào mừng đến với API Hệ thống nhận diện bệnh cây lúa!"}

@app.get("/api/health")
def health_check():
    import json
    from app.api.chat import OpenAI
    
    # Kiểm tra Chat API
    chat_ready = False
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and OpenAI is not None:
        chat_ready = True
        
    # Kiểm tra Disease Library
    disease_library_ready = False
    if os.path.exists("app/data/disease_library.json"):
        try:
            with open("app/data/disease_library.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                if len(data) == 19:
                    disease_library_ready = True
        except Exception:
            pass
            
    return {
        "status": "ok",
        "chat_ready": chat_ready,
        "disease_library_ready": disease_library_ready
    }
