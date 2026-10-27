from scripts.omega_local_hardware_probe import _read_positive_int, profile_now


def test_probe_does_not_claim_owner_access():
    item = profile_now()
    assert item["evidence_scope"] == "EXECUTION_ENVIRONMENT_ONLY_NOT_OWNER_DEVICE"
    assert item["inference_measured"] is False
    assert "hostname" not in item and "serial" not in item


def test_memory_parser_fails_closed_on_missing_file():
    assert _read_positive_int("/path-does-not-exist-omega") is None
