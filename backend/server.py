#!/usr/bin/env python3
"""MEHMET AI backend P1.

Public browser traffic should reach this service through the PWA runtime proxy.
Provider secrets stay server-side in environment variables.
"""
from __future__ import annotations

import json
import hmac
import os
import time
import uuid
import urllib.error
import urllib.request
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

VERSION = "0.1.0"
OPENAI_URL = "https://api.openai.com/v1/responses"
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


def configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def proxy_configured() -> bool:
    return bool(os.getenv("AI_BACKEND_PROXY_TOKEN", "").strip())


def proxy_authorized(headers: Any) -> bool:
    expected = os.getenv("AI_BACKEND_PROXY_TOKEN", "").strip()
    if not expected:
        return False
    provided = (headers.get("X-MEH-Proxy-Token") or "").strip()
    return bool(provided) and hmac.compare_digest(provided, expected)


def json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def client_key(headers: Any, peer_ip: str) -> str:
    forwarded = (headers.get("X-Forwarded-For") or "").split(",", 1)[0].strip()
    return forwarded or peer_ip


def rate_allowed(key: str, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    bucket = _rate_buckets[key]
    cutoff = now - 60.0
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
    if not attachments:
        return message
    safe = []
    for item in attachments[:20]:
        if not isinstance(item, dict):
            continue
        safe.append(
            {
                "name": str(item.get("name", ""))[:256],
                "type": str(item.get("type", ""))[:128],
                "size": item.get("size"),
                "sha256": str(item.get("sha256", ""))[:128],
                "source": str(item.get("source", ""))[:64],
            }
        )
    if not safe:
        return message
    return (
        message
        + "\n\n[Attachment metadata only; file contents are not present]\n"
        + json.dumps(safe, ensure_ascii=False, separators=(",", ":"))
    )


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
    return text, model


class Handler(BaseHTTPRequestHandler):
    server_version = "MEHMET-AI-Backend/" + VERSION

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
        except json.JSONDecodeError as exc:
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
                    "proxy_auth_configured": proxy_configured(),
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
            self._send(
                200,
                {
                    "default": DEFAULT_MODEL,
                    "allowed": list(ALLOWED_MODELS),
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

        if not proxy_configured():
            self._send(
                503,
                {
                    "error": "PROXY_AUTH_NOT_CONFIGURED",
                    "message": "Private runtime-to-backend authentication is not configured.",
                    "request_id": request_id,
                },
                request_id,
            )
            return

        if not proxy_authorized(self.headers):
            self._send(
                401,
                {
                    "error": "UNAUTHORIZED_PROXY",
                    "message": "Private runtime authentication failed.",
                    "request_id": request_id,
                },
                request_id,
            )
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
            self._send(400, {"error": str(exc), "request_id": request_id}, request_id)
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

        attachments = body.get("attachments") or []
        if not isinstance(attachments, list):
            self._send(400, {"error": "ATTACHMENTS_MUST_BE_ARRAY", "request_id": request_id}, request_id)
            return

        try:
            reply, model = call_openai(message, attachments)
        except urllib.error.HTTPError as exc:
            # Log only a bounded provider error code; never keys or raw response bodies.
            try:
                provider_error = json.loads(exc.read(16384)).get("error", {})
                provider_code = provider_error.get("code") if isinstance(provider_error, dict) else None
                safe_codes = {"insufficient_quota", "invalid_api_key", "model_not_found",
                              "permission_denied", "unsupported_country_region_territory",
                              "organization_restricted", "access_terminated", "project_not_found",
                              "invalid_request_error", "model_not_available", "rate_limit_exceeded", "billing_hard_limit_reached"}
                provider_type = provider_error.get("type") if isinstance(provider_error, dict) else None
                provider_code = provider_code if provider_code in safe_codes else (provider_type if provider_type in safe_codes else "UNCLASSIFIED_PROVIDER_ERROR")
            except (ValueError, AttributeError):
                provider_code = "UNCLASSIFIED_PROVIDER_ERROR"
            print(f"UPSTREAM_HTTP_ERROR request_id={request_id} status={exc.code} provider_code={provider_code}", flush=True)
            self._send(
                502,
                {
                    "error": "UPSTREAM_PROVIDER_ERROR",
                    "upstream_status": exc.code,
                    "upstream_code": provider_code,
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
            code = str(exc)
            print(f"CHAT_ERROR request_id={request_id} code={code}", flush=True)
            self._send(502, {"error": code, "request_id": request_id}, request_id)
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

    def log_message(self, fmt: str, *args: Any) -> None:
        print("HTTP " + (fmt % args), flush=True)


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
