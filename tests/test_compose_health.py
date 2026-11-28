import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "tests" / "compose" / "health.yaml"


def _compose(project: str, host_port: int, *args: str) -> str:
    env = os.environ.copy()
    env["HEALTH_TEST_PORT"] = str(host_port)
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(COMPOSE_FILE),
            "-p",
            project,
            *args,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
    )
    return result.stdout.strip()


def _get_json(url: str) -> tuple[int, dict]:
    with urllib.request.urlopen(url, timeout=3) as response:
        return response.status, json.load(response)


def test_health_and_legacy_contract_on_loopback_compose():
    project = f"health-contract-{uuid.uuid4().hex[:12]}"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        host_port = sock.getsockname()[1]
    try:
        _compose(project, host_port, "up", "--detach")

        container_id = _compose(project, host_port, "ps", "-q", "backend")
        bindings = json.loads(
            subprocess.run(
                [
                    "docker",
                    "inspect",
                    container_id,
                    "--format",
                    "{{json .HostConfig.PortBindings}}",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout
        )
        assert bindings["8080/tcp"] == [
            {"HostIp": "127.0.0.1", "HostPort": str(host_port)}
        ]

        internal = subprocess.run(
            [
                "docker",
                "network",
                "inspect",
                f"{project}_isolated",
                "--format",
                "{{.Internal}}",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
        assert internal == "true"

        health_url = f"http://127.0.0.1:{host_port}/api/health"
        deadline = time.monotonic() + 30
        last_error = None
        while time.monotonic() < deadline:
            try:
                health_status, health = _get_json(health_url)
                break
            except (urllib.error.URLError, TimeoutError) as error:
                last_error = error
                time.sleep(1)
        else:
            raise AssertionError("Compose backend did not become reachable") from last_error

        assert health_status == 200
        assert health == {
            "status": "PASS",
            "version": "0.1.0",
            "provider_configured": False,
            "default_model": "gpt-5.6-luna",
        }

        status, providers = _get_json(
            f"http://127.0.0.1:{host_port}/api/providers"
        )
        assert status == 200
        assert providers["providers"] == [
            {
                "id": "openai",
                "label": "OpenAI",
                "model": "gpt-5.6-luna",
                "configured": False,
            }
        ]
        assert providers["research_configured"] is False

        status, models = _get_json(f"http://127.0.0.1:{host_port}/api/models")
        assert status == 200
        assert models["default"] == "gpt-5.6-luna"
        assert "gpt-5.6-luna" in models["allowed"]

        status, vault = _get_json(
            f"http://127.0.0.1:{host_port}/api/vault/status"
        )
        assert status == 200
        assert vault == {
            "status": "PASS",
            "backend": "railway-env",
            "configured_secret_count": 0,
        }

        status, owner = _get_json(
            f"http://127.0.0.1:{host_port}/api/owner/status"
        )
        assert status == 200
        assert owner["runtime"] == "P1_BACKEND_ONLY"
        assert set(owner["owner"].values()) == {"UNPROVISIONED"}
    finally:
        subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                str(COMPOSE_FILE),
                "-p",
                project,
                "down",
                "--volumes",
                "--remove-orphans",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "HEALTH_TEST_PORT": str(host_port)},
        )
