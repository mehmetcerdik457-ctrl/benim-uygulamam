#!/usr/bin/env python3
"""MEHMET AI backend P1.

Public browser traffic should reach this service through the PWA runtime proxy.
Provider secrets stay server-side in environment variables.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
import urllib.error
import urllib.request
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

VERSION = "0.1.0"
OPENAI_URL = "https://api.openai.com/v1/responses"
OPENAI_MODELS_URL = "https://api.openai.com/v1/models"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna").strip()
ALLOWED_MODELS = tuple(
    x.strip()
    for x in os.getenv(
        "OPENAI_ALLOWED_MODELS",
        "gpt-5.6-luna,gpt-5.6-terra,gpt-5.6-sol",
    ).split(",")
    if x.strip()
)
MAX_BODY_BYTES = int(os.getenv("MAX_BODY_BYTES", "65536"))
MAX_MESSAGE_CHARS = int(os.getenv("MAX_MESSAGE_CHARS", "32000"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "2048"))
UPSTREAM_TIMEOUT_SECONDS = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "45"))
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))

_rate_buckets: dict[str, deque[float]] = defaultdict(deque)
_rate_lock = threading.Lock()
MAX_RATE_BUCKETS = 4096
REQUEST_READ_TIMEOUT_SECONDS = 5.0
_SECRET_PATTERN = re.compile(r"(?i)(?:sk-[a-z0-9_-]{16,}|gh[pousr]_[a-z0-9]{20,}|AIza[a-z0-9_-]{30,})")
_REDACTED = "[GIZLI_DEGER_MASKELENDI]"


def redact_sensitive_text(value: str) -> str:
    """Mask configured credentials and recognized token forms before model/log output."""
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if len(key) >= 8:
        value = value.replace(key, _REDACTED)
    return _SECRET_PATTERN.sub(_REDACTED, value)


def configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def client_key(headers: Any, peer_ip: str) -> str:
    # This local service has no configured trusted reverse proxy. Client-supplied
    # forwarding headers cannot establish identity or bypass rate limits.
    return peer_ip


def rate_allowed(key: str, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    with _rate_lock:
        cutoff = now - 60.0
        if key not in _rate_buckets and len(_rate_buckets) >= MAX_RATE_BUCKETS:
            stale = [name for name, items in _rate_buckets.items() if not items or items[-1] < cutoff]
            for name in stale:
                del _rate_buckets[name]
            if len(_rate_buckets) >= MAX_RATE_BUCKETS:
                return False
        bucket = _rate_buckets[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT_PER_MINUTE:
            return False
        bucket.append(now)
        return True


def extract_response_text(data: dict[str, Any]) -> str:
    direct = data.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    chunks: list[str] = []
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if not isinstance(content, dict):
                continue
            if content.get("type") in {"output_text", "text"}:
                value = content.get("text")
                if isinstance(value, str) and value.strip():
                    chunks.append(value.strip())
    return "\n".join(chunks).strip()


def build_input(message: str, attachments: list[dict[str, Any]]) -> str:
    message = redact_sensitive_text(message)
    if not attachments:
        return message
    safe = []
    for item in attachments[:20]:
        if not isinstance(item, dict):
            continue
        safe.append(
            {
                "name": redact_sensitive_text(str(item.get("name", "")))[:256],
                "type": redact_sensitive_text(str(item.get("type", "")))[:128],
                "size": item.get("size") if type(item.get("size")) is int and item["size"] >= 0 else None,
                "sha256": redact_sensitive_text(str(item.get("sha256", "")))[:128],
                "source": redact_sensitive_text(str(item.get("source", "")))[:64],
            }
        )
    if not safe:
        return message
    return (
        message
        + "\n\n[Attachment metadata only; file contents are not present]\n"
        + json.dumps(safe, ensure_ascii=False, separators=(",", ":"))
    )



def fetch_openai_model_ids() -> set[str]:
    """Fetch the account-visible model IDs from OpenAI; never expose provider response bodies."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("PROVIDER_NOT_CONFIGURED")

    req = urllib.request.Request(
        OPENAI_MODELS_URL,
        method="GET",
        headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": f"mehmet-ai-backend/{VERSION}",
        },
    )
    with urllib.request.urlopen(req, timeout=min(UPSTREAM_TIMEOUT_SECONDS, 10.0)) as response:
        payload = json.loads(response.read())

    rows = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise ValueError("INVALID_MODEL_LIST_RESPONSE")
    return {
        row["id"]
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("id"), str) and row["id"]
    }


