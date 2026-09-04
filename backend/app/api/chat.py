import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

router = APIRouter()

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def get_client():
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return None, None

    try:
        client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
        return client, api_key
    except Exception:
        return None, None

class ChatRequest(BaseModel):
    message: str

SYSTEM_PROMPT = """Bạn là một chuyên gia nông nghiệp hàng đầu Việt Nam, chuyên tư vấn về cây lúa và các bệnh trên lúa.
Tên của bạn là RiceAI Bot.
Hãy trả lời các câu hỏi của bà con nông dân một cách ngắn gọn, dễ hiểu, thân thiện và thực tế.
Tuyệt đối không trả lời các câu hỏi ngoài phạm vi nông nghiệp, cây trồng, đặc biệt là các vấn đề chính trị, xã hội, tôn giáo.
Nếu được hỏi ngoài lề, hãy lịch sự từ chối và hướng họ quay lại chủ đề nông nghiệp."""

@router.post("/ask")
async def chat_with_bot(req: ChatRequest):
    client, api_key = get_client()

    if not api_key:
        raise HTTPException(status_code=503, detail="Chưa cấu hình OPENAI_API_KEY ở backend.")

    if OpenAI is None:
        raise HTTPException(status_code=503, detail="Thiếu thư viện OpenAI ở backend.")

    if not client:
        raise HTTPException(status_code=503, detail="Lỗi khởi tạo OpenAI Client.")

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": req.message},
            ],
            temperature=0.7,
        )
        reply = response.choices[0].message.content
        if reply:
            return {
                "reply": reply,
                "sources": [{"title": "Khuyến nông Quốc gia", "url": "http://www.khuyennongvn.gov.vn"}]
            }
        raise HTTPException(status_code=503, detail="Không nhận được phản hồi từ AI.")
    except Exception as e:
        error_text = str(e).lower()
        if "quota" in error_text or "resource exhausted" in error_text or "429" in error_text:
            raise HTTPException(status_code=503, detail="Dịch vụ AI hiện đang quá tải hoặc hết Quota.")
        raise HTTPException(status_code=503, detail=f"Lỗi khi gọi AI: {str(e)}")
