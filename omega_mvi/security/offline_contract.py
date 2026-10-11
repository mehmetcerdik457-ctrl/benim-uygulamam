"""Non-production OMEGA-023/024/025/027/029/030 synthetic security contract.

This is an isolated test harness, NOT authentication, a token issuer, a secret
store, a production backup tool, or a live OIDC integration. Fail closed.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from secrets import token_hex, token_bytes

FIXTURE_ROLES = {
    "synthetic.inventory": frozenset({"repository:read"}),
    "synthetic.retrieval": frozenset({"rag:read"}),
    "synthetic.pr_review": frozenset({"pr:read"}),
    "synthetic.audit": frozenset({"audit:append"}),
    "synthetic.backup": frozenset({"backup:fixture"}),
}
FIXTURE_MAGIC = b"OMEGA-SYNTHETIC-ONLY-V1\x00"
FIXTURE_DATA_PREFIX = b"OMEGA-SYNTHETIC-DATA:"
MAX_TTL = timedelta(minutes=5)


class SecurityDenied(PermissionError):
    """Deliberately non-sensitive, stable error."""


def require_live_identity(*_args, **_kwargs):
    raise SecurityDenied("LIVE_IDENTITY_NOT_CONFIGURED")


def require_live_oidc(*_args, **_kwargs):
    # Never accept JWT-shaped text, self-asserted principals, or unsigned claims.
    raise SecurityDenied("OIDC_TRUST_NOT_CONFIGURED")


def check_fixture_scope(service: str, action: str) -> bool:
    if service not in FIXTURE_ROLES or action not in FIXTURE_ROLES[service]:
        raise SecurityDenied("SERVICE_SCOPE_DENIED")
    return True


def _utc(now: datetime) -> None:
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise SecurityDenied("UTC_TIME_REQUIRED")


@dataclass(frozen=True)
class LeaseMetadata:
    # A lease reference is NOT a bearer token or a secret value.
    reference: str
    service: str
    device: str
    expires_at: datetime
    generation: int


class OfflineLeaseRegistry:
    """In-memory disposable fixture; never grants privileges in a live service."""

    def __init__(self):
        self._leases = {}
        self._generation = {}
        self._revoked_devices = set()
        self._revoked_services = set()

    def issue(self, service: str, device: str, action: str, now: datetime,
              ttl: timedelta = MAX_TTL) -> LeaseMetadata:
        _utc(now)
        check_fixture_scope(service, action)
        if not isinstance(device, str) or not device.startswith("synthetic-device-"):
            raise SecurityDenied("FIXTURE_DEVICE_REQUIRED")
        if device in self._revoked_devices or service in self._revoked_services:
            raise SecurityDenied("IDENTITY_REVOKED")
        if not isinstance(ttl, timedelta) or not timedelta(0) < ttl <= MAX_TTL:
            raise SecurityDenied("TOKEN_TTL_DENIED")
        generation = self._generation.get(service, 0)
        metadata = LeaseMetadata("synthetic-ref-" + token_hex(12), service,
                                 device, now + ttl, generation)
        self._leases[metadata.reference] = metadata
        return metadata

    def check(self, lease: LeaseMetadata, action: str, now: datetime) -> bool:
        _utc(now)
        stored = self._leases.get(getattr(lease, "reference", None))
        if stored is None or stored != lease:
            raise SecurityDenied("UNKNOWN_LEASE")
        if (lease.expires_at <= now or lease.device in self._revoked_devices
                or lease.service in self._revoked_services
                or lease.generation != self._generation.get(lease.service, 0)):
            raise SecurityDenied("TOKEN_EXPIRED_OR_REVOKED")
        return check_fixture_scope(lease.service, action)

    def rotate_fixture(self, service: str):
        if service not in FIXTURE_ROLES:
            raise SecurityDenied("UNKNOWN_SERVICE")
        self._generation[service] = self._generation.get(service, 0) + 1

    def device_lost(self, device: str):
        if not isinstance(device, str) or not device.startswith("synthetic-device-"):
            raise SecurityDenied("FIXTURE_DEVICE_REQUIRED")
        self._revoked_devices.add(device)

    def suspicious_service(self, service: str):
        if service not in FIXTURE_ROLES:
            raise SecurityDenied("UNKNOWN_SERVICE")
        self._revoked_services.add(service)


@dataclass(frozen=True)
class SafeAuditEvent:
    # Closed vocabulary only; no free-text errors, credential values or paths.
    kind: str
    service: str
    outcome: str

    def as_record(self):
        if self.kind not in {"lease_issue", "lease_rotate", "secret_use", "access_revoke", "incident"}:
            raise SecurityDenied("AUDIT_KIND_DENIED")
        if self.service not in FIXTURE_ROLES:
            raise SecurityDenied("AUDIT_SERVICE_DENIED")
        if self.outcome not in {"allowed_fixture", "denied", "revoked"}:
            raise SecurityDenied("AUDIT_OUTCOME_DENIED")
        return {"kind": self.kind, "service": self.service, "outcome": self.outcome}


def encrypt_synthetic_backup(payload: bytes, key: bytes) -> bytes:
    """AES-256-GCM isolated fixture; key stays with test caller, never serialized."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if (not isinstance(payload, bytes) or not payload.startswith(FIXTURE_DATA_PREFIX)
            or len(payload) > 1024 * 1024):
        raise SecurityDenied("NON_SYNTHETIC_BACKUP_DENIED")
    if not isinstance(key, bytes) or len(key) != 32:
        raise SecurityDenied("INVALID_FIXTURE_KEY")
    nonce = token_bytes(12)
    return FIXTURE_MAGIC + nonce + AESGCM(key).encrypt(nonce, payload, FIXTURE_MAGIC)


def restore_synthetic_backup(envelope: bytes, key: bytes) -> bytes:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if (not isinstance(envelope, bytes) or not envelope.startswith(FIXTURE_MAGIC)
            or not (len(FIXTURE_MAGIC) + 12 + 16
                    <= len(envelope) <= len(FIXTURE_MAGIC) + 12 + 1024 * 1024 + 16)
            or not isinstance(key, bytes) or len(key) != 32):
        raise SecurityDenied("INVALID_FIXTURE_ENVELOPE")
    start = len(FIXTURE_MAGIC)
    nonce, ciphertext = envelope[start:start + 12], envelope[start + 12:]
    try:
        payload = AESGCM(key).decrypt(nonce, ciphertext, FIXTURE_MAGIC)
    except (InvalidTag, ValueError) as exc:
        raise SecurityDenied("BACKUP_INTEGRITY_DENIED") from exc
    if not payload.startswith(FIXTURE_DATA_PREFIX):
        raise SecurityDenied("NON_SYNTHETIC_RESTORE_DENIED")
    return payload
