"""OMEGA-030 isolated incident tabletop, not an IdP/device revocation service.

The ONLY changes are to a disposable OfflineLeaseRegistry and synthetic
FixtureAuditLedger. This cannot revoke real sessions or contact any provider.
"""

from dataclasses import dataclass
from datetime import datetime

from .offline_contract import (
    FIXTURE_ROLES, OfflineLeaseRegistry, SafeAuditEvent, SecurityDenied,
)
from .audit_fixture import AuditAnchor, FixtureAuditLedger


@dataclass(frozen=True)
class IncidentResult:
    scenario: str
    evidence: str
    anchor: AuditAnchor
    real_provider_revoked: bool = False


def simulate_incident(*, registry: OfflineLeaseRegistry, ledger: FixtureAuditLedger,
                      scenario: str, target: str, service: str,
                      occurred_at: datetime) -> IncidentResult:
    if type(registry) is not OfflineLeaseRegistry or type(ledger) is not FixtureAuditLedger:
        raise SecurityDenied("INCIDENT_SYNTHETIC_FIXTURE_REQUIRED")
    if service not in FIXTURE_ROLES:
        raise SecurityDenied("INCIDENT_SERVICE_DENIED")
    if scenario not in ("device_lost", "suspicious_service"):
        raise SecurityDenied("INCIDENT_KIND_DENIED")
    if scenario == "device_lost":
        if not isinstance(target, str) or not target.startswith("synthetic-device-"):
            raise SecurityDenied("INCIDENT_DEVICE_DENIED")
    elif target != service:
        raise SecurityDenied("INCIDENT_SCOPE_MISMATCH")
    # UTC validity and writable audit must be checked BEFORE simulated containment.
    # Failure after containment still leaves the fixture revoked (fail closed).
    _ = ledger.verify()
    # This event is safe by construction, with no device id, token, IP or free text.
    ledger.append(writer="synthetic.audit",
                  event=SafeAuditEvent("incident", service, "denied"),
                  occurred_at=occurred_at)
    if scenario == "device_lost":
        registry.device_lost(target)
    else:
        registry.suspicious_service(target)
    try:
        anchor = ledger.append(
            writer="synthetic.audit",
            event=SafeAuditEvent("access_revoke", service, "revoked"),
            occurred_at=occurred_at,
        )
    except SecurityDenied:
        # Audit failure is NEVER interpreted as a successful incident resolution.
        # Containment remains in force; operator must repair evidence before closure.
        raise SecurityDenied("INCIDENT_CONTAINED_AUDIT_INCOMPLETE") from None
    return IncidentResult(scenario, "SYNTHETIC_CONTAINMENT_RECORDED", anchor)


def require_real_incident_action(*_args, **_kwargs):
    raise SecurityDenied("REAL_INCIDENT_ACTION_REQUIRES_AUTHORIZED_PROVIDER")
