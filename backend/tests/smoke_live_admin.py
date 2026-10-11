"""Read-only smoke check against the running local API."""
import httpx
from app.api.auth import create_access_token


def check():
    base = "http://127.0.0.1:8015"
    with httpx.Client(timeout=15) as client:
        def response(email, path):
            token = create_access_token({"sub": email})
            return client.get(base + path, headers={"Authorization": f"Bearer {token}"})

        assert client.get(base + "/api/health").status_code == 200
        library = client.get(base + "/api/disease-library").json()["data"]
        assert len(library) == 7
        assert response("quanghuycavbhp@gmail.com", "/api/admin/stats").status_code == 200
        assert response("quanghuycavbhp@gmail.com", "/api/admin/users").status_code == 200
        assert response("quanghuycavbhp@gmail.com", "/api/admin/mobile").status_code == 200
        employee_stats = response("huydaothptnbk@gmail.com", "/api/admin/stats")
        assert employee_stats.status_code == 200
        assert all(row["user"] == "Ẩn danh" for row in employee_stats.json()["recent_scans"])
        assert response("huydaothptnbk@gmail.com", "/api/admin/content").status_code == 200
        assert response("huydaothptnbk@gmail.com", "/api/admin/users").status_code == 403
        assert response("admin@gmail.com", "/api/admin/stats").status_code == 403
        employee_token = create_access_token({"sub": "huydaothptnbk@gmail.com"})
        assert client.post(base + "/api/admin/content/invalid/publish",
                           headers={"Authorization": f"Bearer {employee_token}"}).status_code == 403


if __name__ == "__main__":
    check()
    print("Live admin API smoke checks passed")
