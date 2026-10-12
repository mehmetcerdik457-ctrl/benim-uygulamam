"""Offline synthetic tests; never touch owner disks or external services."""
import copy
import hashlib
import pytest
from omega_mvi.inspection.provenance import make_fixture_record, build_index, compare_indices, verify_index_chain, _digest


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


def _anchored_history():
    first = build_index([record()], version=1)
    second = build_index([record(b"world")], version=2, previous=first)
    third = build_index([], version=3, previous=second)
    return first, second, third


def test_full_history_matches_independent_genesis_and_tip():
    a, b, c = _anchored_history()
    result = verify_index_chain([a, b, c],
                                expected_genesis_sha256=a["index_sha256"],
                                expected_tip_sha256=c["index_sha256"])
    assert result["history_validated"] is True
    assert result["snapshot_count"] == 3
    assert result["authorization_granted"] is False
    assert result["signed_identity_verified"] is False


@pytest.mark.parametrize("history_indices", [[0, 2], [1, 2], [0, 1], [0, 1, 1], [2, 1, 0], [0, 2, 1]])
def test_history_reordered_truncated_or_replayed_fails(history_indices):
    history = _anchored_history()
    with pytest.raises(ValueError):
        verify_index_chain([history[i] for i in history_indices],
                            expected_genesis_sha256=history[0]["index_sha256"],
                            expected_tip_sha256=history[-1]["index_sha256"])


def test_history_rewritten_with_recomputed_hashes_fails_trusted_tip():
    a, b, c = _anchored_history()
    forged = copy.deepcopy(b)
    entry = forged["entries"]["synthetic://case-01/safe/file.txt"]
    entry["owner_ref"] = "owner:changed"
    unsigned = dict(entry)
    unsigned.pop("record_sha256")
    entry["record_sha256"] = _digest(unsigned)
    unsigned_index = dict(forged)
    unsigned_index.pop("index_sha256")
    forged["index_sha256"] = _digest(unsigned_index)
    # Both hashes can be recomputed by the attacker, but no independent
    # trusted final anchor can be produced by this module.
    with pytest.raises(ValueError):
        verify_index_chain([a, forged, c],
                            expected_genesis_sha256=a["index_sha256"],
                            expected_tip_sha256=c["index_sha256"])


@pytest.mark.parametrize("anchors", [
    ("missing", "0" * 64), ("a" * 64, "missing"),
    (None, "0" * 64), ("0" * 64, None),
])
def test_history_rejects_missing_or_bad_anchor(anchors):
    a, b, c = _anchored_history()
    with pytest.raises(ValueError):
        verify_index_chain([a, b, c],
                            expected_genesis_sha256=anchors[0],
                            expected_tip_sha256=anchors[1])


def test_history_rejects_empty_non_list_or_oversized():
    a, b, c = _anchored_history()
    for snapshots in ([], (a, b, c), [a] * 129):
        with pytest.raises(ValueError):
            verify_index_chain(snapshots,
                               expected_genesis_sha256=a["index_sha256"],
                               expected_tip_sha256=c["index_sha256"])


def test_history_rejects_forged_chain_version_even_with_recomputed_hash():
    a, b, c = _anchored_history()
    altered = copy.deepcopy(b)
    altered["version"] = 4
    unsigned = dict(altered)
    unsigned.pop("index_sha256")
    altered["index_sha256"] = _digest(unsigned)
    with pytest.raises(ValueError):
        verify_index_chain([a, altered, c],
                            expected_genesis_sha256=a["index_sha256"],
                            expected_tip_sha256=c["index_sha256"])
