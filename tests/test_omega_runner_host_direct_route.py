"""Offline tests: runner-to-internal-network probe never claims owner/loopback."""
import io
import json
from pathlib import Path
import sys
import unittest
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import omega_runner_host_direct_route as d


class Completed:
    def __init__(self, value, rc=0):
        self.stdout = value
        self.returncode = rc


def fake_docker(*, ip="172.28.0.4", subnet="172.28.0.0/16",
                internal=True, driver="bridge", second=False):
    def run(args, **kwargs):
        args = list(args)
        if args == [*d.COMPOSE, "ps", "-q", "api"]:
            return Completed("synthetic-api-id")
        if args[:3] == ["docker", "inspect", "--format"]:
            data = {"privatebridge": {"IPAddress": ip}}
            if second:
                data["outside"] = {"IPAddress": "10.0.0.2"}
            return Completed(json.dumps(data))
        if args[:3] == ["docker", "network", "inspect"]:
            if ".Internal" in args[4]:
                return Completed(json.dumps(internal))
            if ".Driver" in args[4]:
                return Completed(driver)
            if ".IPAM.Config" in args[4]:
                return Completed(json.dumps([{"Subnet": subnet}]))
        return Completed("do not log raw stdout", 1)
    return run


class Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def valid_http(url, **kwargs):
    if isinstance(url, str):
        return Response(b'{"mode":"mock","production_ready":false,"external_api_enabled":false}')
    raise HTTPError("http://redacted.invalid", 403, "DENIED", None, None)


class DirectRouteTests(unittest.TestCase):
    def test_positive_direct_access_is_neither_loopback_nor_owner_acceptance(self):
        result = d.diagnose(runner=fake_docker(), opener=valid_http)
        self.assertEqual(result, {
            "scope": "SINGLE_INTERNAL_BRIDGE_RFC1918",
            "http": "PASS_HOST_TO_INTERNAL_ONLY",
            "verdict": "PASS_DIRECT_HOST_TO_INTERNAL_NOT_LOOPBACK_OR_OWNER"
        })

    def test_container_refusal_is_blocked(self):
        def refuse(*args, **kwargs):
            raise ConnectionRefusedError("synthetic")
        self.assertEqual(d.diagnose(runner=fake_docker(), opener=refuse)["http"],
                         "HOST_TO_CONTAINER_BLOCKED")

    def test_noninternal_network_is_rejected_before_http(self):
        self.assertEqual(d.diagnose(runner=fake_docker(internal=False))["scope"],
                         "NETWORK_SCOPE_UNSAFE")

    def test_nonbridge_network_is_rejected(self):
        self.assertEqual(d.diagnose(runner=fake_docker(driver="macvlan"))["scope"],
                         "NETWORK_SCOPE_UNSAFE")

    def test_multiple_network_attachments_are_rejected(self):
        self.assertEqual(d.diagnose(runner=fake_docker(second=True))["scope"],
                         "NETWORK_SCOPE_UNVERIFIED")

    def test_ip_is_required_to_match_docker_ipam(self):
        self.assertEqual(d.diagnose(runner=fake_docker(subnet="172.29.0.0/16"))["scope"],
                         "IPAM_UNVERIFIED")

    def test_public_ip_is_rejected(self):
        self.assertEqual(d.diagnose(runner=fake_docker(ip="8.8.8.8"))["scope"],
                         "NETWORK_SCOPE_UNSAFE")

    def test_execute_allowed_fails(self):
        def open_success(*args, **kwargs):
            if isinstance(args[0], str):
                return valid_http(*args, **kwargs)
            return Response(b'{}')
        self.assertEqual(d.diagnose(runner=fake_docker(), opener=open_success)["http"],
                         "EXECUTION_UNEXPECTEDLY_ALLOWED")

    def test_health_invalid_fails(self):
        def invalid(*args, **kwargs):
            return Response(b'{"mode":"production","production_ready":true}')
        self.assertEqual(d.diagnose(runner=fake_docker(), opener=invalid)["http"],
                         "HTTP_HEALTH_INVALID")


if __name__ == "__main__":
    unittest.main()
