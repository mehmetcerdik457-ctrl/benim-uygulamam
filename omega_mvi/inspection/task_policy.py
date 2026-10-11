"""Default-deny runtime policy contract; no real IdP is installed."""
from datetime import datetime, timedelta, timezone

READ_SCOPES=frozenset(("repository:read","inventory:read","rag:read","pr:read"))

def require_authenticated_task_permission(task, *, verified_principal=None,
                                         action=None, now=None, spent_minor=0):
    """Enforce budget/scope/deadline but DENY all operations without real IdP.

    Caller-supplied identity strings / model output are NEVER verified identity.
    This function is intentionally non-authorizing until an approved IdP integration
    provides immutable verified principals and durable approval decisions.
    """
    if not isinstance(task,dict) or not verified_principal:
        raise PermissionError("VERIFIED_IDENTITY_REQUIRED")
    # No trusted identity integration: even plausible caller claims are denied.
    raise PermissionError("VERIFIED_IDENTITY_PROVIDER_NOT_CONFIGURED")
