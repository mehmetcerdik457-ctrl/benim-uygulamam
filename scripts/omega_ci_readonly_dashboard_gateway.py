"""CI-ONLY allowlisted read-only loopback ingress for synthetic OMEGA dashboard.

No production use; NO real user/IdP authentication, no owner-device acceptance.
Separate from Docker's native port binding. No OMEGA network modification,
no external listener, no proxying arbitrary URLs/methods/headers/cookies,
no redirects, no credentials, no logging request bodies or Docker details.
Only in an explicitly requested GitHub Actions disposable CI job.

A safe production ingress would need an independently approved identity,
authorization, provenance, incident-recovery, and lifecycle design.
"""
import argparse
import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from omega_runner_host_direct_route import target_ip
from omega_runner_host_port_audit import audit

HOST = "127.0.0.1"
PORT = 18080
MAX_BODY = 65536
ALLOWED = {
    "/": "text/html; charset=utf-8",
    "/assets/dashboard.js": "text/javascript; charset=utf-8",
    "/assets/dashboard.css": "text/css; charset=utf-8",
    "/api/health": "application/json",
    "/api/readiness": "application/json",
    "/api/demo/inspection": "application/json",
    "/api/demo/task-status": "application/json",
}
_NO_CACHE = ("no-store", "no-cache")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _fetch(upstream, path, *, opener=None, limit=MAX_BODY):
    """Pinned URL, static path only. No headers/cookies forwarded or redirects."""
    if path not in ALLOWED or not isinstance(upstream, str) or not upstream:
        return None
    op = opener if opener is not None else build_opener(
        ProxyHandler({}), _NoRedirect()).open
    try:
        req = Request("http://" + upstream + ":8000" + path,
                      method="GET", headers={"Accept": "*/*"})
        with op(req, timeout=3) as response:
            if response.status != 200:
                return None
            data = response.read(limit + 1)
            if len(data) > limit:
                return None
            return data
    except (OSError, URLError, HTTPError, ValueError, TypeError):
        return None


def _is_mock(upstream, opener=None):
    payload = _fetch(upstream, "/api/health", opener=opener, limit=2048)
    if payload is None:
        return False
    try:
        value = json.loads(payload)
    except (ValueError, TypeError, UnicodeDecodeError):
        return False
    return (isinstance(value, dict)
            and value.get("service") == "omega-mvi-demo"
            and value.get("mode") == "mock"
            and value.get("production_ready") is False
            and value.get("external_api_enabled") is False)


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass  # No URL, headers, or error logs.

    def _reply(self, status, data=b"", kind="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'self'; "
                         "style-src 'self'; connect-src 'self'; "
                         "img-src 'none'; frame-ancestors 'none'; "
                         "base-uri 'none'; form-action 'none'")
        self.end_headers()
        if data:
            self.wfile.write(data)

    def _reject(self, code=403):
        self.close_connection = True
        self._reply(code, b'{"error":"DENIED"}')

    def do_GET(self):
        # DNS-rebinding and confused-deputy controls, no Host variants.
        hosts = self.headers.get_all("Host", [])
        if len(hosts) != 1 or hosts[0] != "127.0.0.1:" + str(self.server.server_port):
            return self._reject()
        # Host may be trusted, but Origin, Upgrade and proxy auth are not.
        origin = self.headers.get("Origin")
        if (origin not in (None, "http://127.0.0.1:" + str(self.server.server_port))
                or self.headers.get("Upgrade") is not None
                or self.headers.get("Authorization") is not None
                or self.headers.get("Proxy-Authorization") is not None
                or self.headers.get("Cookie") is not None
                or self.headers.get("Transfer-Encoding") is not None
                or self.headers.get("Content-Length") is not None):
            return self._reject()
        parsed = urlsplit(self.path)
        if (parsed.scheme or parsed.netloc or parsed.query or parsed.fragment
                or parsed.path not in ALLOWED or self.path != parsed.path):
            return self._reject(404)
        # Even the aggregate demo endpoint is denied by default in this
        # unauthenticated CI example. Never turn the mock DB into a public API.
        if parsed.path == "/api/demo/task-status":
            return self._reject()
        if not _is_mock(self.server.upstream, self.server.upstream_open):
            return self._reject(503)
        data = _fetch(self.server.upstream, parsed.path,
                      opener=self.server.upstream_open)
        if data is None:
            return self._reject(503)
        self._reply(200, data, ALLOWED[parsed.path])

    def do_POST(self):
        return self._reject(405)

    def do_PUT(self):
        return self._reject(405)

    def do_PATCH(self):
        return self._reject(405)

    def do_DELETE(self):
        return self._reject(405)

    def do_HEAD(self):
        return self._reject(405)

    def do_OPTIONS(self):
        return self._reject(405)


