"""Offline synthetic tests; never touch owner disks or external services."""
import copy
import pytest
from omega_mvi.inspection.provenance import make_fixture_record, build_index, compare_indices


def fields(data=b"hello", **overrides):
    metadata = dict(kind="regular_file", size_bytes=len(data), mtime_ns=100,
                    mode=0o600, uid=1000, gid=1000, acl_sha256=None, xattr_sha256=None)
    metadata.update(overrides)
    return dict(source_ref="synthetic://case-01", relative_path="safe/file.txt",
                source_version="v1", data=data, metadata=metadata,
                owner_ref="owner:synthetic", access_level="internal",
                verified_at="2026-10-11T10:00:00Z", retention_days=7)


def record(data=b"hello", **overrides):
    return make_fixture_record(**fields(data, **overrides))


def test_content_change_detected():
    a = build_index([record()], version=1)
    b = build_index([record(b"world")], version=2, previous=a)
    d = compare_indices(a, b)
    assert d["content_changed"] == ["synthetic://case-01/safe/file.txt"]
    assert d["metadata_changed"] == []


@pytest.mark.parametrize("changed", [dict(mtime_ns=101), dict(mode=0o644),
                                    dict(uid=999), dict(gid=999), dict(acl_sha256="f" * 64),
                                    dict(xattr_sha256="a" * 64)])
def test_metadata_only_change_detected(changed):
    a = build_index([record()], version=1)
    opts = fields()
    opts["metadata"].update(changed)
    b = build_index([make_fixture_record(**opts)], version=2, previous=a)
    d = compare_indices(a, b)
    assert d["metadata_changed"] == ["synthetic://case-01/safe/file.txt"]
    assert not d["content_changed"]


def test_provenance_change_detected_without_content_change():
    a = build_index([record()], version=1)
    opts = fields()
    opts.update(owner_ref="owner:second", access_level="confidential",
                source_version="v2", retention_days=10,
                verified_at="2026-10-12T10:00:00+00:00")
    b = build_index([make_fixture_record(**opts)], version=2, previous=a)
    assert compare_indices(a, b)["provenance_changed"] == ["synthetic://case-01/safe/file.txt"]
    assert a["entries"]["synthetic://case-01/safe/file.txt"]["content_sha256"] == b["entries"]["synthetic://case-01/safe/file.txt"]["content_sha256"]


def test_version_link_and_tamper_rejected():
    a = build_index([record()], version=1)
    with pytest.raises(ValueError):
        build_index([record()], version=3, previous=a)
    b = build_index([record()], version=2, previous=a)
    tampered = copy.deepcopy(a)
    tampered["entries"]["synthetic://case-01/safe/file.txt"]["metadata"]["mode"] = 0o777
    with pytest.raises(ValueError):
        compare_indices(tampered, b)
    with pytest.raises(ValueError):
        compare_indices(b, a)


def test_negative_scope_guards():
    for src in ("file:///home/user", "github://org/private", "", None):
        args = fields()
        args["source_ref"] = src
        with pytest.raises(PermissionError):
            make_fixture_record(**args)
    for path in ("../escape", "/abs", "a/../b", "a//b", "a\\b"):
        args = fields()
        args["relative_path"] = path
        with pytest.raises(ValueError):
            make_fixture_record(**args)
    args = fields()
    args["access_level"] = "restricted"
    with pytest.raises(PermissionError):
        make_fixture_record(**args)
    args = fields()
    args["retention_days"] = 0
    with pytest.raises(ValueError):
        make_fixture_record(**args)


def test_missing_or_mismatched_metadata_fails_closed():
    args = fields()
    del args["metadata"]["uid"]
    with pytest.raises(ValueError):
        make_fixture_record(**args)
    args = fields()
    args["metadata"]["size_bytes"] = 99
    with pytest.raises(ValueError):
        make_fixture_record(**args)


def test_no_plaintext_in_serialized_record():
    secret_like_fixture = b"synthetic-private-payload-do-not-persist"
    entry = make_fixture_record(**fields(secret_like_fixture))
    assert secret_like_fixture.decode() not in str(entry)
    assert len(entry["content_sha256"]) == 64
    assert "source_ref" in entry and "owner_ref" in entry


def test_added_and_removed_and_duplicate_identity():
    a = build_index([record()], version=1)
    b = build_index([], version=2, previous=a)
    assert compare_indices(a, b)["removed"] == ["synthetic://case-01/safe/file.txt"]
    with pytest.raises(ValueError):
        build_index([record(), record()], version=1)
