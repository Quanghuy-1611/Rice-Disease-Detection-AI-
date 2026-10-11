from fastapi import APIRouter, HTTPException, Depends
import json
from pathlib import Path
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import DiseaseContent
from app.api.seven_class_model import CLASSES

router = APIRouter()

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "disease_library.json"

def load_disease_library():
    if not DATA_PATH.exists():
        return []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return [item for item in json.load(f) if item.get("slug") in CLASSES]

def published_library(db: Session):
    items = load_disease_library()
    overrides = {row.slug: row for row in db.query(DiseaseContent).all()}
    for item in items:
        row = overrides.get(item["slug"])
        if row and row.published_json:
            item.update(json.loads(row.published_json))
    return items


@router.get("")
def get_disease_library(db: Session = Depends(get_db)):
    """Lấy danh sách cẩm nang đúng bảy lớp của mô hình đang triển khai."""
    data = published_library(db)
    return {"success": True, "data": data}

@router.get("/{slug}")
def get_disease_detail(slug: str, db: Session = Depends(get_db)):
    """Lấy chi tiết một bệnh theo slug."""
    data = published_library(db)
    for item in data:
        if item["slug"] == slug:
            return {"success": True, "data": item}
    raise HTTPException(status_code=404, detail="Không tìm thấy thông tin bệnh.")
