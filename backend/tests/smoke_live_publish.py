"""End-to-end publish check; restores the original public content even on failure."""
import httpx
from app.api.auth import create_access_token

FIELDS = ("overview", "symptoms", "favorable_conditions", "prevention", "ipm_advice")
BASE = "http://127.0.0.1:8015"


def check():
    with httpx.Client(timeout=15) as client:
        admin = {"Authorization": "Bearer " + create_access_token({"sub": "quanghuycavbhp@gmail.com"})}
        employee = {"Authorization": "Bearer " + create_access_token({"sub": "huydaothptnbk@gmail.com"})}
        items = client.get(BASE + "/api/disease-library").json()["data"]
        item = next(row for row in items if row["slug"] == "normal")
        original = {field: item[field] for field in FIELDS}
        altered = {**original, "overview": original["overview"] + " [kiểm tra đồng bộ]"}
        path = BASE + "/api/admin/content/normal"
        try:
            assert client.put(path, json=altered, headers=employee).status_code == 200
            assert next(row for row in client.get(BASE + "/api/disease-library").json()["data"] if row["slug"] == "normal")["overview"] == original["overview"]
            assert client.post(path + "/publish", headers=employee).status_code == 403
            assert client.post(path + "/publish", headers=admin).status_code == 200
            assert next(row for row in client.get(BASE + "/api/disease-library").json()["data"] if row["slug"] == "normal")["overview"] == altered["overview"]
        finally:
            assert client.put(path, json=original, headers=admin).status_code == 200
            assert client.post(path + "/publish", headers=admin).status_code == 200
        assert next(row for row in client.get(BASE + "/api/disease-library").json()["data"] if row["slug"] == "normal")["overview"] == original["overview"]


if __name__ == "__main__":
    check()
    print("Live draft/publish sync passed; public content restored")
