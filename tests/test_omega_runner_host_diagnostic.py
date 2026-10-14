"""No-network deterministic tests of the runner-host acceptance diagnostic."""
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import omega_runner_host_diagnostic as h


class Connection:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def close(self):
        pass


class Response(BytesIO):
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


class Result:
    def __init__(self, out, rc=0):
        self.stdout = out
        self.returncode = rc


def runner_factory(*, address="127.0.0.1", internal=True, inside="OK"):
    def fake(args, **kwargs):
        cmd = " ".join(args[:3])
        if args[-3:] == ["ps", "-q", "ingress"]:
            return Result("synthetic-container-id")
        if args[-3:] == ["ps", "-q", "api"]:
            return Result("synthetic-api-id")
        if args[-3:] == ["ps", "-q", "db"]:
            return Result("synthetic-db-id")
        if args[:3] == ["docker", "inspect", "--format"]:
            if args[-1] in ("synthetic-api-id", "synthetic-db-id"):
                if "Ports" in args[3]:
                    port = "8000/tcp" if args[-1] == "synthetic-api-id" else "5432/tcp"
                    return Result(json.dumps({port: None}))
                return Result(json.dumps({"omega-mvi-demo_isolated_demo": {}}))
            if "Ports" in args[3]:
                return Result(json.dumps({"8080/tcp": [
                    {"HostIp": address, "HostPort": "18080"}]}))
            return Result(json.dumps({"omega-mvi-demo_isolated_demo": {}, "omega-mvi-demo_loopback_ingress": {}}))
        if args[:3] == ["docker", "network", "inspect"]:
            return Result(("true" if internal else "false") if args[-1].endswith("_isolated_demo") else "false")
        if args[:5] == ["docker", "compose", "-f", "compose.omega.yml", "exec"]:
            return Result(inside)
        return Result("", rc=1)
    return fake


def denied_opener(request, **kwargs):
    if isinstance(request, str):
        return Response(b'{"mode":"mock","production_ready":false}')
    raise HTTPError("http://localhost.invalid", 403, "DENIED", None, None)


def refused(*args, **kwargs):
    raise ConnectionRefusedError("synthetic, not from a real runner")


def test_internal_network_and_declared_loopback_can_still_be_refused():
    report = h.diagnose(runner=runner_factory(), connector=refused)
    assert report == {
        "binding": "LOOPBACK_ONLY", "network": "SEGMENTED_INGRESS",
        "container": "PASS", "tcp": "REFUSED",
        "http": "BLOCKED", "verdict": "BLOCKED_NOT_ACCEPTED",
        "cause": "TCP_CONNECTION_REFUSED_ROOT_CAUSE_UNKNOWN",
    }


def test_runner_only_success_requires_all_evidence_and_denied_execute():
    report = h.diagnose(runner=runner_factory(),
                        connector=lambda *args, **kwargs: Connection(),
                        opener=denied_opener)
    assert report["verdict"] == "PASS_RUNNER_ONLY_NOT_OWNER"
    assert report["http"] == "PASS"
    assert report["network"] == "SEGMENTED_INGRESS"


def test_no_unrestricted_host_binding_is_accepted():
    report = h.diagnose(runner=runner_factory(address="0.0.0.0"),
                        connector=refused)
    assert report["binding"] == "UNSAFE"
    assert report["verdict"] == "UNSAFE"


def test_noninternal_network_denies_even_if_runner_can_connect():
    report = h.diagnose(runner=runner_factory(internal=False),
                        connector=lambda *a, **k: Connection(),
                        opener=denied_opener)
    assert report["verdict"] == "UNSAFE"


def test_observation_is_distinct_from_required_acceptance(monkeypatch, capsys):
    report = h.diagnose(runner=runner_factory(), connector=refused)
    monkeypatch.setattr(h, "diagnose", lambda: report)
    assert h.main([]) == 0
    assert h.main(["--require-runner-host"]) == 2
    output = capsys.readouterr()
    assert "OMEGA_RUNNER_HOST_VERDICT=BLOCKED_NOT_ACCEPTED" in output.out
    assert "ROOT_CAUSE_UNKNOWN" in output.out
    assert "synthetic-container-id" not in output.out
    assert not output.err


def test_missing_docker_does_not_claim_host_pass():
    def missing(*args, **kwargs):
        raise FileNotFoundError("private runner path must never be printed")
    result = h.diagnose(runner=missing, connector=refused)
    assert result["verdict"] == "BLOCKED_NOT_ACCEPTED"
    assert result["binding"] == "UNVERIFIED"
    assert result["network"] == "UNVERIFIED"

