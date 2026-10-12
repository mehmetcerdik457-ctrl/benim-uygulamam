"""Safety tests: no real Docker or live database access in this module."""
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "omega_ops_isolated_restore.sh"


def probe(extra):
    # Run only the script's early guard; no production variables are inherited.
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
           "GITHUB_ACTIONS": "false",
           "RUNNER_ENVIRONMENT": "self-hosted",
           "GITHUB_REPOSITORY": "not-approved/repository",
           "GITHUB_RUN_ID": "42",
           "GITHUB_RUN_ATTEMPT": "1"}
    env.update(extra)
    return subprocess.run(["bash", str(SCRIPT)], env=env, text=True,
                          capture_output=True, timeout=5, check=False)


class OperationsIsolationTest(unittest.TestCase):
    def test_refuse_non_actions(self):
        p = probe({})
        self.assertEqual(p.returncode, 20)
        self.assertIn("BLOCKED_NON_EPHEMERAL_RUNNER", p.stdout)

    def test_refuse_self_hosted_even_with_correct_repo(self):
        p = probe({"GITHUB_ACTIONS": "true",
                   "GITHUB_REPOSITORY": "mehmetcerdik457-ctrl/benim-uygulamam"})
        self.assertEqual(p.returncode, 20)

    def test_refuse_fork_or_other_repository(self):
        p = probe({"GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted"})
        self.assertEqual(p.returncode, 20)

    def test_refuse_bad_run_id(self):
        p = probe({"GITHUB_ACTIONS": "true",
                   "RUNNER_ENVIRONMENT": "github-hosted",
                   "GITHUB_REPOSITORY": "mehmetcerdik457-ctrl/benim-uygulamam",
                   "GITHUB_RUN_ID": "suspicious"})
        self.assertEqual(p.returncode, 20)

    def test_refuse_missing_runtime_credential_before_docker(self):
        p = probe({"GITHUB_ACTIONS": "true",
                   "RUNNER_ENVIRONMENT": "github-hosted",
                   "GITHUB_REPOSITORY": "mehmetcerdik457-ctrl/benim-uygulamam",
                   "OMEGA_TEST_DB_SENTINEL": "a" * 32,
                   "OMEGA_DEV_DB_PASSWORD": "short"})
        self.assertEqual(p.returncode, 21)

    def test_refuse_unset_password_without_shell_error(self):
        p = probe({"GITHUB_ACTIONS": "true",
                   "RUNNER_ENVIRONMENT": "github-hosted",
                   "GITHUB_REPOSITORY": "mehmetcerdik457-ctrl/benim-uygulamam",
                   "OMEGA_TEST_DB_SENTINEL": "b" * 32})
        self.assertEqual(p.returncode, 21)
        self.assertIn("BLOCKED_MISSING_TEMP_CREDENTIALS", p.stdout)
        self.assertNotIn("unbound variable", p.stderr)

    def test_refuse_empty_sentinel(self):
        p = probe({"GITHUB_ACTIONS": "true",
                   "RUNNER_ENVIRONMENT": "github-hosted",
                   "GITHUB_REPOSITORY": "mehmetcerdik457-ctrl/benim-uygulamam",
                   "OMEGA_TEST_DB_SENTINEL": "",
                   "OMEGA_DEV_DB_PASSWORD": "x" * 26})
        self.assertEqual(p.returncode, 21)

    def test_restoration_remains_fixture_only(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("public.omega_ops_fixture", source)
        self.assertIn("omega_ops_restore", source)
        self.assertIn("OMEGA_TEST_DB_SENTINEL", source)
        self.assertIn("--no-owner", source)
        self.assertIn("OMEGA_OPS_INVALID_ARCHIVE_REJECTION=PASS", source)
        self.assertIn("BLOCKED_PROJECT_ALREADY_EXISTS", source)
        self.assertNotIn("docker volume rm", source)
        self.assertNotIn("pg_restore --clean", source)
        self.assertNotIn("docker system prune", source)


if __name__ == "__main__":
    unittest.main()
