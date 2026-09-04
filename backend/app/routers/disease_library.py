from fastapi import APIRouter, HTTPException
import json
import os

router = APIRouter()

DATA_PATH = "app/data/disease_library.json"

def load_disease_library():
    if not os.path.exists(DATA_PATH):
        return []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@router.get("")
def get_disease_library():
    """Lấy danh sách cẩm nang 19 nhóm bệnh."""
    data = load_disease_library()
    return {"success": True, "data": data}

@router.get("/{slug}")
def get_disease_detail(slug: str):
    """Lấy chi tiết một bệnh theo slug."""
    data = load_disease_library()
    for item in data:
        if item["slug"] == slug:
            return {"success": True, "data": item}
    raise HTTPException(status_code=404, detail="Không tìm thấy thông tin bệnh.")
