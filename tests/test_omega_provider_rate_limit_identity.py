"""Offline rate-limit identity contracts; no sockets, credentials or provider calls.

The backend cannot authenticate arbitrary X-Forwarded-For values. Until a
trusted, authenticated per-client proxy identity exists, use the socket peer.
This can pool clients behind one proxy; it is a documented availability
tradeoff and not owner-device acceptance.
"""
from __future__ import annotations

import pytest

from backend import server


@pytest.mark.parametrize("forwarded", [
    "203.0.113.9",
    "198.51.100.15, 203.0.113.50",
    "unknown",
    "",
    "203.0.113.9\r\nX-Injected: value",
])
def test_unattested_forwarded_values_do_not_change_bucket(forwarded):
    peer = "192.0.2.4"
    assert server.client_key({"X-Forwarded-For": forwarded}, peer) == peer


def test_missing_forwarded_header_keeps_socket_peer():
    assert server.client_key({}, "2001:db8::2") == "2001:db8::2"


def test_rotating_untrusted_forwarded_ip_cannot_bypass_rate_limit(monkeypatch):
    monkeypatch.setattr(server, "RATE_LIMIT_PER_MINUTE", 2)
    monkeypatch.setattr(server, "_rate_buckets", server.defaultdict(server.deque))
    peer = "192.0.2.4"
    outcomes = []
    for i in range(4):
        key = server.client_key({"X-Forwarded-For": f"203.0.113.{i+1}"}, peer)
        outcomes.append(server.rate_allowed(key, now=1_000.0))
    assert outcomes == [True, True, False, False]
    assert list(server._rate_buckets) == [peer]


def test_distinct_socket_peers_have_separate_limits(monkeypatch):
    monkeypatch.setattr(server, "RATE_LIMIT_PER_MINUTE", 1)
    monkeypatch.setattr(server, "_rate_buckets", server.defaultdict(server.deque))
    for peer in ("192.0.2.4", "192.0.2.5"):
        key = server.client_key({"X-Forwarded-For": "203.0.113.99"}, peer)
        assert server.rate_allowed(key, now=1_000.0)
        assert not server.rate_allowed(key, now=1_000.0)
