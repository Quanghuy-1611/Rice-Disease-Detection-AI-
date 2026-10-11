"""Phone photos are oriented and bounded before model inference."""

from io import BytesIO
from unittest.mock import patch

from PIL import Image

from app.api.image_quality import prepare_image


def check():
    image = Image.new("RGB", (300, 200), (90, 130, 70))
    exif = Image.Exif()
    exif[274] = 6  # Rotate 90 degrees clockwise for display.
    source = BytesIO()
    image.save(source, format="JPEG", exif=exif)
    prepared = prepare_image(source.getvalue())
    assert prepared.size == (200, 300)
    assert prepared.getexif().get(274) is None

    with patch("app.api.image_quality.MAX_INPUT_PIXELS", 50_000):
        try:
            prepare_image(source.getvalue())
        except ValueError as exc:
            assert "50 megapixel" in str(exc)
        else:
            raise AssertionError("Oversized input should be rejected before decoding")

    large = Image.new("RGB", (2400, 1800), (90, 130, 70))
    source = BytesIO()
    large.save(source, format="JPEG")
    assert prepare_image(source.getvalue()).size == (1920, 1440)


if __name__ == "__main__":
    check()
    print("Image orientation and size checks passed")
