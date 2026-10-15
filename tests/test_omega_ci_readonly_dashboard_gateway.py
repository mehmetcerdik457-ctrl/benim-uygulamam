"""Socket-level CI-only dashboard ingress tests, no real Docker/network egress."""
import contextlib
from http.client import HTTPConnection
import io
import json
import os
from pathlib import Path
import socket
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import omega_ci_readonly_dashboard_gateway as g


HEALTH = b'{"service":"omega-mvi-demo","mode":"mock","production_ready":false,"external_api_enabled":false}'
ASSETS = {
    "/": b"<!doctype html><title>PROJECT OMEGA</title>",
    "/assets/dashboard.js": b"console.log('safe mock');",
    "/assets/dashboard.css": b"body { color: inherit; }",
    "/api/health": HEALTH,
    "/api/readiness": b'{"production_ready":false}',
    "/api/demo/inspection": b'{"mode":"mock","synthetic":true}',
}


class Response(io.BytesIO):
    status = 200
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


class OpenMock:
    def __init__(self, *, invalid_health=False, giant=False):
        self.paths = []
        self.invalid_health = invalid_health
        self.giant = giant

    def __call__(self, request, timeout=3):
        uri = request.full_url
        self.paths.append(uri)
        self.assert_url(uri)
        path = uri.split(":8000", 1)[1]
        body = ASSETS[path]
        if path == "/api/health" and self.invalid_health:
            body = b'{"service":"omega-mvi-demo","mode":"production","production_ready":true,"external_api_enabled":true}'
        if path == "/" and self.giant:
            body = b"x" * (g.MAX_BODY + 1)
        return Response(body)

    @staticmethod
    def assert_url(url):
        if not url.startswith("http://127.0.0.1:8000/"):
            raise AssertionError("unexpected upstream URL")


def request(port, method, path, *, headers=None):
    conn = HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        conn.request(method, path, headers=headers or {})
        response = conn.getresponse()
        return response.status, response.read(), dict(response.getheaders())
    finally:
        conn.close()


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.fake = OpenMock()
        self.server = g._Server(("127.0.0.1", 0), "127.0.0.1",
                                opener=self.fake)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.port = self.server.server_port

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=3)
        self.server.server_close()
        self.assertFalse(self.thread.is_alive())

    def test_all_dashboard_readonly_paths_render_under_mock_guard(self):
        for path, expected in ASSETS.items():
            with self.subTest(path=path):
                status, body, headers = request(self.port, "GET", path)
                self.assertEqual(status, 200)
                self.assertEqual(body, expected)
                self.assertEqual(headers["Cache-Control"], "no-store")
                self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
                self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_unverified_demo_db_reads_are_denied_without_fetch(self):
        before = len(self.fake.paths)
        status, _, _ = request(self.port, "GET", "/api/demo/task-status")
        self.assertEqual(status, 403)
        self.assertEqual(len(self.fake.paths), before)

    def test_any_write_method_is_denied_before_upstream(self):
        before = len(self.fake.paths)
        for method in ("POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"):
            with self.subTest(method=method):
                status, _, _ = request(self.port, method, "/api/execute")
                self.assertEqual(status, 405)
        self.assertEqual(len(self.fake.paths), before)

    def test_unknown_path_query_traversal_absolute_uri_and_encoded_path_deny(self):
        before = len(self.fake.paths)
        for path in ("/admin", "/api/health?secret=x", "/%2e%2e/api/health",
                     "//evil.invalid/api/health", "/api/%68ealth"):
            with self.subTest(path=path):
                status, _, _ = request(self.port, "GET", path)
                self.assertEqual(status, 404)
        self.assertEqual(len(self.fake.paths), before)

    def test_host_header_mismatch_blocks_before_any_target_call(self):
        before = len(self.fake.paths)
        status, _, _ = request(self.port, "GET", "/", headers={"Host": "evil.invalid"})
        self.assertEqual(status, 403)
        self.assertEqual(len(self.fake.paths), before)

    def test_auth_cookies_upgrade_and_bodies_are_never_forwarded(self):
        for name, value in (("Cookie", "session=sensitive"), ("Authorization", "Bearer xxx"),
                            ("Origin", "https://evil.invalid"),
                            ("Upgrade", "websocket"), ("Content-Length", "0")):
            with self.subTest(name=name):
                before = len(self.fake.paths)
                status, _, _ = request(self.port, "GET", "/", headers={name: value})
                self.assertEqual(status, 403)
                self.assertEqual(len(self.fake.paths), before)

    def test_unhealthy_production_target_rejected(self):
        self.server.upstream_open = OpenMock(invalid_health=True)
        status, _, _ = request(self.port, "GET", "/")
        self.assertEqual(status, 503)

    def test_oversize_static_payload_rejected(self):
        self.server.upstream_open = OpenMock(giant=True)
        status, _, _ = request(self.port, "GET", "/")
        self.assertEqual(status, 503)

    def test_loopback_only_constructor_rejects_external_listeners(self):
        for ip in ("0.0.0.0", "::", "localhost", "192.168.1.2"):
            with self.subTest(ip=ip), self.assertRaises(ValueError):
                g._Server((ip, 0), "127.0.0.1")

    def test_disabled_without_explicit_ci_and_flag(self):
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(g.main(["--ci-disposable"]), 2)
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(g.main([]), 2)

    def test_mock_health_validation_rejects_wrong_service_and_unavailable(self):
        self.assertTrue(g._is_mock("127.0.0.1", self.fake))
        self.assertFalse(g._is_mock("127.0.0.1", OpenMock(invalid_health=True)))
        def blocked(request, timeout=3):
            raise OSError("not published")
        self.assertFalse(g._is_mock("127.0.0.1", blocked))

    def test_only_exact_target_paths_can_be_fetched(self):
        before = len(self.fake.paths)
        self.assertIsNone(g._fetch("127.0.0.1", "http://evil.invalid/",
                                  opener=self.fake))
        self.assertIsNone(g._fetch("127.0.0.1", "/admin", opener=self.fake))
        self.assertEqual(len(self.fake.paths), before)


if __name__ == "__main__":
    unittest.main()
