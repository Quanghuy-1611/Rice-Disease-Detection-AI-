from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import predict, plus_predict, auth, chat, admin, disease_library, client, plans
from app.database import engine, Base
import os
import mimetypes
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
app.include_router(plus_predict.router, prefix="/api", tags=["Plus Predict"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(client.router, prefix="/api/client", tags=["Client"])
app.include_router(plans.router, prefix="/api/plans", tags=["Plans"])
app.include_router(disease_library.router, prefix="/api/disease-library", tags=["Disease Library"])

# Mount thư mục uploads để Frontend có thể lấy ảnh
os.makedirs("uploads", exist_ok=True)
mimetypes.add_type("application/vnd.android.package-archive", ".apk")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def root():
    return {"message": "Chào mừng đến với API Hệ thống nhận diện bệnh cây lúa!"}

@app.get("/api/health")
def health_check():
    import json
    from app.api.chat import OpenAI
    from app.api.plans import plus_model_ready
    from app.api.seven_class_model import CLASSES, model
    
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
                if len([item for item in data if item.get("slug") in CLASSES]) == len(CLASSES):
                    disease_library_ready = True
        except Exception:
            pass
            
    return {
        "status": "ok",
        "model_ready": model.model is not None,
        "plus_model_ready": plus_model_ready(),
        "model_classes": list(CLASSES),
        "chat_ready": chat_ready,
        "disease_library_ready": disease_library_ready
    }
