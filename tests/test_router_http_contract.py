import json
import os
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import server


def _start_server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread


def _get_json(base, path):
    with urllib.request.urlopen(base + path, timeout=5) as r:
        return r.status, json.loads(r.read())


def test_http_router_contract_fail_closed(monkeypatch):
    # CI must never depend on real provider credentials.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("AI_BACKEND_PROXY_TOKEN", raising=False)

    httpd, thread = _start_server()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        status, health = _get_json(base, "/api/health")
        assert status == 200
        assert health["status"] == "PASS"
        assert health["version"] == "0.2.0"
        assert health["providers_configured"] == {
            "openai": False,
            "huggingface": False,
        }
        assert health["proxy_auth_configured"] is False
        assert health["default_provider"] == "openai"
        assert health["default_profile"] == "max"

        status, providers = _get_json(base, "/api/providers")
        assert status == 200
        by_id = {item["id"]: item for item in providers["providers"]}
        assert by_id["openai"]["profiles"]["max"] == "gpt-6-astra"
        assert by_id["openai"]["profiles"]["balanced"] == "gpt-6-sol"
        assert by_id["openai"]["profiles"]["fast"] == "gpt-6-luna"
        assert by_id["huggingface"]["profiles"]["balanced"] == "openai/gpt-oss-20b:preferred"

        status, models = _get_json(base, "/api/models")
        assert status == 200
        assert "gpt-6-astra" in models["openai"]["allowed"]
        assert "deepseek-ai/DeepSeek-R1:preferred" in models["huggingface"]["allowed"]

        req = urllib.request.Request(
            base + "/api/chat",
            data=json.dumps({
                "message": "probe",
                "provider": "openai",
                "profile": "max",
            }).encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 503
            body = json.loads(exc.read())
            assert body["error"] == "PROXY_AUTH_NOT_CONFIGURED"
        else:
            raise AssertionError("chat unexpectedly accepted without proxy auth")
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
