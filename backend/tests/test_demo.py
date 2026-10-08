"""The single-origin demo must initialize auth and preserve SPA routes."""
import importlib
from fastapi.testclient import TestClient

def test_demo_routes(client, tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<html>Atlas demo</html>", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "main.js").write_text("console.log('atlas')", encoding="utf-8")
    monkeypatch.setenv("ATLAS_FRONTEND_DIST", str(tmp_path))
    demo = importlib.import_module("app.demo")
    with TestClient(demo.app) as site:
        assert site.get("/").text == "<html>Atlas demo</html>"
        assert site.get("/app/chat").text == "<html>Atlas demo</html>"
        assert site.get("/assets/main.js").status_code == 200
        assert site.get("/assets/missing.js").status_code == 404
        assert site.get("/api/health").json()["status"] == "ok"
        assert site.get("/api/auth/me").status_code == 401
