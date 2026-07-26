from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import User, Diagnosis
from app.api.auth import get_current_user

router = APIRouter()

@router.get("/stats")
def get_admin_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Không có quyền truy cập. Yêu cầu quyền Admin.")
    
    # 1. Total users
    total_users = db.query(User).count()
    
    # 2. Total scans
    total_scans = db.query(Diagnosis).count()
    
    # 3. Disease distribution
    distribution = db.query(Diagnosis.prediction, func.count(Diagnosis.id)).group_by(Diagnosis.prediction).all()
    disease_distribution = [{"name": pred, "value": count} for pred, count in distribution]
    
    # 4. Recent scans (last 10)
    recent_diagnoses = db.query(Diagnosis).order_by(Diagnosis.created_at.desc()).limit(10).all()
    recent_scans = []
    for diag in recent_diagnoses:
        owner_name = diag.owner.full_name if diag.owner else "Unknown"
        recent_scans.append({
            "id": diag.id,
            "user": owner_name,
            "prediction": diag.prediction,
            "confidence": diag.confidence,
            "created_at": diag.created_at.isoformat(),
            "heatmap_url": diag.image_filename # just returning filename to reconstruct url if needed
        })
        
    return {
        "total_users": total_users,
        "total_scans": total_scans,
        "disease_distribution": disease_distribution,
        "recent_scans": recent_scans
    }
