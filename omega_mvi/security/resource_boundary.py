"""OMEGA-023: fixture-only resource isolation and minimum-permission contract.

A GitHub provider principal, real workload identity or user login is NEVER
created or inferred. Caller text and service labels are not trusted IAM. This
contract checks only synthetic lease references held by an offline registry.
"""

from __future__ import annotations
from datetime import datetime

from .offline_contract import OfflineLeaseRegistry, SecurityDenied

SYNTHETIC_TENANT = "synthetic-tenant-omega"
RESOURCE_POLICY = {
    "synthetic.inventory": ("repository:read", "synthetic-repository-omega"),
    "synthetic.retrieval": ("rag:read", "synthetic-rag-omega"),
    "synthetic.pr_review": ("pr:read", "synthetic-pr-omega"),
    "synthetic.audit": ("audit:append", "synthetic-audit-omega"),
    "synthetic.backup": ("backup:fixture", "synthetic-backup-omega"),
}


def require_synthetic_resource_authorization(*, registry: OfflineLeaseRegistry,
                                             lease, tenant: str,
                                             resource: str, scope: str,
                                             now: datetime) -> bool:
    if type(registry) is not OfflineLeaseRegistry:
        raise SecurityDenied("RESOURCE_TRUSTED_REGISTRY_REQUIRED")
    service = getattr(lease, "service", None)
    policy = RESOURCE_POLICY.get(service)
    # Reject broad resource selectors, cross-tenant claims, and unused scopes.
    if (policy is None or type(tenant) is not str
            or tenant != SYNTHETIC_TENANT
            or type(resource) is not str or resource != policy[1]
            or type(scope) is not str or scope != policy[0]):
        raise SecurityDenied("RESOURCE_BOUNDARY_DENIED")
    registry.check(lease, scope, now)
    return True


def require_live_workload_authorization(*_args, **_kwargs):
    raise SecurityDenied("TRUSTED_WORKLOAD_IDENTITY_NOT_PROVISIONED")
