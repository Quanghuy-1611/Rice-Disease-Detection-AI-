"""Fast, conservative upload checks before a diagnosis consumes a quota slot."""

from io import BytesIO

import numpy as np
from PIL import Image, ImageOps


MAX_INPUT_PIXELS = 50_000_000
MAX_INFERENCE_SIDE = 1920


def prepare_image(contents: bytes) -> Image.Image:
    """Honor phone orientation and cap decoded image size before inference."""
    image = Image.open(BytesIO(contents))
    if image.width * image.height > MAX_INPUT_PIXELS:
        raise ValueError("Ảnh có độ phân giải quá lớn. Hãy chọn ảnh dưới 50 megapixel.")
    image.draft("RGB", (MAX_INFERENCE_SIDE, MAX_INFERENCE_SIDE))
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((MAX_INFERENCE_SIDE, MAX_INFERENCE_SIDE), Image.Resampling.LANCZOS)
    return image


def blur_score(image: Image.Image) -> float:
    gray = np.asarray(image.convert("L").resize((224, 224)), dtype=np.float32)
    laplacian = (4 * gray[1:-1, 1:-1] - gray[:-2, 1:-1]
                 - gray[2:, 1:-1] - gray[1:-1, :-2] - gray[1:-1, 2:])
    return float(laplacian.var())


def quality_message(image: Image.Image) -> str | None:
    if min(image.size) < 160:
        return "Ảnh quá nhỏ để phân tích. Hãy chụp lại gần và rõ hơn."
    if np.asarray(image.resize((64, 64)), dtype=np.float32).std() < 8:
        return "Ảnh gần như trống. Hãy chụp lại."
    if blur_score(image) < 30:
        return "Ảnh quá mờ để đưa ra kết luận. Hãy giữ máy ổn định và chụp lại."
    return None
