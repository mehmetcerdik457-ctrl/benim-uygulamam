#!/usr/bin/env python3
"""MEHMET AI backend P2 model router.

Public browser traffic should reach this service through the PWA runtime proxy.
Provider secrets stay server-side in environment variables.

Router goals:
- keep OpenAI as the primary high-capability provider;
- support explicit max/balanced/fast OpenAI profiles;
- support Hugging Face Inference Providers for open-source models;
- fail closed when a provider credential is absent;
- never expose provider credentials to the browser.
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

VERSION = "0.2.0"

OPENAI_URL = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/responses").strip()
HF_CHAT_URL = os.getenv(
    "HF_CHAT_URL",
    "https://router.huggingface.co/v1/chat/completions",
).strip()

DEFAULT_PROVIDER = os.getenv("AI_DEFAULT_PROVIDER", "openai").strip().lower() or "openai"
DEFAULT_PROFILE = os.getenv("AI_DEFAULT_PROFILE", "max").strip().lower() or "max"

OPENAI_PROFILE_MODELS = {
    "max": os.getenv("OPENAI_MODEL_MAX", "gpt-6-astra").strip(),
    "balanced": os.getenv("OPENAI_MODEL_BALANCED", "gpt-6-sol").strip(),
    "fast": os.getenv("OPENAI_MODEL_FAST", "gpt-6-luna").strip(),
}
OPENAI_ALLOWED_MODELS = tuple(
    x.strip()
    for x in os.getenv(
        "OPENAI_ALLOWED_MODELS",
        "gpt-6-astra,gpt-6-sol,gpt-6-luna,gpt-5.6-sol,gpt-5.6-terra,gpt-5.6-luna",
    ).split(",")
    if x.strip()
)

HF_PROFILE_MODELS = {
    "max": os.getenv("HF_MODEL_MAX", "deepseek-ai/DeepSeek-R1:preferred").strip(),
    "balanced": os.getenv("HF_MODEL_BALANCED", "openai/gpt-oss-20b:preferred").strip(),
    "fast": os.getenv("HF_MODEL_FAST", "Qwen/Qwen3-8B:preferred").strip(),
}
HF_ALLOWED_MODELS = tuple(
    x.strip()
    for x in os.getenv(
        "HF_ALLOWED_MODELS",
        "deepseek-ai/DeepSeek-R1:preferred,openai/gpt-oss-20b:preferred,Qwen/Qwen3-8B:preferred",
    ).split(",")
    if x.strip()
)

MAX_BODY_BYTES = int(os.getenv("MAX_BODY_BYTES", "65536"))
MAX_MESSAGE_CHARS = int(os.getenv("MAX_MESSAGE_CHARS", "32000"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "2048"))
UPSTREAM_TIMEOUT_SECONDS = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "45"))
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))

_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


def openai_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def huggingface_configured() -> bool:
    return bool(os.getenv("HF_TOKEN", "").strip())


def provider_configured(provider: str) -> bool:
    provider = provider.strip().lower()
    if provider == "openai":
        return openai_configured()
    if provider in {"huggingface", "hf"}:
        return huggingface_configured()
    return False


def configured() -> bool:
    """Compatibility helper retained for existing tests/health checks."""
    return provider_configured(DEFAULT_PROVIDER)


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

    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()

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


def normalize_provider(value: Any) -> str:
    provider = str(value or DEFAULT_PROVIDER).strip().lower()
    if provider == "hf":
        provider = "huggingface"
    if provider not in {"openai", "huggingface"}:
        raise ValueError("PROVIDER_NOT_ALLOWED")
    return provider


def normalize_profile(value: Any) -> str:
    profile = str(value or DEFAULT_PROFILE).strip().lower()
    if profile not in {"max", "balanced", "fast"}:
        raise ValueError("PROFILE_NOT_ALLOWED")
    return profile


def select_model(provider: str, requested_model: Any = None, profile: Any = None) -> str:
    provider = normalize_provider(provider)
    profile_name = normalize_profile(profile)

    if provider == "openai":
        allowed = OPENAI_ALLOWED_MODELS
        default_model = OPENAI_PROFILE_MODELS[profile_name]
    else:
        allowed = HF_ALLOWED_MODELS
        default_model = HF_PROFILE_MODELS[profile_name]

    requested = str(requested_model or "").strip()
    model = requested or default_model
    if model not in allowed:
        raise ValueError("MODEL_NOT_ALLOWED")
    return model


def call_openai(message: str, attachments: list[dict[str, Any]], model: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("PROVIDER_NOT_CONFIGURED")

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
    return text


def call_huggingface(message: str, attachments: list[dict[str, Any]], model: str) -> str:
    token = os.getenv("HF_TOKEN", "").strip()
    if not token:
        raise RuntimeError("PROVIDER_NOT_CONFIGURED")

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": build_input(message, attachments),
            }
        ],
        "max_tokens": MAX_OUTPUT_TOKENS,
    }
    req = urllib.request.Request(
        HF_CHAT_URL,
        data=json_bytes(payload),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
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
    return text


def call_provider(
    provider: str,
    message: str,
    attachments: list[dict[str, Any]],
    model: str,
) -> str:
    if provider == "openai":
        return call_openai(message, attachments, model)
    if provider == "huggingface":
        return call_huggingface(message, attachments, model)
    raise ValueError("PROVIDER_NOT_ALLOWED")


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
                    "providers_configured": {
                        "openai": openai_configured(),
                        "huggingface": huggingface_configured(),
                    },
                    "proxy_auth_configured": proxy_configured(),
                    "default_provider": DEFAULT_PROVIDER,
                    "default_profile": DEFAULT_PROFILE,
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
                            "configured": openai_configured(),
                            "profiles": OPENAI_PROFILE_MODELS,
                        },
                        {
                            "id": "huggingface",
                            "label": "Hugging Face / Open Source",
                            "configured": huggingface_configured(),
                            "profiles": HF_PROFILE_MODELS,
                        },
                    ],
                    "default_provider": DEFAULT_PROVIDER,
                    "default_profile": DEFAULT_PROFILE,
                    "research_configured": False,
                },
            )
            return

        if path == "/api/models":
            self._send(
                200,
                {
                    "default_provider": DEFAULT_PROVIDER,
                    "default_profile": DEFAULT_PROFILE,
                    "openai": {
                        "profiles": OPENAI_PROFILE_MODELS,
                        "allowed": list(OPENAI_ALLOWED_MODELS),
                    },
                    "huggingface": {
                        "profiles": HF_PROFILE_MODELS,
                        "allowed": list(HF_ALLOWED_MODELS),
                    },
                },
            )
            return

        if path == "/api/vault/status":
            secret_count = sum(
                1
                for name in ("OPENAI_API_KEY", "HF_TOKEN", "AI_BACKEND_PROXY_TOKEN")
                if os.getenv(name, "").strip()
            )
            self._send(
                200,
                {
                    "status": "PASS",
                    "backend": "railway-env",
                    "configured_secret_count": secret_count,
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
                    "runtime": "P2_MODEL_ROUTER",
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

        try:
            provider = normalize_provider(body.get("provider"))
            profile = normalize_profile(body.get("profile"))
            model = select_model(provider, body.get("model"), profile)
        except ValueError as exc:
            self._send(409, {"error": str(exc), "request_id": request_id}, request_id)
            return

        if not provider_configured(provider):
            self._send(
                503,
                {
                    "error": "PROVIDER_NOT_CONFIGURED",
                    "provider": provider,
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
            reply = call_provider(provider, message, attachments, model)
        except urllib.error.HTTPError as exc:
            print(
                f"UPSTREAM_HTTP_ERROR request_id={request_id} provider={provider} status={exc.code}",
                flush=True,
            )
            self._send(
                502,
                {
                    "error": "UPSTREAM_PROVIDER_ERROR",
                    "provider": provider,
                    "upstream_status": exc.code,
                    "request_id": request_id,
                },
                request_id,
            )
            return
        except (urllib.error.URLError, TimeoutError) as exc:
            print(
                f"UPSTREAM_NETWORK_ERROR request_id={request_id} provider={provider} type={type(exc).__name__}",
                flush=True,
            )
            self._send(
                504,
                {
                    "error": "UPSTREAM_TIMEOUT",
                    "provider": provider,
                    "request_id": request_id,
                },
                request_id,
            )
            return
        except Exception as exc:
            code = str(exc)
            print(
                f"CHAT_ERROR request_id={request_id} provider={provider} code={code}",
                flush=True,
            )
            self._send(
                502,
                {
                    "error": code,
                    "provider": provider,
                    "request_id": request_id,
                },
                request_id,
            )
            return

        self._send(
            200,
            {
                "text": reply,
                "provider": provider,
                "profile": profile,
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
                "default_provider": DEFAULT_PROVIDER,
                "default_profile": DEFAULT_PROFILE,
                "providers_configured": {
                    "openai": openai_configured(),
                    "huggingface": huggingface_configured(),
                },
            },
            separators=(",", ":"),
        ),
        flush=True,
    )
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
