import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import server


def parse_env_file(path: Path) -> dict[str, str]:
    env_vars = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip()
    return env_vars


def test_env_example_has_no_secret_values():
    env_example = parse_env_file(ROOT / ".env.example")
    secret_keys = [
        "OPENAI_API_KEY",
        "SENTRY_DSN",
        "PYPI_API_TOKEN",
        "NPM_TOKEN",
        "DOCKERHUB_USERNAME",
        "DOCKERHUB_PASSWORD",
        "ANDROID_KEYSTORE_BASE64",
        "ANDROID_KEY_ALIAS",
        "ANDROID_KEY_PASSWORD",
        "ANDROID_STORE_PASSWORD",
    ]
    for key in secret_keys:
        assert key in env_example, f"Expected key {key} in .env.example"
        assert env_example[key] == "", f"Expected key {key} to have an empty placeholder value in .env.example"


def test_backend_defaults_align_with_env_example():
    env_example = parse_env_file(ROOT / ".env.example")
    assert server.DEFAULT_MODEL == env_example["OPENAI_MODEL"]
    expected_allowed = tuple(
        x.strip() for x in env_example["OPENAI_ALLOWED_MODELS"].split(",") if x.strip()
    )
    assert server.ALLOWED_MODELS == expected_allowed
    assert server.MAX_BODY_BYTES == int(env_example["MAX_BODY_BYTES"])
    assert server.MAX_MESSAGE_CHARS == int(env_example["MAX_MESSAGE_CHARS"])
    assert server.MAX_OUTPUT_TOKENS == int(env_example["MAX_OUTPUT_TOKENS"])
    assert server.UPSTREAM_TIMEOUT_SECONDS == float(env_example["UPSTREAM_TIMEOUT_SECONDS"])
    assert server.RATE_LIMIT_PER_MINUTE == int(env_example["RATE_LIMIT_PER_MINUTE"])


def test_scope_policy_invariants():
    scope_path = ROOT / "scope.yaml"
    assert scope_path.is_file(), "scope.yaml must exist"
    content = scope_path.read_text(encoding="utf-8")
    expected_lines = [
        "default_mode: read_only",
        "default_execution_mode: dry_run",
        "secret_values_may_enter_llm_context: false",
        "secret_values_may_enter_git_or_rag: false",
        "destructive_or_external_actions_require_human_approval: true",
        "model_output_grants_authority: false",
        "unknown_permissions_are_denied: true",
    ]
    for expected in expected_lines:
        assert expected in content, f"scope.yaml missing expected policy invariant: '{expected}'"


def test_governance_files_exist_and_non_empty():
    required_files = [
        ROOT / "README.md",
        ROOT / "SECURITY.md",
        ROOT / "AI_MASTER_ROADMAP.md",
        ROOT / "CURRENT_STATE.md",
        ROOT / "scope.yaml",
        ROOT / "requirements.txt",
        ROOT / "start.sh",
        ROOT / "docs" / "PROJECT_OMEGA_PHASE_0.md",
        ROOT / "docs" / "EXECUTION_STATUS.md",
        ROOT / "docs" / "adr" / "0001-mvi-technology-boundaries.md",
    ]
    for file_path in required_files:
        assert file_path.is_file(), f"Required file missing: {file_path.relative_to(ROOT)}"
        assert file_path.stat().st_size > 0, f"File must not be empty: {file_path.relative_to(ROOT)}"


def test_openai_integration_is_explicit():
    assert server.OPENAI_URL.startswith("https://api.openai.com/"), "OPENAI_URL must explicitly target OpenAI API"
    assert "local" not in server.OPENAI_URL.lower(), "External OpenAI endpoint must not masquerade as a local provider"


def test_requirements_strictly_stdlib():
    req_path = ROOT / "requirements.txt"
    assert req_path.is_file(), "requirements.txt must exist"
    lines = [
        line.strip()
        for line in req_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert len(lines) == 0, f"Runtime requirements.txt must remain stdlib-only, found: {lines}"
