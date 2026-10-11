from scripts.omega_loopback_model_benchmark import CASES, probe
import pytest


def test_only_synthetic_nonsecret_smoke_cases():
    assert {case[0] for case in CASES} == {"tr", "en", "code"}
    assert all(len(case[1]) < 128 for case in CASES)


def test_closed_loopback_no_server_cannot_be_benchmark_evidence():
    # Port 0 is not a remote service; connection failure is expected.
    with pytest.raises(OSError):
        probe("mock", 0, "public synthetic", 1, timeout=1)
