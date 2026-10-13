"""Synthetic, no-Docker tests for IPv4/IPv6 default-route gate."""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import omega_runner_egress_route_guard as g


class Process:
    def __init__(self, payload="", rc=0):
        self.stdout = payload
        self.returncode = rc


def fixture(v4=False, v6=False, rc=0):
    def runner(cmd, **kwargs):
        assert cmd[:6] == ["docker", "compose", "-f", "compose.omega.yml", "exec", "-T"]
        assert cmd[6:9] == ["api", "python", "-c"]
        return Process(json.dumps({"ipv4_default": v4, "ipv6_default": v6}), rc=rc)
    return runner


def embedded_ipv6_parser():
    # Exercise the exact pure helper used inside docker compose exec,
    # without looking at CI host routes.
    definitions = g._CONTAINER_PROBE.split("print(json.dumps", 1)[0]
    namespace = {}
    exec(definitions, namespace)
    return namespace["classify_ipv6_default"]


def ipv6_row(*, dest=None, prefix="00", flags="00000003", interface="eth0"):
    return " ".join((dest if dest is not None else "0"*32, prefix,
                     "0"*32, "00", "0"*32,
                     "00000000", "00000000", "00000000",
                     flags, interface))


class EgressRouteTests(unittest.TestCase):
    def test_rejecting_ipv6_loopback_default_is_not_usable_egress(self):
        parse = embedded_ipv6_parser()
        self.assertIs(parse([ipv6_row(flags="00200200", interface="lo")]), False)

    def test_real_interface_ipv6_default_is_unsafe(self):
        parse = embedded_ipv6_parser()
        self.assertIs(parse([ipv6_row(flags="00000003", interface="eth0")]), True)

    def test_unknown_loopback_ipv6_default_stays_unverified(self):
        parse = embedded_ipv6_parser()
        self.assertIsNone(parse([ipv6_row(flags="00000003", interface="lo")]))

    def test_malformed_ipv6_route_stays_unverified(self):
        parse = embedded_ipv6_parser()
        self.assertIsNone(parse(["bad route row"]))

    def test_no_routes_is_only_narrow_pass(self):
        self.assertEqual(g.audit(fixture()), {
            "ipv4": "ABSENT", "ipv6": "ABSENT",
            "verdict": "PASS_ROUTES_ABSENT_NOT_FULL_EGRESS_OR_OWNER_ACCEPTANCE"})

    def test_ipv4_default_is_unsafe(self):
        self.assertEqual(g.audit(fixture(v4=True))["verdict"],
                         "UNSAFE_DEFAULT_ROUTE_PRESENT")

    def test_ipv6_default_is_unsafe(self):
        self.assertEqual(g.audit(fixture(v6=True))["verdict"],
                         "UNSAFE_DEFAULT_ROUTE_PRESENT")

    def test_failed_docker_exec_blocks(self):
        self.assertEqual(g.audit(fixture(rc=125))["verdict"],
                         "BLOCKED_NOT_ACCEPTED")

    def test_missing_ipv6_route_does_not_prove_egress_denial(self):
        self.assertEqual(g.audit(fixture(v6=None))["verdict"],
                         "BLOCKED_NOT_ACCEPTED")

    def test_malformed_results_block(self):
        for payload in ('', 'not-json', '[]', '{}',
                        '{"ipv4_default":false,"ipv6_default":false,"unexpected":true}',
                        '{"ipv4_default":0,"ipv6_default":false}'):
            with self.subTest(payload=payload):
                def run(*a, **kw):
                    return Process(payload)
                self.assertEqual(g.audit(run)["verdict"], "BLOCKED_NOT_ACCEPTED")

    def test_never_emit_raw_container_output_or_error_paths(self):
        def fake(*args, **kwargs):
            raise FileNotFoundError("/private/owner/secret")
        with patch.object(g, "audit", return_value=g.audit(fake)):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(g.main(), 2)
            self.assertNotIn("/private", out.getvalue())
            self.assertIn("BLOCKED_NOT_ACCEPTED", out.getvalue())

    def test_exit_codes_success_and_unsafe_are_distinct(self):
        for route, code in ((False, 0), (True, 1)):
            with self.subTest(route=route):
                with patch.object(g, "audit", return_value=g.audit(fixture(v4=route))):
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(g.main(), code)


if __name__ == "__main__":
    unittest.main()
