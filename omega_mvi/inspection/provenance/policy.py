"""Synthetic-only provenance transition risk report. No permissions are issued.

This module deliberately does NOT persist records, authorize deletes, sign
custody receipts, or grant any filesystem access. Inputs are index snapshots
validated by the existing SHA-256 verifier.
"""
from __future__ import annotations

from omega_mvi.inspection.provenance import compare_indices


def review_provenance_changes(old: dict, new: dict) -> dict:
    """Identify owner, source and retention changes that need independent review.

    A source hash only detects integrity drift: it cannot prove identity or
    consent. Human approval must be verified by a separate trusted service.
    """
    drift = compare_indices(old, new)
    prior, current = old["entries"], new["entries"]
    fields = ("source_version", "owner_ref", "access_level", "retention_days")
    changed = {}
    for key in sorted(prior.keys() & current.keys()):
        differences = [field for field in fields if prior[key][field] != current[key][field]]
        # Operating-system ownership, mode, ACL and xattrs can alter effective
        # access even if the high-level access_level label stays unchanged.
        for field in ("mode", "uid", "gid", "acl_sha256", "xattr_sha256"):
            if prior[key]["metadata"][field] != current[key]["metadata"][field]:
                differences.append("metadata." + field)
        if differences:
            changed[key] = differences
    # Additions, removals and CONTENT changes require independent review.\n    # A correct checksum is integrity evidence, never a source approval.
    approval_items = sorted(set(drift["added"] + drift["removed"] + drift["content_changed"] + list(changed)))
    return {
        "schema": "omega.synthetic-provenance-transition.v1",
        "old_index_sha256": old["index_sha256"],
        "new_index_sha256": new["index_sha256"],
        "added": drift["added"],
        "removed": drift["removed"],
        "content_changed": drift["content_changed"],
        "metadata_changed": drift["metadata_changed"],
        "policy_fields_changed": changed,
        "requires_external_review": bool(approval_items),
        "review_items": approval_items,
        "approval_granted": False,
        "deletion_authorized": False,
        "storage_retention_enforced": False,
        "identity_verified": False,
    }
