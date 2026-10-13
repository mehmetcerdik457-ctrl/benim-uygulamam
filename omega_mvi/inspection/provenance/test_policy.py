"""Fail-closed fixture-only checks for sensitive provenance transitions."""
import copy
import hashlib

import pytest

from omega_mvi.inspection.provenance import make_fixture_record, build_index
from omega_mvi.inspection.provenance.policy import review_provenance_changes


EMPTY = hashlib.sha256(b"").hexdigest()


def record(*, name="safe.txt", owner="owner:test", level="internal", retention=7,
           revision="v1", mtime=100, mode=0o600, uid=1, gid=1, data=b"synthetic-only",
           acl=EMPTY, xattr=EMPTY, verified="2026-10-12T08:00:00Z"):
    return make_fixture_record(
        source_ref="synthetic://fixture", relative_path=name,
        source_version=revision, data=data, owner_ref=owner,
        access_level=level, verified_at=verified, retention_days=retention,
        metadata=dict(kind="regular_file", size_bytes=len(data), mtime_ns=mtime,
                      mode=mode, uid=uid, gid=gid,
                      acl_sha256=acl, xattr_sha256=xattr),
    )


def transition(before, after):
    old = build_index(before, version=1)
    new = build_index(after, version=2, previous=old)
    return review_provenance_changes(old, new)


@pytest.mark.parametrize(("modified", "field"), [
    ({"owner": "owner:new"}, "owner_ref"),
    ({"level": "public"}, "access_level"),
    ({"level": "confidential"}, "access_level"),
    ({"retention": 365}, "retention_days"),
    ({"retention": 1}, "retention_days"),
    ({"revision": "v2"}, "source_version"),
])
def test_sensitive_change_never_approves_itself(modified, field):
    r = transition([record()], [record(**modified)])
    assert r["requires_external_review"] is True
    assert r["policy_fields_changed"] == {"synthetic://fixture/safe.txt": [field]}
    assert r["approval_granted"] is False
    assert r["identity_verified"] is False
    assert r["deletion_authorized"] is False
    assert r["storage_retention_enforced"] is False


def test_metadata_only_requires_integrity_review_not_authority_grant():
    r = transition([record()], [record(mtime=200)])
    assert r["metadata_changed"] == ["synthetic://fixture/safe.txt"]
    assert r["policy_fields_changed"] == {}
    assert r["requires_external_review"] is False
    assert r["approval_granted"] is False


def test_verification_timestamp_only_not_equivalent_to_renewed_retention():
    r = transition([record()], [record(verified="2026-10-13T08:00:00Z")])
    assert r["policy_fields_changed"] == {}
    assert r["storage_retention_enforced"] is False
    assert r["approval_granted"] is False


@pytest.mark.parametrize("kind", ["added", "removed"])
def test_collection_membership_changes_need_review(kind):
    existing = record()
    if kind == "added":
        r = transition([existing], [existing, record(name="new.txt")])
    else:
        r = transition([existing], [])
    assert r["requires_external_review"] is True
    assert r[kind] != []
    assert r["approval_granted"] is False
    assert r["deletion_authorized"] is False


def test_multi_field_changes_are_deterministic_and_scope_bounded():
    r = transition([record()], [record(owner="owner:new", level="public", retention=1)])
    assert r["policy_fields_changed"] == {
        "synthetic://fixture/safe.txt": ["owner_ref", "access_level", "retention_days"]
    }
    assert r["review_items"] == ["synthetic://fixture/safe.txt"]


def test_tampered_index_is_rejected_before_policy_report():
    a = build_index([record()], version=1)
    b = build_index([record()], version=2, previous=a)
    forged = copy.deepcopy(b)
    forged["entries"]["synthetic://fixture/safe.txt"]["owner_ref"] = "owner:intruder"
    with pytest.raises(ValueError):
        review_provenance_changes(a, forged)


def test_out_of_order_or_unlinked_index_rejected():
    a = build_index([record()], version=1)
    b = build_index([record()], version=2, previous=a)
    with pytest.raises(ValueError):
        review_provenance_changes(b, a)


@pytest.mark.parametrize(("modified", "field"), [
    ({"mode": 0o644}, "metadata.mode"),
    ({"uid": 2}, "metadata.uid"),
    ({"gid": 2}, "metadata.gid"),
    ({"acl": hashlib.sha256(b"changed-acl-fixture").hexdigest()}, "metadata.acl_sha256"),
    ({"xattr": hashlib.sha256(b"changed-xattr-fixture").hexdigest()}, "metadata.xattr_sha256"),
])
def test_effective_permissions_changes_require_review(modified, field):
    result = transition([record()], [record(**modified)])
    assert result["requires_external_review"] is True
    assert result["policy_fields_changed"] == {"synthetic://fixture/safe.txt": [field]}
    assert result["approval_granted"] is False
    assert result["deletion_authorized"] is False


def test_content_sha_change_with_same_identity_forces_independent_review():
    # No owner/access/version labels change. A new document body must still
    # be reviewed before it can be accepted into a trusted source snapshot.
    old = build_index([record()], version=1)
    new = build_index([record(data=b"changed-synthetic-content")], version=2, previous=old)
    report = review_provenance_changes(old, new)
    assert report["content_changed"] == ["synthetic://fixture/safe.txt"]
    assert report["requires_external_review"] is True
    assert report["review_items"] == ["synthetic://fixture/safe.txt"]
    assert report["approval_granted"] is False
    assert report["identity_verified"] is False


def test_unchanged_content_does_not_invent_review_trigger():
    old = build_index([record()], version=1)
    new = build_index([record()], version=2, previous=old)
    report = review_provenance_changes(old, new)
    assert report["content_changed"] == []
    assert report["requires_external_review"] is False
