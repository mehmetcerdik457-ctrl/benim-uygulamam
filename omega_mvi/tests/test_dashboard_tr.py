from pathlib import Path
import sys
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.main import app
def test_turkish_dashboard_is_local_and_execution_denied():
    client=TestClient(app)
    r=client.get("/")
    assert r.status_code==200
    assert "Türkçe güvenli müfettiş" in r.text
    assert "Üretime hazırlık" in r.text
    assert "Content-Security-Policy" in r.headers
    assert client.post("/api/execute",json={"action":"run"}).status_code==403