def test_effective_docker_port_mapping_missing_is_specific_blocker():
    normal = runner_factory()
    def no_binding(args, **kwargs):
        if args[:3] == ["docker", "inspect", "--format"] and "Ports" in args[3]:
            return Result(json.dumps({"8080/tcp": None}))
        return normal(args, **kwargs)
    report = h.diagnose(runner=no_binding, connector=refused)
    assert report["network"] == "SEGMENTED_INGRESS"
    assert report["binding"] == "MISSING"
    assert report["tcp"] == "REFUSED"
    assert report["cause"] == "HOST_PORT_MAPPING_MISSING_UPSTREAM_CAUSE_UNKNOWN"
    assert report["verdict"] == "BLOCKED_NOT_ACCEPTED"


def test_extra_duplicate_or_malformed_published_ports_are_unsafe():
    base = runner_factory()
    valid = {"HostIp": "127.0.0.1", "HostPort": "18080"}
    for published in (
        {"8080/tcp": [valid, valid]},
        {"8080/tcp": [valid], "9999/tcp": [{"HostIp": "0.0.0.0", "HostPort": "9999"}]},
        {"8080/tcp": [dict(valid, unexpected="field")]},
        {"8080/tcp": ["not-a-port-mapping"]},
        {"8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": 18080}]},
    ):
        def fake(args, **kwargs):
            if args[:3] == ["docker", "inspect", "--format"] and "Ports" in args[3]:
                return Result(json.dumps(published))
            return base(args, **kwargs)
        report = h.diagnose(runner=fake,
                            connector=lambda *a, **k: Connection(),
                            opener=denied_opener)
        assert report["binding"] == "UNSAFE"
        assert report["verdict"] == "UNSAFE"


def test_unpublished_extra_exposed_port_does_not_fake_an_unsafe_bind():
    base = runner_factory()
    def fake(args, **kwargs):
        if args[:3] == ["docker", "inspect", "--format"] and "Ports" in args[3]:
            return Result(json.dumps({
                "8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": "18080"}],
                "8000/tcp": None,
            }))
        return base(args, **kwargs)
    report = h.diagnose(runner=fake,
                        connector=lambda *a, **k: Connection(),
                        opener=denied_opener)
    assert report["binding"] == "LOOPBACK_ONLY"
    assert report["verdict"] == "PASS_RUNNER_ONLY_NOT_OWNER"


def test_project_network_name_suffix_spoof_is_unsafe():
    base = runner_factory()
    def spoof(args, **kwargs):
        if (args[:3] == ["docker", "inspect", "--format"]
                and "NetworkSettings.Networks" in args[3]
                and args[-1] == "synthetic-container-id"):
            return Result(json.dumps({
                "untrusted_isolated_demo": {},
                "untrusted_loopback_ingress": {},
            }))
        return base(args, **kwargs)
    report = h.diagnose(runner=spoof,
                        connector=lambda *a, **k: Connection(),
                        opener=denied_opener)
    assert report["network"] == "UNSAFE"
    assert report["verdict"] == "UNSAFE"


def test_live_api_db_extra_network_or_host_publication_is_unsafe():
    base = runner_factory()
    for service in ("api", "db"):
        for kind in ("network", "published"):
            def altered(args, **kwargs):
                if (args[:3] == ["docker", "inspect", "--format"]
                        and args[-1] == "synthetic-" + service + "-id"):
                    if kind == "network" and "NetworkSettings.Networks" in args[3]:
                        return Result(json.dumps({
                            "omega-mvi-demo_isolated_demo": {},
                            "unreviewed_external": {},
                        }))
                    if kind == "published" and "NetworkSettings.Ports" in args[3]:
                        return Result(json.dumps({
                            "5432/tcp": [{"HostIp": "0.0.0.0", "HostPort": "5432"}]
                        }))
                return base(args, **kwargs)
            report = h.diagnose(runner=altered,
                                connector=lambda *a, **k: Connection(),
                                opener=denied_opener)
            assert report["network"] == "UNSAFE"
            assert report["verdict"] == "UNSAFE"


def test_missing_runtime_database_blocks_host_acceptance():
    base = runner_factory()
    def missing(args, **kwargs):
        if args[-3:] == ["ps", "-q", "db"]:
            return Result("", rc=1)
        return base(args, **kwargs)
    report = h.diagnose(runner=missing,
                        connector=lambda *a, **k: Connection(),
                        opener=denied_opener)
    assert report["network"] == "UNVERIFIED"
    assert report["verdict"] == "BLOCKED_NOT_ACCEPTED"
