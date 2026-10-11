import os
import sys

# Thêm thư mục hiện tại vào PYTHONPATH để nhận diện package 'app'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from app.models import User, Diagnosis

print("="*40)
print("TIẾN TRÌNH RESET DATABASE CÂY LÚA")
print("="*40)

print("[1] Đang xóa toàn bộ dữ liệu cũ...")
Base.metadata.drop_all(bind=engine)

print("[2] Đang tạo lại các bảng CSDL (Users, Diagnoses)...")
Base.metadata.create_all(bind=engine)

print("="*40)
print("✅ KHỞI TẠO DATABASE THÀNH CÔNG!")
print("Đăng ký bằng Firebase và cấp vai trò qua khu vực quản trị an toàn.")
print("="*40)
