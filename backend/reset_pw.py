import sqlite3
import bcrypt

def reset_all_passwords():
    db_path = r'D:\Phát hiện bệnh cây lúa\backend\paddy_disease.db'
    conn = sqlite3.connect(db_path)
    
    pwd = bcrypt.hashpw(b'123456', bcrypt.gensalt()).decode('utf-8')
    
    # Update all users
    conn.execute("UPDATE users SET hashed_password=?", (pwd,))
    conn.commit()
    
    users = conn.execute("SELECT email FROM users").fetchall()
    print("Reset password to 123456 for:", [u[0] for u in users])
    conn.close()

if __name__ == '__main__':
    reset_all_passwords()
