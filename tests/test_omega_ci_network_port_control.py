"""No-Docker tests for controlled A/B port-publication reproducer."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import omega_ci_network_port_control as control

REQUEST = {"8000/tcp": [{"HostIp": "127.0.0.1", "HostPort": ""}]}
LOOPBACK = {"8000/tcp": [{"HostIp": "127.0.0.1", "HostPort": "49152"}]}


class MockProcess:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.returncode = returncode


class Controls(unittest.TestCase):
    def test_internal_only_failure_with_healthy_normal_control(self):
        self.assertEqual(control.classify("MISSING", "LOOPBACK_ONLY"),
                         "REPRODUCED_INTERNAL_ONLY_PORT_OMISSION")

    def test_both_published_does_not_prove_internal_failure(self):
        self.assertEqual(control.classify("LOOPBACK_ONLY", "LOOPBACK_ONLY"),
                         "NOT_REPRODUCED_BOTH_PUBLISHED")

    def test_inconclusive_failed_normal_control_is_blocked(self):
        self.assertEqual(control.classify("MISSING", "MISSING"), "BLOCKED_INCONCLUSIVE")

    def test_wildcard_binding_is_unsafe(self):
        requested = {"8000/tcp": [{"HostIp": "0.0.0.0", "HostPort": ""}]}
        self.assertEqual(control.mapping(requested, LOOPBACK,
                         "127.0.0.1:49152"), "UNSAFE")

    def test_extra_host_port_is_unsafe(self):
        effective = dict(LOOPBACK)
        effective["9000/tcp"] = [{"HostIp": "127.0.0.1", "HostPort": "49999"}]
        self.assertEqual(control.mapping(REQUEST, effective,
                         "127.0.0.1:49152"), "UNSAFE")

    def test_valid_dynamic_loopback_binding(self):
        self.assertEqual(control.mapping(REQUEST, LOOPBACK,
                         "127.0.0.1:49152"), "LOOPBACK_ONLY")

    def test_missing_internal_binding(self):
        self.assertEqual(control.mapping(REQUEST, {"8000/tcp": None}, None), "MISSING")

    def test_unexpected_docker_port_result_is_unsafe(self):
        self.assertEqual(control.mapping(REQUEST, LOOPBACK,
                         "0.0.0.0:49152"), "UNSAFE")

    def test_partial_create_failure_cleans_only_named_disposable_networks(self):
        calls = []
        def runner(args, **kwargs):
            calls.append(list(args))
            if args[:6] == ["docker", "compose", "-f", "compose.omega.yml", "images", "--quiet"]:
                return MockProcess("a"*64)
            if args[:3] == ["docker", "network", "create"] and "--internal" not in args:
                return MockProcess(returncode=1)
            return MockProcess("synthetic")
        report = control._probe(runner)
        self.assertEqual(report["verdict"], "BLOCKED_INCONCLUSIVE")
        removed = [x for x in calls if x[:3] == ["docker", "network", "rm"]]
        self.assertEqual(len(removed), 1)
        self.assertTrue(removed[0][-1].startswith("omega-ci-netctrl-"))
        self.assertFalse(any(x[:2] == ["docker", "run"] for x in calls))

    def test_success_case_cleans_only_its_two_networks_and_two_containers(self):
        commands = []
        def runner(args, **kwargs):
            commands.append(list(args))
            if args[:6] == ["docker", "compose", "-f", "compose.omega.yml", "images", "--quiet"]:
                return MockProcess("a"*64)
            if args[:3] == ["docker", "inspect", "--format"]:
                value = (REQUEST if "HostConfig.PortBindings" in args[3] else
                         {"8000/tcp": None} if args[-1].endswith("-a") else LOOPBACK)
                return MockProcess(json.dumps(value))
            if args[:2] == ["docker", "port"]:
                return MockProcess(returncode=1) if args[-2].endswith("-a") else MockProcess("127.0.0.1:49152")
            return MockProcess("synthetic")
        result = control._probe(runner)
        self.assertEqual(result, {"internal": "MISSING", "normal": "LOOPBACK_ONLY",
                                  "stage": "BOTH_PORTS_INSPECTED",
                                  "verdict": "REPRODUCED_INTERNAL_ONLY_PORT_OMISSION"})
        removed_containers = [x for x in commands if x[:3] == ["docker", "rm", "--force"]]
        removed_networks = [x for x in commands if x[:3] == ["docker", "network", "rm"]]
        self.assertEqual(len(removed_containers), 2)
        self.assertEqual(len(removed_networks), 2)
        self.assertTrue(all(x[-1].startswith("omega-ci-netctrl-") for x in
                            removed_containers + removed_networks))
        self.assertFalse(any("omega-mvi-demo" in " ".join(x) for x in commands))

    def test_disabled_outside_ci_and_requires_explicit_flag(self):
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(control.main(["--ci-disposable"]), 2)
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(control.main([]), 2)


if __name__ == "__main__":
    unittest.main()
