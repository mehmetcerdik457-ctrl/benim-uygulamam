"""Negative regression tests for request header rate-limit and access-log privacy.

Provider calls are not used. Static synthetic tokens are not real credentials.
"""
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import server


def test_client_key_does_not_trust_spoofed_forwarded_for():
    headers = Message()
    headers["X-Forwarded-For"] = "192.0.2.123, 198.51.100.2"
    assert server.client_key(headers, "127.0.0.1") == "127.0.0.1"


def test_client_key_is_stable_under_many_forwarded_headers():
    peer = "127.0.0.1"
    for spoofed in ("", "192.0.2.12", "192.0.2.13", "127.0.0.1"):
        headers = Message()
        headers["X-Forwarded-For"] = spoofed
        assert server.client_key(headers, peer) == peer


def test_http_access_log_redacts_query_secrets(capsys):
    sentinel = "OMEGA_SYNTHETIC_QUERY_SECRET"
    handler = SimpleNamespace(command="GET", path="/api/health?key=" + sentinel)
    server.Handler.log_message(
        handler, '"%s" %s %s',
        "GET /api/health?key=" + sentinel + " HTTP/1.1", "200", "-"
    )
    output = capsys.readouterr().out
    assert sentinel not in output
    assert "route=/api/health" in output
    assert "status=200" in output


def test_http_access_log_does_not_emit_unknown_path_or_raw_message(capsys):
    sentinel = "OMEGA_SYNTHETIC_PATH_SECRET"
    handler = SimpleNamespace(command="GET", path="/untrusted/" + sentinel)
    server.Handler.log_message(handler, sentinel, sentinel)
    output = capsys.readouterr().out
    assert sentinel not in output
    assert "route=OTHER" in output


def test_http_access_log_does_not_emit_raw_method_or_status(capsys):
    sentinel = "OMEGA_SYNTHETIC_INJECTION"
    handler = SimpleNamespace(command=sentinel, path="/api/models")
    server.Handler.log_message(handler, '"%s" %s %s', sentinel, sentinel, "-")
    output = capsys.readouterr().out
    assert sentinel not in output
    assert "method=OTHER" in output
    assert "status=UNKNOWN" in output
