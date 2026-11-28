"""Deterministic repository contract tests validating documented baseline against implementation."""
import ast
import json
import re
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import server


def test_backend_stdlib_only():
    """Verify backend/server.py imports only from the Python standard library."""
    server_path = ROOT / "backend" / "server.py"
    assert server_path.exists(), "backend/server.py must exist"

    tree = ast.parse(server_path.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.add(node.module.split(".")[0])

    stdlib = set(sys.stdlib_module_names) | set(sys.builtin_module_names)
    non_stdlib = {m for m in imported_modules if m not in stdlib}
    assert not non_stdlib, f"backend/server.py imported non-stdlib modules: {non_stdlib}"


def test_backend_documented_constants():
    """Verify documented default configurations in backend/server.py."""
    assert isinstance(server.VERSION, str) and server.VERSION
    assert server.OPENAI_URL == "https://api.openai.com/v1/responses"
    assert server.DEFAULT_MODEL in server.ALLOWED_MODELS
    assert "gpt-5.6-luna" in server.ALLOWED_MODELS
    assert server.MAX_BODY_BYTES > 0
    assert server.MAX_MESSAGE_CHARS > 0
    assert server.MAX_OUTPUT_TOKENS > 0
    assert server.UPSTREAM_TIMEOUT_SECONDS > 0
    assert server.RATE_LIMIT_PER_MINUTE > 0


def test_scope_and_policy_baseline():
    """Verify scope.yaml defines read-only/dry-run defaults and strict secret policy."""
    scope_path = ROOT / "scope.yaml"
    assert scope_path.exists(), "scope.yaml must exist"
    content = scope_path.read_text(encoding="utf-8")

    assert "default_mode: read_only" in content
    assert "default_execution_mode: dry_run" in content
    assert "secret_values_may_enter_llm_context: false" in content
    assert "secret_values_may_enter_git_or_rag: false" in content
    assert "destructive_or_external_actions_require_human_approval: true" in content


def test_env_example_has_no_live_secrets():
    """Verify .env.example contains only non-secret placeholders."""
    env_example = ROOT / ".env.example"
    assert env_example.exists(), ".env.example must exist"
    content = env_example.read_text(encoding="utf-8")

    secret_pattern = re.compile(
        r"(sk-proj-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"
    )
    assert not secret_pattern.search(content), "Found live secret pattern in .env.example"
    assert "OPENAI_API_KEY=" in content


def test_documented_endpoints_contract(monkeypatch):
    """Verify all documented HTTP endpoints respond according to contract."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    server._rate_buckets.clear()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    try:
        # GET /api/health
        with urllib.request.urlopen(f"{base_url}/api/health") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data.get("status") == "PASS"
            assert data.get("version") == server.VERSION
            assert data.get("provider_configured") is False
            assert data.get("default_model") == server.DEFAULT_MODEL

        # GET /api/providers
        with urllib.request.urlopen(f"{base_url}/api/providers") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "providers" in data
            assert data.get("research_configured") is False

        # GET /api/models
        with urllib.request.urlopen(f"{base_url}/api/models") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data.get("default") == server.DEFAULT_MODEL
            assert isinstance(data.get("allowed"), list)

        # GET /api/vault/status
        with urllib.request.urlopen(f"{base_url}/api/vault/status") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data.get("status") == "PASS"

        # GET /api/owner/status
        with urllib.request.urlopen(f"{base_url}/api/owner/status") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data.get("runtime") == "P1_BACKEND_ONLY"
            assert data.get("owner", {}).get("OWNER_ID") == "UNPROVISIONED"

        # POST /api/research - fail closed with 501
        research_req = urllib.request.Request(
            f"{base_url}/api/research",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(research_req)
            assert False, "POST /api/research should have failed with 501"
        except urllib.error.HTTPError as exc:
            assert exc.code == 501
            err_data = json.loads(exc.read().decode("utf-8"))
            assert err_data.get("error") == "RESEARCH_PROVIDER_UNCONFIGURED"

        # POST /api/chat - unconfigured provider fails closed with 503
        chat_req = urllib.request.Request(
            f"{base_url}/api/chat",
            data=json.dumps({"message": "test"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(chat_req)
            assert False, "POST /api/chat should have failed with 503 without API key"
        except urllib.error.HTTPError as exc:
            assert exc.code == 503
            err_data = json.loads(exc.read().decode("utf-8"))
            assert err_data.get("error") == "PROVIDER_NOT_CONFIGURED"

        # GET /api/unknown -> 404
        try:
            urllib.request.urlopen(f"{base_url}/api/unknown")
            assert False, "Unknown GET should return 404"
        except urllib.error.HTTPError as exc:
            assert exc.code == 404

    finally:
        httpd.shutdown()
        httpd.server_close()
