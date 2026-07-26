import os
import sys

# Thêm thư mục hiện tại vào PYTHONPATH để nhận diện package 'app'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from app.models import User, Diagnosis
from sqlalchemy.orm import Session
import bcrypt

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

print("="*40)
print("TIẾN TRÌNH RESET DATABASE CÂY LÚA")
print("="*40)

print("[1] Đang xóa toàn bộ dữ liệu cũ...")
Base.metadata.drop_all(bind=engine)

print("[2] Đang tạo lại các bảng CSDL (Users, Diagnoses)...")
Base.metadata.create_all(bind=engine)

print("[3] Đang tạo tài khoản Admin mặc định...")
with Session(engine) as session:
    admin_user = User(
        email="admin@gmail.com",
        full_name="Quản Trị Viên",
        hashed_password=get_password_hash("123456"),
        role="admin"
    )
    session.add(admin_user)
    session.commit()

print("="*40)
print("✅ KHỞI TẠO DATABASE THÀNH CÔNG!")
print("Tài khoản : admin@gmail.com")
print("Mật khẩu  : 123456")
print("="*40)
