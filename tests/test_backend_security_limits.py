"""Yerel HTTP güvenlik regresyonları; yalnız sentetik sır ve sahte sağlayıcı."""
import contextlib
import http.client
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import server


@pytest.fixture
def live(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    server._rate_buckets.clear()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd.server_port
    httpd.shutdown()
    httpd.server_close()
    thread.join(2)
    server._rate_buckets.clear()


def call(port, path, method="GET", body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


@pytest.mark.parametrize("path", ["/api/health?token=", "/unknown/"])
def test_request_target_does_not_reach_logs(live, path, capsys):
    canary = "OMEGA_SYNTHETIC_QUERY_SECRET_123456"
    call(live, path + canary)
    out = capsys.readouterr()
    assert canary not in out.out + out.err


def test_forwarded_headers_cannot_bypass_real_peer_rate_limit(live, monkeypatch):
    monkeypatch.setattr(server, "RATE_LIMIT_PER_MINUTE", 2)
    statuses = [call(live, "/api/chat", "POST", b'{"message":"hello"}',
                     {"X-Forwarded-For": "203.0.113." + str(i)})[0]
                for i in range(3)]
    assert statuses == [503, 503, 429]


@pytest.mark.parametrize("field", ["name", "type", "source", "sha256"])
def test_configured_secret_metadata_never_reaches_model_input(monkeypatch, field):
    canary = "OMEGA_SYNTHETIC_CONFIGURED_KEY_123456"
    monkeypatch.setenv("OPENAI_API_KEY", canary)
    output = server.build_input("hello", [{field: canary, "size": 1}])
    assert canary not in output
    assert "GIZLI_DEGER_MASKELENDI" in output


@pytest.mark.parametrize("size", [{"secret": "NESTED_CANARY"}, ["ARRAY_CANARY"], -1, True, "TEXT_CANARY"])
def test_invalid_attachment_size_is_not_forwarded(size):
    output = server.build_input("hello", [{"name": "a.txt", "size": size}])
    metadata = json.loads(output.split("\n")[-1])
    assert metadata[0]["size"] is None
    assert "CANARY" not in output


def test_user_message_known_secret_is_masked_before_model(monkeypatch):
    canary = "OMEGA_SYNTHETIC_CONFIGURED_KEY_123456"
    monkeypatch.setenv("OPENAI_API_KEY", canary)
    assert canary not in server.build_input("hello " + canary, [])


def test_known_token_form_is_masked_without_configured_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    canary = "sk-" + "A" * 32
    assert canary not in server.build_input(canary, [])


def test_model_listing_unknown_exception_cannot_reach_response_or_traceback(live, monkeypatch, capsys):
    canary = "OMEGA_SYNTHETIC_PROVIDER_FAILURE_123456"
    monkeypatch.setenv("OPENAI_API_KEY", "NOT_A_REAL_API_KEY")
    def failing():
        raise OSError(canary)
    monkeypatch.setattr(server, "fetch_openai_model_ids", failing)
    status, payload = call(live, "/api/models")
    captured = capsys.readouterr()
    assert status == 502
    assert payload == {"error": "MODEL_LIST_UNAVAILABLE"}
    assert canary not in captured.out + captured.err
    assert "Traceback" not in captured.err


def test_partial_body_hits_timeout_and_returns_safe_json(live, monkeypatch):
    monkeypatch.setattr(server, "REQUEST_READ_TIMEOUT_SECONDS", 0.1)
    c = http.client.HTTPConnection("127.0.0.1", live, timeout=2)
    try:
        c.putrequest("POST", "/api/chat")
        c.putheader("Content-Length", "50")
        c.endheaders()
        c.send(b"{")
        response = c.getresponse()
        assert response.status == 408
        assert json.loads(response.read())["error"] == "REQUEST_TIMEOUT"
    finally:
        c.close()


def test_rate_bucket_capacity_fails_closed_and_reclaims_stale_entries(monkeypatch):
    monkeypatch.setattr(server, "MAX_RATE_BUCKETS", 2)
    server._rate_buckets.clear()
    assert server.rate_allowed("a", 100)
    assert server.rate_allowed("b", 100)
    assert not server.rate_allowed("c", 101)
    assert len(server._rate_buckets) == 2
    assert server.rate_allowed("c", 162)
    assert len(server._rate_buckets) <= 2
    server._rate_buckets.clear()


def test_binary_secret_scan_is_quiet_and_detects_synthetic_value(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    canary = "sk-proj-" + "Q" * 32
    (tmp_path / "fixture.bin").write_bytes(b"\x00" + canary.encode())
    subprocess.run(["git", "-C", str(tmp_path), "add", "fixture.bin"], check=True)
    result = subprocess.run(["git", "-C", str(tmp_path), "grep", "-a", "-q", "-E",
                             "sk-proj-[A-Za-z0-9_-]{16,}"], capture_output=True)
    assert result.returncode == 0
    assert not result.stdout and not result.stderr


def test_deeply_nested_json_returns_fixed_input_error(live, capsys):
    payload = b'{"message":' + b'[' * 10000 + b'0' + b']' * 10000 + b'}'
    status, body = call(live, "/api/chat", "POST", payload)
    captured = capsys.readouterr()
    assert status == 400
    assert body["error"] == "INVALID_JSON"
    assert "Traceback" not in captured.err
