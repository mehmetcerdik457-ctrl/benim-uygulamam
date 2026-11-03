"""Exercise Railway's *staged* offline pre-deploy condition on real backend source.

No keys, provider network calls, Railway changes, or production deployments.
All credentials below are test-only placeholders.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
# This is the Python expression inside Railway's existing staged preDeployCommand.
STAGED_CHECK = (
    "from backend import server as s;import sys;"
    "ok=(s.OPENAI_URL=='https://api.openai.com/v1/responses' "
    "and s.configured() and s.proxy_configured() "
    "and bool(s.ALLOWED_MODELS) and s.DEFAULT_MODEL in s.ALLOWED_MODELS "
    "and type(s.MAX_OUTPUT_TOKENS) is int and s.MAX_OUTPUT_TOKENS>0);"
    "print('OMEGA_PREDEPLOY_OFFLINE='+"
    "('PASS_CONFIG_ONLY_NO_MODEL_REQUEST' if ok else 'DENIED'));"
    "sys.exit(0 if ok else 2)"
)
TEST_ENV = {
    "OPENAI_API_KEY": "unit-test-only-not-a-real-key",
    "AI_BACKEND_PROXY_TOKEN": "unit-test-only-not-a-real-token",
    "OPENAI_MODEL": "gpt-5.6-luna",
    "OPENAI_ALLOWED_MODELS": "gpt-5.6-luna",
    "MAX_OUTPUT_TOKENS": "32",
}


def run_check(changes: dict[str, str | None] | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.update(TEST_ENV)
    for key, value in (changes or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return subprocess.run(
        [sys.executable, "-c", STAGED_CHECK],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )


class RailwayStagedPredeployTests(unittest.TestCase):
    def test_valid_configuration_passes_without_live_request(self):
        result = run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS_CONFIG_ONLY_NO_MODEL_REQUEST", result.stdout)
        self.assertNotIn("LIVE_PROVIDER_MODEL", result.stdout)

    def test_missing_provider_key_fails_closed(self):
        result = run_check({"OPENAI_API_KEY": None})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("DENIED", result.stdout)

    def test_missing_proxy_token_fails_closed(self):
        result = run_check({"AI_BACKEND_PROXY_TOKEN": None})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("DENIED", result.stdout)

    def test_disallowed_default_model_fails_closed(self):
        result = run_check({"OPENAI_MODEL": "model-not-on-allowlist"})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("DENIED", result.stdout)

    def test_empty_allowlist_fails_closed(self):
        result = run_check({"OPENAI_ALLOWED_MODELS": ""})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("DENIED", result.stdout)

    def test_zero_output_tokens_fails_closed(self):
        result = run_check({"MAX_OUTPUT_TOKENS": "0"})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("DENIED", result.stdout)

    def test_non_integer_token_limit_fails_closed(self):
        result = run_check({"MAX_OUTPUT_TOKENS": "wrong"})
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("PASS_CONFIG_ONLY_NO_MODEL_REQUEST", result.stdout)

    def test_existing_security_selftest_passes_with_placeholders(self):
        env = {**os.environ, **TEST_ENV}
        result = subprocess.run(
            [sys.executable, "scripts/security_selftest.py"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("BACKEND_SECURITY_SELFTEST=PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
