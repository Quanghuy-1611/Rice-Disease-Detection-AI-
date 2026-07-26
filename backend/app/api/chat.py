import os
from pathlib import Path
from fastapi import APIRouter
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
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")
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
Nếu được hỏi ngoài lề, hãy lịch sự từ chối và hướng họ quay lại chủ đề nông nghiệp.
"""

@router.post("/ask")
async def chat_with_bot(req: ChatRequest):
    client, api_key = get_client()

    if not api_key:
        return {"reply": "Hiện tại chưa có API key được cấu hình. Bạn có thể thử lại sau hoặc hỏi về các bệnh lúa phổ biến như đạo ôn, đốm nâu, bạc lá."}

    if OpenAI is None:
        return {"reply": "Thư viện AI chưa được cài đúng. Vui lòng cài package openai để chatbot hoạt động."}

    if not client:
        return {"reply": "Hiện tại dịch vụ AI chưa khởi tạo được. Bạn có thể thử lại sau vài phút."}

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
            return {"reply": reply}
        return {"reply": "Tôi chưa nhận được phản hồi từ dịch vụ AI. Vui lòng thử lại sau."}
    except Exception as e:
        error_text = str(e).lower()
        if "quota" in error_text or "resource exhausted" in error_text or "429" in error_text:
            return {
                "reply": "Dịch vụ AI hiện đang vượt quá giới hạn truy cập. Bạn có thể thử lại sau vài phút hoặc hỏi về các bệnh lúa phổ biến như đạo ôn, đốm nâu, bạc lá." 
            }
        return {"reply": f"Xin lỗi, tôi gặp lỗi khi gọi AI: {str(e)}"}
