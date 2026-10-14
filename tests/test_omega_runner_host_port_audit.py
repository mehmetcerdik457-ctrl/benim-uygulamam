"""No-network positive and negative tests for the runner port audit."""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import omega_runner_host_port_audit as audit


class Proc:
    def __init__(self, stdout, returncode=0):
        self.stdout = stdout
        self.returncode = returncode


def runner(*, requested="127.0.0.1", effective=None, internal=True,
           compose_port=None, extra_port=False):
    desired = {"8080/tcp": [{"HostIp": requested, "HostPort": "18080"}]}
    if extra_port:
        desired["9999/tcp"] = [{"HostIp": "0.0.0.0", "HostPort": "9999"}]
    mapped = effective if effective is not None else desired
    observed = "127.0.0.1:18080" if compose_port is None else compose_port

    def fake(args, **kwargs):
        args = list(args)
        if args == ["docker", "version", "--format", "{{.Server.Version}}"]:
            return Proc("29.6.2")
        if args == [*audit.COMPOSE, "ps", "-q", "ingress"]:
            return Proc("disposable-container-id")
        if args == [*audit.COMPOSE, "ps", "-q", "api"]:
            return Proc("disposable-api-id")
        if args == [*audit.COMPOSE, "ps", "-q", "db"]:
            return Proc("disposable-db-id")
        if args[:3] == ["docker", "inspect", "--format"]:
            if args[-1] in ("disposable-api-id", "disposable-db-id"):
                if "NetworkSettings.Ports" in args[3]:
                    port = "8000/tcp" if args[-1] == "disposable-api-id" else "5432/tcp"
                    return Proc(json.dumps({port: None}))
                return Proc(json.dumps({"omega-mvi-demo_isolated_demo": {}}))
            if "HostConfig.PortBindings" in args[3]:
                return Proc(json.dumps(desired))
            if "NetworkSettings.Ports" in args[3]:
                return Proc(json.dumps(mapped))
            if "NetworkSettings.Networks" in args[3]:
                return Proc(json.dumps({"omega-mvi-demo_isolated_demo": {}, "omega-mvi-demo_loopback_ingress": {}}))
        if args[:3] == ["docker", "network", "inspect"]:
            return Proc(json.dumps(internal if args[-1].endswith("_isolated_demo") else False))
        if args == [*audit.COMPOSE, "port", "ingress", "8080"]:
            return Proc(observed)
        return Proc("private information must not leak", 1)
    return fake


class PortAuditTests(unittest.TestCase):
    def test_requested_but_missing_effective_port_is_blocked(self):
        fake = runner(effective={"8080/tcp": None}, compose_port="")
        result = audit.audit(fake)
        self.assertEqual(result["requested"], "LOOPBACK_ONLY")
        self.assertEqual(result["effective"], "MISSING")
        self.assertEqual(result["network"], "SEGMENTED_INGRESS")
        self.assertEqual(result["cause"], "DOCKER_REQUEST_ACCEPTED_BUT_PUBLICATION_NOT_EFFECTIVE")
        self.assertEqual(result["verdict"], "BLOCKED_NOT_ACCEPTED")
        with patch.object(audit, "audit", return_value=result):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(audit.main(), 2)
            self.assertNotIn("disposable-container-id", output.getvalue())

    def test_valid_mapping_is_not_automatically_http_accepted(self):
        result = audit.audit(runner())
        self.assertEqual(result["verdict"], "PORT_CONTRACT_PASS_NOT_HTTP_OR_OWNER")
        self.assertEqual(result["cause"], "DOCKER_MAPPING_PRESENT_HTTP_NOT_YET_CHECKED")
        with patch.object(audit, "audit", return_value=result):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(audit.main(), 0)

    def test_wildcard_requested_mapping_is_unsafe(self):
        result = audit.audit(runner(requested="0.0.0.0"))
        self.assertEqual(result["verdict"], "UNSAFE")
        with patch.object(audit, "audit", return_value=result):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(audit.main(), 1)

    def test_noninternal_network_is_unsafe_even_if_mapping_works(self):
        self.assertEqual(audit.audit(runner(internal=False))["verdict"], "UNSAFE")

    def test_multiple_internal_network_attachments_are_not_accepted(self):
        original = audit._json

        def two_networks(args, fake_runner):
            if "NetworkSettings.Networks" in str(args):
                return {"omega-mvi-demo_isolated_demo": {}, "unexpected-internal": {}}
            return original(args, fake_runner)

        with patch.object(audit, "_json", side_effect=two_networks):
            result = audit.audit(runner())
        self.assertEqual(result["network"], "UNSAFE")
        self.assertEqual(result["verdict"], "UNSAFE")

    def test_unexpected_additional_publication_is_unsafe(self):
        self.assertEqual(audit.audit(runner(extra_port=True))["verdict"], "UNSAFE")

    def test_conflicting_compose_port_is_unsafe(self):
        self.assertEqual(audit.audit(runner(compose_port="0.0.0.0:18080"))["verdict"], "UNSAFE")

    def test_disagreement_between_engine_and_compose_port_blocks(self):
        self.assertEqual(audit.audit(runner(compose_port=""))["verdict"], "BLOCKED_NOT_ACCEPTED")

    def test_missing_docker_blocks_without_leaking_runner_paths(self):
        def fake(*args, **kwargs):
            raise FileNotFoundError("/private/runner/path")
        result = audit.audit(fake)
        self.assertEqual(result["verdict"], "BLOCKED_NOT_ACCEPTED")
        self.assertEqual(result["cause"], "API_CONTAINER_NOT_IDENTIFIED")
        self.assertNotIn("/private", repr(result))


    def test_spoofed_project_network_suffix_is_unsafe(self):
        original = audit._json
        def spoof(args, fake_runner):
            if "NetworkSettings.Networks" in str(args) and args[-1] == "disposable-container-id":
                return {"untrusted_isolated_demo": {},
                        "untrusted_loopback_ingress": {}}
            return original(args, fake_runner)
        with patch.object(audit, "_json", side_effect=spoof):
            result = audit.audit(runner())
        self.assertEqual(result["network"], "UNSAFE")
        self.assertEqual(result["verdict"], "UNSAFE")

    def test_private_services_with_extra_network_or_published_port_are_unsafe(self):
        original = audit._json
        for service in ("api", "db"):
            for kind in ("extra_network", "published_port"):
                def mutated(args, fake_runner):
                    if args[-1] == "disposable-" + service + "-id":
                        if kind == "extra_network" and "NetworkSettings.Networks" in str(args):
                            return {"omega-mvi-demo_isolated_demo": {}, "external": {}}
                        if kind == "published_port" and "NetworkSettings.Ports" in str(args):
                            return {"5432/tcp": [{"HostIp": "0.0.0.0", "HostPort": "5432"}]}
                    return original(args, fake_runner)
                with patch.object(audit, "_json", side_effect=mutated):
                    result = audit.audit(runner())
                self.assertEqual(result["verdict"], "UNSAFE")

    def test_missing_db_runtime_evidence_blocks_acceptance(self):
        base = runner()
        def missing(args, **kwargs):
            if list(args) == [*audit.COMPOSE, "ps", "-q", "db"]:
                return Proc("", 1)
            return base(args, **kwargs)
        self.assertEqual(audit.audit(missing)["verdict"], "BLOCKED_NOT_ACCEPTED")

if __name__ == "__main__":
    unittest.main()
