"""Offline synthetic tests; never touch owner disks or external services."""
import copy
import hashlib
import pytest
from omega_mvi.inspection.provenance import make_fixture_record, build_index, compare_indices, _digest


def fields(data=b"hello", **overrides):
    metadata = dict(kind="regular_file", size_bytes=len(data), mtime_ns=100,
                    mode=0o600, uid=1000, gid=1000, acl_sha256=hashlib.sha256(b"").hexdigest(),
                    xattr_sha256=hashlib.sha256(b"").hexdigest())
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


def test_orphan_version_or_restarted_genesis_rejected():
    with pytest.raises(ValueError):
        build_index([record()], version=2)
    genesis = build_index([record()], version=1)
    with pytest.raises(ValueError):
        build_index([record()], version=1, previous=genesis)


def test_unknown_acl_and_xattr_fail_closed():
    for key in ("acl_sha256", "xattr_sha256"):
        args = fields()
        args["metadata"][key] = None
        with pytest.raises(ValueError, match="ACL/xattr"):
            make_fixture_record(**args)
    args = fields()
    args["metadata"]["mode"] = True
    with pytest.raises(ValueError):
        make_fixture_record(**args)


@pytest.mark.parametrize("path", ["a\nb", "a\x00b", "a?b", "a/b/../c", "a/./c", "a//b"])
def test_malformed_synthetic_paths_rejected(path):
    args = fields()
    args["relative_path"] = path
    with pytest.raises(ValueError):
        make_fixture_record(**args)


@pytest.mark.parametrize("owner", ["owner:", "owner:sensitive email@example.net", "not-owner", None])
def test_opaque_owner_ref_rejected(owner):
    args = fields()
    args["owner_ref"] = owner
    with pytest.raises(ValueError):
        make_fixture_record(**args)


@pytest.mark.parametrize("timestamp", ["2026-10-11T10:00:00", "not-a-time", "", None])
def test_verification_requires_real_timezone(timestamp):
    args = fields()
    args["verified_at"] = timestamp
    with pytest.raises(ValueError):
        make_fixture_record(**args)


@pytest.mark.parametrize("name,value", [
    ("relative_path", "../private"),
    ("source_ref", "synthetic://../../escaped"),
    ("source_version", "../bad"),
    ("owner_ref", "owner:"),
    ("retention_days", True),
    ("retention_days", -1),
    ("access_level", "restricted"),
    ("verified_at", "2026-10-11T10:00:00"),
])
def test_recomputed_hash_cannot_legalize_bad_fixture_field(name, value):
    forged = record()
    forged[name] = value
    tmp = dict(forged)
    tmp.pop("record_sha256")
    forged["record_sha256"] = _digest(tmp)
    with pytest.raises(ValueError):
        build_index([forged], version=1)


def test_recomputed_hash_cannot_legalize_extra_field():
    forged = record()
    forged["unexpected"] = "ignored-by-some-consumers"
    tmp = dict(forged)
    tmp.pop("record_sha256")
    forged["record_sha256"] = _digest(tmp)
    with pytest.raises(ValueError):
        build_index([forged], version=1)


def test_tampered_genesis_index_rehashed_still_rejected():
    original = build_index([record()], version=1)
    forged = copy.deepcopy(original)
    forged["version"] = 2
    forged["previous_index_sha256"] = None
    tmp = dict(forged)
    tmp.pop("index_sha256")
    forged["index_sha256"] = _digest(tmp)
    with pytest.raises(ValueError):
        compare_indices(forged, original)


def test_verified_utc_timestamp_canonicalized():
    args = fields()
    args["verified_at"] = "2026-10-11T13:00:00+03:00"
    assert make_fixture_record(**args)["verified_at"] == "2026-10-11T10:00:00Z"


def test_synthetic_record_count_limit_and_data_limit():
    args = fields(b"x" * (1024 * 1024 + 1))
    with pytest.raises(ValueError):
        make_fixture_record(**args)
    with pytest.raises(ValueError):
        build_index([record()] * 1001, version=1)