def call_openai(message: str, attachments: list[dict[str, Any]]) -> tuple[str, str]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("PROVIDER_NOT_CONFIGURED")

    model = DEFAULT_MODEL if DEFAULT_MODEL in ALLOWED_MODELS else ALLOWED_MODELS[0]
    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": build_input(message, attachments),
                    }
                ],
            }
        ],
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "store": False,
    }
    req = urllib.request.Request(
        OPENAI_URL,
        data=json_bytes(payload),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": f"mehmet-ai-backend/{VERSION}",
        },
    )
    with urllib.request.urlopen(req, timeout=UPSTREAM_TIMEOUT_SECONDS) as response:
        raw = response.read()
    data = json.loads(raw)
    text = extract_response_text(data)
    if not text:
        raise RuntimeError("EMPTY_PROVIDER_RESPONSE")
    return redact_sensitive_text(text), model


class Handler(BaseHTTPRequestHandler):
    server_version = "MEHMET-AI-Backend/" + VERSION

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(REQUEST_READ_TIMEOUT_SECONDS)

    def _send(self, status: int, payload: dict[str, Any], request_id: str | None = None) -> None:
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if request_id:
            self.send_header("X-Request-ID", request_id)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        raw_len = self.headers.get("Content-Length")
        try:
            length = int(raw_len or "0")
        except ValueError as exc:
            raise ValueError("INVALID_CONTENT_LENGTH") from exc
        if length <= 0:
            raise ValueError("EMPTY_BODY")
        if length > MAX_BODY_BYTES:
            raise OverflowError("BODY_TOO_LARGE")
        raw = self.rfile.read(length)
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, RecursionError) as exc:
            raise ValueError("INVALID_JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("JSON_OBJECT_REQUIRED")
        return value

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/api/health":
            self._send(
                200,
                {
                    "status": "PASS",
                    "version": VERSION,
                    "provider_configured": configured(),
                    "default_model": DEFAULT_MODEL,
                },
            )
            return

        if path == "/api/providers":
            self._send(
                200,
                {
                    "providers": [
                        {
                            "id": "openai",
                            "label": "OpenAI",
                            "model": DEFAULT_MODEL,
                            "configured": configured(),
                        }
                    ],
                    "research_configured": False,
                },
            )
            return

        if path == "/api/models":
            if not configured():
                self._send(503, {"error": "PROVIDER_NOT_CONFIGURED"})
                return
            try:
                live_ids = fetch_openai_model_ids()
            except urllib.error.HTTPError as exc:
                self._send(502, {"error": "MODEL_LIST_UPSTREAM_ERROR", "upstream_status": exc.code})
                return
            except (urllib.error.URLError, TimeoutError):
                self._send(504, {"error": "MODEL_LIST_TIMEOUT"})
                return
            except Exception:
                # Provider exceptions can contain credentials. Do not let the
                # server's default exception traceback reach container logs.
                self._send(502, {"error": "MODEL_LIST_UNAVAILABLE"})
                return

            allowed_live = sorted(set(ALLOWED_MODELS) & live_ids)
            self._send(
                200,
                {
                    "default": DEFAULT_MODEL if DEFAULT_MODEL in allowed_live else None,
                    "allowed": allowed_live,
                    "unavailable_allowed": sorted(set(ALLOWED_MODELS) - live_ids),
                },
            )
            return

        if path == "/api/vault/status":
            self._send(
                200,
                {
                    "status": "PASS",
                    "backend": "railway-env",
                    "configured_secret_count": 1 if configured() else 0,
                },
            )
            return

        if path == "/api/owner/status":
            self._send(
                200,
                {
                    "owner": {
                        "OWNER_ID": "UNPROVISIONED",
                        "AUTH_LEVEL": "UNPROVISIONED",
                        "AUTH_METHOD": "UNPROVISIONED",
                    },
                    "runtime": "P1_BACKEND_ONLY",
                },
            )
            return

        self._send(404, {"error": "NOT_FOUND"})

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        request_id = str(uuid.uuid4())

        if path == "/api/research":
            self._send(
                501,
                {
                    "error": "RESEARCH_PROVIDER_UNCONFIGURED",
                    "message": "Research provider is not configured yet.",
                    "request_id": request_id,
                },
                request_id,
            )
            return

        if path != "/api/chat":
            self._send(404, {"error": "NOT_FOUND", "request_id": request_id}, request_id)
            return

        key = client_key(self.headers, self.client_address[0])
        if not rate_allowed(key):
            self._send(
                429,
                {
                    "error": "RATE_LIMITED",
                    "message": "Too many requests.",
                    "request_id": request_id,
                },
                request_id,
            )
            return

        try:
            body = self._read_json()
        except OverflowError:
            self._send(413, {"error": "BODY_TOO_LARGE", "request_id": request_id}, request_id)
            return
        except ValueError as exc:
            allowed = {"INVALID_CONTENT_LENGTH", "EMPTY_BODY", "INVALID_JSON", "JSON_OBJECT_REQUIRED"}
            error = str(exc) if str(exc) in allowed else "INVALID_JSON"
            self._send(400, {"error": error, "request_id": request_id}, request_id)
            return
        except TimeoutError:
            self._send(408, {"error": "REQUEST_TIMEOUT", "request_id": request_id}, request_id)
            return

        provider = body.get("provider")
        if provider not in (None, "", "openai"):
            self._send(
                409,
                {
                    "error": "PROVIDER_NOT_CONFIGURED",
                    "message": "Requested provider is not configured.",
                    "request_id": request_id,
                },
                request_id,
            )
            return

        if not configured():
            self._send(
                503,
                {
                    "error": "PROVIDER_NOT_CONFIGURED",
                    "message": "OpenAI provider is not configured.",
                    "request_id": request_id,
                },
                request_id,
            )
            return

        message = body.get("message")
        if not isinstance(message, str) or not message.strip():
            self._send(400, {"error": "MESSAGE_REQUIRED", "request_id": request_id}, request_id)
            return
        message = message.strip()
        if len(message) > MAX_MESSAGE_CHARS:
            self._send(413, {"error": "MESSAGE_TOO_LARGE", "request_id": request_id}, request_id)
            return

        attachments = body.get("attachments", [])
        if attachments is None:
            attachments = []
        if not isinstance(attachments, list):
            self._send(400, {"error": "ATTACHMENTS_MUST_BE_ARRAY", "request_id": request_id}, request_id)
            return

        try:
            reply, model = call_openai(message, attachments)
        except urllib.error.HTTPError as exc:
            print(f"UPSTREAM_HTTP_ERROR request_id={request_id} status={exc.code}", flush=True)
            self._send(
                502,
                {
                    "error": "UPSTREAM_PROVIDER_ERROR",
                    "upstream_status": exc.code,
                    "request_id": request_id,
                },
                request_id,
            )
            return
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"UPSTREAM_NETWORK_ERROR request_id={request_id} type={type(exc).__name__}", flush=True)
            self._send(504, {"error": "UPSTREAM_TIMEOUT", "request_id": request_id}, request_id)
            return
        except Exception as exc:
            # Never reflect arbitrary provider/runtime exception text to clients or logs:
            # exception strings can contain credentials or upstream response fragments.
            error_type = type(exc).__name__
            print(f"CHAT_ERROR request_id={request_id} type={error_type}", flush=True)
            self._send(
                502,
                {"error": "UPSTREAM_PROVIDER_ERROR", "request_id": request_id},
                request_id,
            )
            return

        self._send(
            200,
            {
                "text": reply,
                "provider": "openai",
                "model": model,
                "request_id": request_id,
            },
            request_id,
        )

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        routes = {"/api/health", "/api/models", "/api/providers", "/api/vault/status", "/api/owner/status", "/api/chat", "/api/research"}
        path = getattr(self, "path", "").split("?", 1)[0]
        route = path if path in routes else "UNKNOWN_ROUTE"
        method = getattr(self, "command", "")
        method = method if method in {"GET", "POST", "HEAD", "OPTIONS", "PUT", "DELETE", "PATCH"} else "UNKNOWN_METHOD"
        status = int(code) if str(code).isdigit() else None
        print(json.dumps({"event": "http", "method": method, "route": route, "status": status}), flush=True)

    def log_message(self, fmt: str, *args: Any) -> None:
        # BaseHTTPRequestHandler also calls this for malformed request lines.
        # Neither formatting arguments nor arbitrary client paths are safe logs.
        print('{"event":"http_protocol_error"}', flush=True)


def main() -> None:
    port = int(os.getenv("PORT", "8080"))
    print(
        json.dumps(
            {
                "event": "backend_start",
                "version": VERSION,
                "port": port,
                "provider_configured": configured(),
                "model": DEFAULT_MODEL,
            },
            separators=(",", ":"),
        ),
        flush=True,
    )
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
