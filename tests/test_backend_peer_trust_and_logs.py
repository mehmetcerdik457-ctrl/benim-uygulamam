"""Offline safety tests: untrusted HTTP forwarding and request logging.

No network, tokens, device, or provider account is accessed here.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import server


def test_forwarded_headers_cannot_override_verified_peer():
    peer = "192.0.2.14"
    for headers in (
        {},
        {"X-Forwarded-For": "198.51.100.1"},
        {"X-Forwarded-For": "198.51.100.1, 192.0.2.99"},
        {"X-Real-IP": "198.51.100.2"},
        {"Forwarded": "for=198.51.100.3"},
        {"X-Forwarded-For": "invalid, secret=SYNTHETIC"},
    ):
        assert server.client_key(headers, peer) == peer


def test_spoofed_forwarding_does_not_reset_rate_limit(monkeypatch):
    monkeypatch.setattr(server, "RATE_LIMIT_PER_MINUTE", 1)
    server._rate_buckets.clear()
    try:
        first = server.client_key({"X-Forwarded-For": "198.51.100.8"}, "192.0.2.14")
        second = server.client_key({"X-Forwarded-For": "198.51.100.9"}, "192.0.2.14")
        assert first == second
        assert server.rate_allowed(first, now=100.0)
        assert not server.rate_allowed(second, now=101.0)
        assert server.rate_allowed(second, now=161.1)
    finally:
        server._rate_buckets.clear()


def test_missing_peer_is_fail_closed_single_bucket():
    assert server.client_key({"X-Forwarded-For": "198.51.100.1"}, "") == "UNKNOWN_PEER"


def test_raw_request_line_and_synthetic_secret_never_logged(capsys):
    handler = object.__new__(server.Handler)
    marker = "SYNTHETIC_SECRET_MUST_NOT_APPEAR"
    handler.log_message('"%s" %s %s', f"GET /api/chat?key={marker} HTTP/1.1", "400", "-")
    output = capsys.readouterr().out
    assert output == "HTTP_STATUS status=400\n"
    assert marker not in output
    assert "/api/chat" not in output


def test_untrusted_log_format_and_status_are_discarded(capsys):
    handler = object.__new__(server.Handler)
    handler.log_message("raw attacker text %s", "SYNTHETIC_SECRET")
    handler.log_message('"%s" %s %s', "GET /", "400\nSYNTHETIC_SECRET", "-")
    assert capsys.readouterr().out == ""
