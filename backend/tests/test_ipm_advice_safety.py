"""A photo or user-selected severity cannot establish a treatment threshold."""

from app.api.ipm_advisor import get_ipm_advice
from app.api.seven_class_model import CLASSES


def check():
    for label in CLASSES:
        for severity in ("low", "medium", "high"):
            advice = get_ipm_advice(label, severity)
            assert advice["recommendation"]
            assert advice["threshold_reached"] is False
            assert advice["chemical_methods"] == []
            assert "phun ngay" not in advice["recommendation"].lower()
            assert "rút cạn nước" not in advice["recommendation"].lower()
    assert "Bạn báo" in get_ipm_advice("brown_spot", "high")["recommendation"]


if __name__ == "__main__":
    check()
    print("IPM advice safety checks passed")
