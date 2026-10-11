from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import bcrypt
from datetime import datetime, timedelta
import jwt
import os
from pathlib import Path
from app.database import get_db
from app.models import User
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

load_dotenv()

router = APIRouter()

# Cấu hình bảo mật
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY is not set in environment variables.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

# Initialize Firebase Admin SDK once. The credential is intentionally read from
# an untracked local JSON file (or an explicit environment variable), never from
# the repository. This is required to verify the Firebase ID token sent by the
# mobile app after its OTP flow succeeds.
_default_firebase_credentials = (
    Path(__file__).resolve().parents[2] / "firebase-adminsdk.json"
)
_firebase_credentials_path = Path(
    os.getenv("FIREBASE_ADMIN_CREDENTIALS", str(_default_firebase_credentials))
)
FIREBASE_ADMIN_READY = bool(firebase_admin._apps)
FIREBASE_ADMIN_ERROR: str | None = None

if not FIREBASE_ADMIN_READY:
    try:
        if not _firebase_credentials_path.is_file():
            raise FileNotFoundError(
                f"Không tìm thấy tệp Firebase Admin: {_firebase_credentials_path}"
            )
        cred = credentials.Certificate(str(_firebase_credentials_path))
        firebase_admin.initialize_app(cred)
        FIREBASE_ADMIN_READY = True
    except Exception as error:
        FIREBASE_ADMIN_ERROR = str(error)
        print("Warning: Firebase Admin SDK initialization failed:", error)

# Pydantic models
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: str
    password: str

class FirebaseExchange(BaseModel):
    id_token: str

class Token(BaseModel):
    access_token: str
    token_type: str
    full_name: str
    role: str

class UserProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Hàm helper lấy user hiện tại từ token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token không hợp lệ")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token đã hết hạn hoặc không hợp lệ")

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Không tìm thấy người dùng")
    return user

@router.post("/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    raise HTTPException(status_code=410, detail="Hãy đăng ký bằng Firebase và xác minh email.")

@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    raise HTTPException(status_code=410, detail="Hãy đăng nhập bằng Firebase với email đã xác minh.")

@router.post("/firebase/exchange", response_model=Token)
def firebase_exchange(req: FirebaseExchange, db: Session = Depends(get_db)):
    if not FIREBASE_ADMIN_READY:
        raise HTTPException(
            status_code=503,
            detail=(
                "Dịch vụ OTP chưa được cấu hình ở máy chủ. "
                "Cần FIREBASE_ADMIN_CREDENTIALS hoặc backend/firebase-adminsdk.json."
            ),
        )
    try:
        # Allow small clock differences between this machine and Firebase.
        # Firebase Admin still verifies the token signature, issuer and expiry.
        decoded_token = firebase_auth.verify_id_token(
            req.id_token, clock_skew_seconds=30
        )
        uid = str(decoded_token.get("uid") or "")
        provider = decoded_token.get("firebase", {}).get("sign_in_provider")
        email = decoded_token.get("email")
        email_verified = bool(decoded_token.get("email_verified"))
        if not uid:
            raise HTTPException(status_code=401, detail="Token Firebase không có mã người dùng.")
        if provider != "anonymous" and (not email or not email_verified):
            raise HTTPException(
                status_code=403,
                detail="Tài khoản cần xác minh email trước khi sử dụng RiceAI.",
            )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=401,
            detail="Phiên Firebase không hợp lệ hoặc đã hết hạn. Hãy đăng nhập lại; nếu lỗi lặp lại, hãy đồng bộ giờ trên máy chủ.",
        ) from e

    # Firebase anonymous users vẫn có một định danh ổn định. Lưu nó dưới một
    # email nội bộ để mô hình User hiện tại không phải nới lỏng ràng buộc email.
    identity_email = (
        f"guest_{uid}@anonymous.riceai" if provider == "anonymous" else email.lower()
    )
    db_user = db.query(User).filter(User.email == identity_email).first()
    
    if not db_user:
        hashed_password = get_password_hash("random_firebase_password")
        display_name = (
            "Khách RiceAI"
            if provider == "anonymous"
            else str(decoded_token.get("name") or identity_email.split("@")[0])
        )
        db_user = User(
            email=identity_email,
            hashed_password=hashed_password,
            full_name=display_name,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

    access_token = create_access_token(data={"sub": db_user.email, "role": db_user.role})
    return {"access_token": access_token, "token_type": "bearer", "full_name": db_user.full_name, "role": db_user.role}

@router.get("/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {"email": current_user.email, "full_name": current_user.full_name, "role": current_user.role}

@router.put("/me")
def update_users_me(
    update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.full_name = update.full_name.strip()
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return {"email": current_user.email, "full_name": current_user.full_name, "role": current_user.role}