class _Server(ThreadingHTTPServer):
    daemon_threads = False
    block_on_close = True
    allow_reuse_address = False

    def __init__(self, addr, upstream, opener=None):
        if (not isinstance(addr, tuple) or len(addr) != 2
                or addr[0] != HOST or not isinstance(addr[1], int)
                or isinstance(addr[1], bool) or not 0 <= addr[1] <= 65535):
            raise ValueError("CI-only IPv4 loopback required")
        self.upstream = upstream
        self.upstream_open = opener
        super().__init__(addr, _Handler)


def experiment():
    evidence = audit()
    if (evidence.get("requested") != "LOOPBACK_ONLY"
            or evidence.get("effective") != "MISSING"
            or evidence.get("network") != "INTERNAL"):
        return "DOCKER_PRECONDITIONS_UNVERIFIED"
    ip, status = target_ip()
    if status != "SINGLE_INTERNAL_BRIDGE_RFC1918" or not ip:
        return "INTERNAL_TARGET_UNVERIFIED"
    if not _is_mock(ip):
        return "MOCK_HEALTH_NOT_VERIFIED"
    try:
        from http.client import HTTPConnection
        with _Server((HOST, PORT), ip) as server:
            thread = threading.Thread(target=server.serve_forever,
                                      kwargs={"poll_interval": 0.02}, daemon=True)
            thread.start()
            try:
                def check(method, path, expected):
                    conn = HTTPConnection(HOST, PORT, timeout=4)
                    try:
                        conn.request(method, path)
                        response = conn.getresponse()
                        status = response.status
                        data = response.read(MAX_BODY + 1)
                        return status == expected and len(data) <= MAX_BODY
                    finally:
                        conn.close()
                if not all(check("GET", path, 200) for path in ALLOWED
                           if path != "/api/demo/task-status"):
                    return "DASHBOARD_GET_NOT_VERIFIED"
                if not check("GET", "/api/demo/task-status", 403):
                    return "DATABASE_DENIAL_NOT_VERIFIED"
                if not all(check("POST", path, 405) for path in (
                        "/api/execute", "/api/chat", "/api/demo/inspection")):
                    return "MUTATION_DENIAL_NOT_VERIFIED"
                if not all(check("GET", path, 404) for path in (
                        "/admin", "/api/health?token=secret", "/%2e%2e/api/health")):
                    return "PATH_DENIAL_NOT_VERIFIED"
            finally:
                server.shutdown()
                thread.join(timeout=3)
                if thread.is_alive():
                    return "INGRESS_SHUTDOWN_UNVERIFIED"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.settimeout(0.5)
            if client.connect_ex((HOST, PORT)) == 0:
                return "INGRESS_LISTENER_PERSISTED"
        return "PASS_CI_READONLY_DASHBOARD_NOT_DOCKER_OR_OWNER"
    except (OSError, ValueError, TypeError):
        return "INGRESS_NOT_VERIFIED"


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--ci-disposable", action="store_true")
    args = parser.parse_args(argv)
    if not args.ci_disposable or os.environ.get("GITHUB_ACTIONS") != "true":
        print("OMEGA_READONLY_INGRESS=DISABLED_OUTSIDE_EXPLICIT_CI")
        return 2
    result = experiment()
    print("OMEGA_READONLY_INGRESS=" + result)
    return 0 if result == "PASS_CI_READONLY_DASHBOARD_NOT_DOCKER_OR_OWNER" else 2


if __name__ == "__main__":
    raise SystemExit(main())
