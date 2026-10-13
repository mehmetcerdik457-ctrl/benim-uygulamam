"""OMEGA-023 explicit synthetic scope/resource/tenant negative evidence."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from omega_mvi.security.offline_contract import OfflineLeaseRegistry, SecurityDenied
from omega_mvi.security.resource_boundary import (
    RESOURCE_POLICY, SYNTHETIC_TENANT,
    require_live_workload_authorization,
    require_synthetic_resource_authorization,
)

NOW = datetime(2026, 10, 13, 8, tzinfo=timezone.utc)
DEVICE = "synthetic-device-identity"


@pytest.mark.parametrize("service,policy", list(RESOURCE_POLICY.items()))
def test_023_fixture_each_service_only_exact_resource(service, policy):
    registry = OfflineLeaseRegistry()
    scope, resource = policy
    lease = registry.issue(service, DEVICE, scope, NOW)
    params = dict(registry=registry, lease=lease, tenant=SYNTHETIC_TENANT,
                  resource=resource, scope=scope, now=NOW)
    assert require_synthetic_resource_authorization(**params)
    for change in [
        {"tenant": "another-tenant"},
        {"tenant": "*"},
        {"resource": "*"},
        {"resource": "synthetic-other"},
        {"scope": "admin:*"},
        {"scope": "repository:write"},
    ]:
        with pytest.raises(SecurityDenied, match="RESOURCE_BOUNDARY_DENIED"):
            require_synthetic_resource_authorization(**{**params, **change})
    with pytest.raises(SecurityDenied, match="TOKEN_EXPIRED_OR_REVOKED"):
        require_synthetic_resource_authorization(
            **{**params, "now": NOW + timedelta(minutes=5)}
        )


def test_023_cannot_forge_different_service_into_existing_lease():
    registry = OfflineLeaseRegistry()
    lease = registry.issue("synthetic.inventory", DEVICE, "repository:read", NOW)
    other_service = replace(lease, service="synthetic.backup")
    with pytest.raises(SecurityDenied, match="UNKNOWN_LEASE"):
        require_synthetic_resource_authorization(
            registry=registry, lease=other_service, tenant=SYNTHETIC_TENANT,
            resource="synthetic-backup-omega", scope="backup:fixture", now=NOW,
        )


def test_023_rotated_or_revoked_lease_cannot_use_same_resource():
    registry = OfflineLeaseRegistry()
    lease = registry.issue("synthetic.inventory", DEVICE, "repository:read", NOW)
    registry.rotate_fixture("synthetic.inventory")
    with pytest.raises(SecurityDenied, match="TOKEN_EXPIRED_OR_REVOKED"):
        require_synthetic_resource_authorization(
            registry=registry, lease=lease, tenant=SYNTHETIC_TENANT,
            resource="synthetic-repository-omega", scope="repository:read", now=NOW,
        )


def test_023_live_workload_identity_always_denied():
    with pytest.raises(SecurityDenied, match="TRUSTED_WORKLOAD_IDENTITY_NOT_PROVISIONED"):
        require_live_workload_authorization(
            claimed_service="synthetic.inventory", claimed_access="all"
        )
