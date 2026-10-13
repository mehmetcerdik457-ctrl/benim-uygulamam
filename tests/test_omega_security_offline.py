"""Offline-only fixture evidence. Passing tests do NOT accept OMEGA-023..030."""
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from secrets import token_bytes

import pytest

from omega_mvi.security.offline_contract import (
    FIXTURE_ROLES, OfflineLeaseRegistry, SafeAuditEvent, SecurityDenied,
    check_fixture_scope, encrypt_synthetic_backup, require_live_identity,
    require_live_oidc, restore_synthetic_backup,
)

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
SERVICE = "synthetic.inventory"
DEVICE = "synthetic-device-1"


def test_023_unique_isolated_minimal_scopes():
    assert len(FIXTURE_ROLES) == 5
    assert len(set(FIXTURE_ROLES)) == len(FIXTURE_ROLES)
    assert all(len(scope) == 1 and "*" not in scope for scope in FIXTURE_ROLES.values())
    for service, scopes in FIXTURE_ROLES.items():
        for permitted in scopes:
            assert check_fixture_scope(service, permitted)
    with pytest.raises(SecurityDenied, match="SERVICE_SCOPE_DENIED"):
        check_fixture_scope("synthetic.inventory", "backup:fixture")
    with pytest.raises(SecurityDenied):
        check_fixture_scope("unknown", "repository:read")
    with pytest.raises(SecurityDenied, match="LIVE_IDENTITY_NOT_CONFIGURED"):
        require_live_identity("claimed-owner")


def test_024_expiry_rotation_and_bad_ttl():
    registry = OfflineLeaseRegistry()
    lease = registry.issue(SERVICE, DEVICE, "repository:read", NOW)
    assert registry.check(lease, "repository:read", NOW)
    with pytest.raises(SecurityDenied, match="TOKEN_EXPIRED_OR_REVOKED"):
        registry.check(lease, "repository:read", NOW + timedelta(minutes=5))
    with pytest.raises(SecurityDenied):
        registry.issue(SERVICE, DEVICE, "repository:read", NOW, timedelta(hours=24))
    with pytest.raises(SecurityDenied):
        registry.issue(SERVICE, DEVICE, "repository:read", NOW, timedelta(0))
    registry.rotate_fixture(SERVICE)
    with pytest.raises(SecurityDenied, match="TOKEN_EXPIRED_OR_REVOKED"):
        registry.check(lease, "repository:read", NOW)
    replacement = registry.issue(SERVICE, DEVICE, "repository:read", NOW)
    assert replacement.reference != lease.reference
    assert registry.check(replacement, "repository:read", NOW)
    with pytest.raises(FrozenInstanceError):
        replacement.service = "synthetic.backup"


def test_024_untrusted_device_or_non_utc_denied():
    registry = OfflineLeaseRegistry()
    with pytest.raises(SecurityDenied):
        registry.issue(SERVICE, "production-phone", "repository:read", NOW)
    with pytest.raises(SecurityDenied):
        registry.issue(SERVICE, DEVICE, "repository:read", NOW.replace(tzinfo=None))
    with pytest.raises(SecurityDenied):
        registry.issue(SERVICE, DEVICE, "audit:append", NOW)


def test_025_audit_is_closed_schema_not_secret_payload():
    event = SafeAuditEvent("secret_use", SERVICE, "denied")
    record = event.as_record()
    assert set(record) == {"kind", "service", "outcome"}
    assert not any(k in record for k in ("token", "password", "key", "payload", "path"))
    with pytest.raises(TypeError):
        SafeAuditEvent("secret_use", SERVICE, "denied", token="synthetic-sensitive")
    for bad in ("Bearer synthetic", "synthetic-password", "unknown"):
        with pytest.raises(SecurityDenied):
            SafeAuditEvent("secret_use", bad, "denied").as_record()
    with pytest.raises(SecurityDenied):
        SafeAuditEvent("bad-event:fake-token", SERVICE, "denied").as_record()


def test_027_oidc_is_explicitly_unavailable_even_for_jwt_shaped_text():
    with pytest.raises(SecurityDenied, match="OIDC_TRUST_NOT_CONFIGURED"):
        require_live_oidc("eyJhbGciOiJub25lIn0.e30.")
    with pytest.raises(SecurityDenied, match="OIDC_TRUST_NOT_CONFIGURED"):
        require_live_oidc("claimed-idp", "claimed-owner", "claimed-scope")


def test_029_encrypted_fixture_restore_and_tamper_rejection():
    key = token_bytes(32)  # ephemeral fixture key, never stored or printed
    payload = b"OMEGA-SYNTHETIC-DATA:disposable-backup-v1"
    envelope = encrypt_synthetic_backup(payload, key)
    assert envelope != payload and payload not in envelope
    assert restore_synthetic_backup(envelope, key) == payload
    with pytest.raises(SecurityDenied, match="BACKUP_INTEGRITY_DENIED"):
        restore_synthetic_backup(envelope, token_bytes(32))
    corrupted = bytearray(envelope)
    corrupted[-1] ^= 0x01
    with pytest.raises(SecurityDenied, match="BACKUP_INTEGRITY_DENIED"):
        restore_synthetic_backup(bytes(corrupted), key)
    with pytest.raises(SecurityDenied, match="INVALID_FIXTURE_ENVELOPE"):
        restore_synthetic_backup(envelope[:15], key)
    # Refuse unbounded attacker-controlled envelope before attempting decryption.
    with pytest.raises(SecurityDenied, match="INVALID_FIXTURE_ENVELOPE"):
        restore_synthetic_backup(envelope + b"x" * (1024 * 1024 + 1), key)
    with pytest.raises(SecurityDenied, match="NON_SYNTHETIC_BACKUP_DENIED"):
        encrypt_synthetic_backup(b"production-data", key)


def test_030_device_loss_revocation_and_suspicious_activity():
    registry = OfflineLeaseRegistry()
    lease = registry.issue(SERVICE, DEVICE, "repository:read", NOW)
    registry.device_lost(DEVICE)
    with pytest.raises(SecurityDenied, match="TOKEN_EXPIRED_OR_REVOKED"):
        registry.check(lease, "repository:read", NOW)
    with pytest.raises(SecurityDenied, match="IDENTITY_REVOKED"):
        registry.issue(SERVICE, DEVICE, "repository:read", NOW)
    other = registry.issue(SERVICE, "synthetic-device-2", "repository:read", NOW)
    registry.suspicious_service(SERVICE)
    with pytest.raises(SecurityDenied, match="TOKEN_EXPIRED_OR_REVOKED"):
        registry.check(other, "repository:read", NOW)
    with pytest.raises(SecurityDenied, match="IDENTITY_REVOKED"):
        registry.issue(SERVICE, "synthetic-device-2", "repository:read", NOW)


def test_024_duck_typed_lease_with_forged_equality_cannot_reuse_reference():
    registry = OfflineLeaseRegistry()
    valid = registry.issue(SERVICE, DEVICE, "repository:read", NOW)

    class SpoofedLease:
        reference = valid.reference
        service = valid.service
        device = valid.device
        expires_at = valid.expires_at
        generation = valid.generation

        def __eq__(self, other):
            return True  # malicious equality implementation must not be trusted

    with pytest.raises(SecurityDenied, match="UNKNOWN_LEASE"):
        registry.check(SpoofedLease(), "repository:read", NOW)
    assert registry.check(valid, "repository:read", NOW)
