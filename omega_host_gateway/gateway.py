"""Isolated OMEGA DEMO runner-host gateway, never a user or Owner endpoint.

Only GET /api/health and POST /api/execute are relayed to the mock API.
The latter must be DENIED (403); any unexpected approval is a fatal fault.
No arbitrary routes, URL changes, credentials, or request headers are relayed.
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

_UPSTREAM = "http://api:8000"
_MAX_BODY = 2048
_MAX_REPLY = 8192


def _upstream_request(path, *, data=None, opener=None):
    opener = opener or build_opener(ProxyHandler({})).open
    request = Request(_UPSTREAM + path, method="POST" if data is not None else "GET",
                      data=data, headers={"Content-Type": "application/json"})
    try:
        with opener(request, timeout=3) as reply:
            status = reply.status
            payload = reply.read(_MAX_REPLY + 1)
    except HTTPError as exc:
        status = exc.code
        payload = exc.read(_MAX_REPLY + 1)
    except (URLError, OSError, ValueError, TimeoutError):
        return 503, b'{"error":"UPSTREAM_UNAVAILABLE"}'
    if len(payload) > _MAX_REPLY:
        return 503, b'{"error":"UPSTREAM_INVALID"}'
    try:
        decoded = json.loads(payload)
    except (ValueError, UnicodeError):
        return 503, b'{"error":"UPSTREAM_INVALID"}'
    if type(decoded) is not dict:
        return 503, b'{"error":"UPSTREAM_INVALID"}'
    if path == "/api/health":
        if (status != 200 or decoded.get("mode") != "mock"
                or decoded.get("production_ready") is not False):
            return 503, b'{"error":"UPSTREAM_INVALID"}'
        # Return only the minimal safe diagnostic, not other internal metadata.
        return 200, b'{"mode":"mock","production_ready":false}'
    if path == "/api/execute" and status == 403:
        return 403, b'{"error":"EXECUTION_DENIED"}'
    # A backend unexpectedly accepting execution must NEVER be passed through.
    return 503, b'{"error":"UPSTREAM_EXECUTION_POLICY_FAULT"}'


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _reply(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)
        self.close_connection = True

    def do_GET(self):
        if self.path != "/api/health":
            self._reply(404, b'{"error":"ROUTE_NOT_EXPOSED"}')
            return
        status, body = _upstream_request("/api/health")
        self._reply(status, body)

    def do_POST(self):
        if self.path != "/api/execute":
            self._reply(403, b'{"error":"ROUTE_NOT_EXPOSED"}')
            return
        value = self.headers.get("Content-Length")
        if value is None or not value.isascii() or not value.isdecimal() or len(value) > 8:
            self._reply(400, b'{"error":"BODY_DENIED"}')
            return
        length = int(value)
        if length > _MAX_BODY:
            self._reply(413, b'{"error":"BODY_DENIED"}')
            return
        try:
            raw = self.rfile.read(length)
        except (OSError, TimeoutError):
            self._reply(400, b'{"error":"BODY_DENIED"}')
            return
        # No client auth/cookies/forwarded headers or arbitrary URL forwarded.
        status, body = _upstream_request("/api/execute", data=raw)
        self._reply(status, body)

    def log_message(self, format, *args):
        # Request targets and user-controlled headers must never reach CI logs.
        pass


def main():
    # Internal to Docker: externally reachable only via localhost port mapping.
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    server.daemon_threads = True
    server.serve_forever()


if __name__ == "__main__":
    main()
