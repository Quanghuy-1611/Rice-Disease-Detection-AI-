import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import User
from app.api.auth import get_password_hash

def create_admin():
    db = SessionLocal()
    admin_email = "admin@riceai.com"
    
    # Check if admin already exists
    admin_user = db.query(User).filter(User.email == admin_email).first()
    if admin_user:
        print(f"Admin account '{admin_email}' already exists.")
        db.close()
        return

    # Create new admin
    hashed_password = get_password_hash("admin123")
    new_admin = User(
        email=admin_email,
        hashed_password=hashed_password,
        full_name="Quản trị viên",
        role="admin"
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    print(f"Admin account created successfully! Email: {admin_email}, Password: admin123")
    db.close()

if __name__ == "__main__":
    create_admin()
