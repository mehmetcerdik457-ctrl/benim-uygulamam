"""Synthetic OMEGA-030 tabletop evidence: no provider or real device mutation."""

from datetime import datetime, timezone
from secrets import token_bytes
import pytest

from omega_mvi.security.audit_fixture import (
    FixtureAuditLedger, SENTINEL_CONTENT, SENTINEL_NAME,
)
from omega_mvi.security.incident_fixture import (
    require_real_incident_action, simulate_incident,
)
from omega_mvi.security.offline_contract import (
    OfflineLeaseRegistry, SafeAuditEvent, SecurityDenied,
)

NOW = datetime(2026, 10, 12, 9, tzinfo=timezone.utc)


@pytest.fixture
def tabletop(tmp_path):
    (tmp_path / SENTINEL_NAME).write_text(SENTINEL_CONTENT, encoding="ascii")
    key = token_bytes(32)
    audit = FixtureAuditLedger(tmp_path, key, create=True)
    registry = OfflineLeaseRegistry()
    yield registry, audit, tmp_path, key
    audit.close()


def _lease(registry, service, device):
    scope = {"synthetic.inventory": "repository:read",
             "synthetic.pr_review": "pr:read"}[service]
    return registry.issue(service, device, scope, NOW)


def test_030_device_loss_contains_one_device_and_retains_verifiable_audit(tabletop):
    registry, ledger, directory, key = tabletop
    lost = _lease(registry, "synthetic.inventory", "synthetic-device-lost")
    safe = _lease(registry, "synthetic.inventory", "synthetic-device-unaffected")
    result = simulate_incident(registry=registry, ledger=ledger, scenario="device_lost",
                               target="synthetic-device-lost", service="synthetic.inventory",
                               occurred_at=NOW)
    assert result.evidence == "SYNTHETIC_CONTAINMENT_RECORDED"
    assert result.real_provider_revoked is False
    with pytest.raises(SecurityDenied, match="TOKEN_EXPIRED_OR_REVOKED"):
        registry.check(lost, "repository:read", NOW)
    assert registry.check(safe, "repository:read", NOW)
    assert result.anchor.sequence == 2
    assert ledger.verify(expected_anchor=result.anchor) == result.anchor
    ledger.close()
    reopened = FixtureAuditLedger(directory, key)
    assert reopened.verify(expected_anchor=result.anchor) == result.anchor
    reopened.close()
    # Test finalizer only attempts to close already-closed connection.


def test_030_suspicious_service_revokes_every_synthetic_device(tabletop):
    registry, ledger, *_ = tabletop
    a = _lease(registry, "synthetic.inventory", "synthetic-device-1")
    b = _lease(registry, "synthetic.inventory", "synthetic-device-2")
    unrelated = _lease(registry, "synthetic.pr_review", "synthetic-device-3")
    report = simulate_incident(registry=registry, ledger=ledger,
                               scenario="suspicious_service", target="synthetic.inventory",
                               service="synthetic.inventory", occurred_at=NOW)
    assert report.anchor.sequence == 2
    for lease in (a, b):
        with pytest.raises(SecurityDenied):
            registry.check(lease, "repository:read", NOW)
    assert registry.check(unrelated, "pr:read", NOW)


@pytest.mark.parametrize("scenario,target,service", [
    ("device_lost", "real-mobile-device", "synthetic.inventory"),
    ("suspicious_service", "synthetic.pr_review", "synthetic.inventory"),
    ("wipe_everything", "synthetic-device-1", "synthetic.inventory"),
    ("device_lost", "synthetic-device-1", "root"),
])
def test_030_bad_incident_scope_denied_before_mutation(tabletop, scenario, target, service):
    registry, ledger, *_ = tabletop
    safe = _lease(registry, "synthetic.inventory", "synthetic-device-1")
    with pytest.raises(SecurityDenied):
        simulate_incident(registry=registry, ledger=ledger, scenario=scenario,
                          target=target, service=service, occurred_at=NOW)
    assert registry.check(safe, "repository:read", NOW)
    assert ledger.verify().sequence == 0


def test_030_failed_post_containment_audit_still_revokes(tabletop, monkeypatch):
    registry, ledger, *_ = tabletop
    old = _lease(registry, "synthetic.inventory", "synthetic-device-1")
    actual_append = ledger.append
    calls = [0]

    def fail_second(*args, **kwargs):
        calls[0] += 1
        if calls[0] == 2:
            raise SecurityDenied("SYNTHETIC_FAULT")
        return actual_append(*args, **kwargs)

    monkeypatch.setattr(ledger, "append", fail_second)
    with pytest.raises(SecurityDenied, match="INCIDENT_CONTAINED_AUDIT_INCOMPLETE"):
        simulate_incident(registry=registry, ledger=ledger, scenario="device_lost",
                          target="synthetic-device-1", service="synthetic.inventory",
                          occurred_at=NOW)
    with pytest.raises(SecurityDenied):
        registry.check(old, "repository:read", NOW)
    assert ledger.verify().sequence == 1  # incomplete audit is NOT resolution


def test_030_real_provider_action_always_denied(tabletop):
    with pytest.raises(SecurityDenied, match="REAL_INCIDENT_ACTION_REQUIRES_AUTHORIZED_PROVIDER"):
        require_real_incident_action(device="my-phone", auth="self-claimed-owner")
