"""Deny-first runtime contract for OMEGA-053 controls.

The evaluator checks budget, read scopes and expiry, but NO live IdP is
configured. It never yields an ALLOW decision. Caller text is never identity.
"""
from datetime import datetime, timedelta, timezone

READ_SCOPES=frozenset(("repository:read","inventory:read","rag:read","pr:read"))

def require_authenticated_task_permission(task, *, verified_principal=None,
                                          action=None, now=None, spent_minor=0):
    if not isinstance(task,dict):
        raise PermissionError("TASK_CONTRACT_REQUIRED")
    if verified_principal is None:
        raise PermissionError("VERIFIED_IDENTITY_REQUIRED")
    # A claimed username, JWT-shaped string or LLM statement is not an IdP.
    budget=task.get("budget_limit_minor")
    currency=task.get("budget_currency")
    deadline=task.get("deadline_utc")
    scopes=task.get("permissions")
    if type(budget) is not int or budget<0 or currency not in ("USD","TRY"):
        raise PermissionError("INVALID_BUDGET")
    if type(spent_minor) is not int or spent_minor<0 or spent_minor>budget:
        raise PermissionError("BUDGET_EXHAUSTED")
    if not isinstance(scopes,(tuple,list)) or any(type(x) is not str for x in scopes):
        raise PermissionError("INVALID_PERMISSIONS")
    if not set(scopes).issubset(READ_SCOPES) or action not in READ_SCOPES or action not in scopes:
        raise PermissionError("SCOPE_DENIED")
    if now is None:
        now=datetime.now(timezone.utc)
    if not isinstance(now,datetime) or now.tzinfo is None or now.utcoffset()!=timedelta(0):
        raise PermissionError("INVALID_NOW")
    if not isinstance(deadline,datetime) or deadline.tzinfo is None or deadline.utcoffset()!=timedelta(0):
        raise PermissionError("INVALID_DEADLINE")
    if deadline<=now:
        raise PermissionError("DEADLINE_EXPIRED")
    # Even perfect budget/scope/time checks cannot elevate caller text to IdP.
    raise PermissionError("VERIFIED_IDENTITY_PROVIDER_NOT_CONFIGURED")
