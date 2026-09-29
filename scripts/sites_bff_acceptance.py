#!/usr/bin/env python3
"""Exercise the Sites server credential through the real runtime HTTP gateway.

Default mode uses a local mock backend. --live uses the configured private backend
and provider credentials already present in the environment. Secret values are
never printed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
LIVE = "--live" in sys.argv
DIAGNOSE = "--diagnose" in sys.argv
MARKER = "SITES_BFF_RUNTIME_OK"


def request(url: str, *, sites_token: str | None = None, payload=None):
    headers = {"Content-Type": "application/json"}
    if sites_token is not None:
        headers["X-Mehmet-Sites-BFF"] = sites_token
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=70) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


class MockBackend(BaseHTTPRequestHandler):
    def do_POST(self):
        assert self.path == "/api/chat"
        assert self.headers.get("X-MEH-Proxy-Token") == "sites-bff-local-proxy"
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert body.get("message")
        data = json.dumps({
            "text": MARKER,
            "provider": "test",
            "model": "local-mock",
            "request_id": "sites-bff-local-test",
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args):
        pass


def main() -> None:
    env = dict(os.environ)
    mock = None

    if LIVE:
        required = ["SITES_BFF_TOKEN", "AI_BACKEND_PROXY_TOKEN", "AI_BACKEND_URL"]
        missing = [name for name in required if not env.get(name)]
        if missing:
            raise SystemExit("LIVE_SETUP_REQUIRED:" + ",".join(missing))
        if len(env["SITES_BFF_TOKEN"].strip()) < 32:
            raise SystemExit("SITES_BFF_TOKEN_TOO_SHORT")
    else:
        mock = ThreadingHTTPServer(("127.0.0.1", 0), MockBackend)
        threading.Thread(target=mock.serve_forever, daemon=True).start()
        env.update(
            SITES_BFF_TOKEN="sites-bff-test-" + secrets.token_urlsafe(32),
            AI_BACKEND_PROXY_TOKEN="sites-bff-local-proxy",
            AI_BACKEND_URL=f"http://127.0.0.1:{mock.server_port}",
        )

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    env["PORT"] = str(port)
    base = f"http://127.0.0.1:{port}"
    token = env["SITES_BFF_TOKEN"]

    with tempfile.TemporaryFile() as log:
        proc = subprocess.Popen(
            [sys.executable, str(ROOT / "runtime_v022_server.py")],
            env=env,
            stdout=log,
            stderr=log,
        )
        try:
            for _ in range(120):
                try:
                    status, raw = request(base + "/__health")
                    if status == 200:
                        break
                except OSError:
                    pass
                if proc.poll() is not None:
                    raise RuntimeError("RUNTIME_START_FAILED")
                time.sleep(0.1)
            else:
                raise RuntimeError("RUNTIME_HEALTH_TIMEOUT")

            health = json.loads(raw)
            assert health["status"] == "PASS"
            assert health["backend_proxy_configured"] is True

            assert request(
                base + "/api/chat",
                payload={"message": "unauthenticated"},
            )[0] == 401

            assert request(
                base + "/api/chat",
                sites_token="wrong-" + token,
                payload={"message": "wrong token"},
            )[0] == 403

            assert request(
                base + "/api/owner/status",
                sites_token=token,
            )[0] == 403

            assert request(
                base + "/api/research",
                sites_token=token,
                payload={"message": "wrong route"},
            )[0] == 403

            status, raw = request(
                base + "/api/chat",
                sites_token=token,
                payload={
                    "provider": "openai",
                    "message": "Bu bir bağlantı testidir. Yalnız "
                    + MARKER
                    + " yaz.",
                    "attachments": [],
                },
            )
            reply = json.loads(raw or b"{}")

            if status != 200:
                result = {
                    "event": "SITES_BFF_CHAT_ACCEPTANCE",
                    "mode": "real-provider" if LIVE else "mock",
                    "status": "BLOCKED",
                    "http_status": status,
                    "upstream_status": reply.get("upstream_status"),
                    "upstream_code": reply.get("upstream_code"),
                    "request_id": reply.get("request_id"),
                }
                print(json.dumps(result), flush=True)
                if DIAGNOSE:
                    return
                raise AssertionError("SITES_BFF_CHAT_STATUS_" + str(status))

            text = reply.get("text", "")
            if MARKER not in text:
                raise AssertionError("UNEXPECTED_MODEL_RESPONSE")

            print(json.dumps({
                "event": "SITES_BFF_CHAT_ACCEPTANCE",
                "mode": "real-provider" if LIVE else "mock",
                "status": "PASS",
                "provider": reply.get("provider"),
                "model": reply.get("model"),
                "request_id": reply.get("request_id"),
            }), flush=True)
            print(
                "SITES_BFF_NEGATIVE_ROUTE_TESTS=PASS; "
                "SITES_BFF_CHAT_GATEWAY=PASS",
                flush=True,
            )
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
            if mock:
                mock.shutdown()


if __name__ == "__main__":
    main()
