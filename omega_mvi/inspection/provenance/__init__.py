"""Synthetic-only provenance and versioned SHA-256 index contracts.

No filesystem traversal, persistence, network access or authority is provided.
OMEGA-014's live scan remains blocked until separately verified owner scope.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping

SCHEMA_VERSION = "omega.synthetic-provenance.v1"
_ALLOWED_CLASSES = frozenset({"public", "internal", "confidential"})
_METADATA_FIELDS = frozenset({"kind", "size_bytes", "mtime_ns", "mode", "uid", "gid", "acl_sha256", "xattr_sha256"})
_HEX = frozenset("0123456789abcdef")
_SAFE_PART = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
_RECORD_FIELDS = frozenset({
    "schema_version", "source_ref", "relative_path", "source_version", "owner_ref",
    "access_level", "verified_at", "retention_days", "evidence_scope",
    "content_sha256", "metadata", "metadata_sha256", "record_sha256",
})
_INDEX_FIELDS = frozenset({
    "schema_version", "version", "previous_index_sha256", "entries", "index_sha256",
})
_MAX_RECORDS = 1000


def _safe_component(value: object, maximum: int) -> bool:
    return (type(value) is str and value not in (".", "..") and 0 < len(value) <= maximum
            and all(char in _SAFE_PART for char in value))


def _validate_identity(source_ref: object, relative_path: object,
                       source_version: object, owner_ref: object) -> None:
    if not isinstance(source_ref, str) or not source_ref.startswith("synthetic://"):
        raise PermissionError("synthetic fixture source required")
    source_name = source_ref[len("synthetic://"):]
    if (len(source_ref) > 256 or not source_name or source_name.startswith("/")
            or not all(_safe_component(part, 128) for part in source_name.split("/"))):
        raise PermissionError("untrusted synthetic fixture source")
    if (type(relative_path) is not str or len(relative_path) > 256
            or not relative_path or relative_path.startswith("/")
            or not all(_safe_component(part, 128) for part in relative_path.split("/"))):
        raise ValueError("unsafe fixture relative path")
    if not _safe_component(source_version, 128):
        raise ValueError("invalid source version")
    if (not isinstance(owner_ref, str) or not owner_ref.startswith("owner:")
            or not _safe_component(owner_ref[6:], 122)):
        raise ValueError("invalid opaque synthetic owner")


def _verified_at_utc(verified_at: object) -> str:
    try:
        if not isinstance(verified_at, str):
            raise ValueError("invalid verification timestamp")
        dt = datetime.fromisoformat(verified_at.replace("Z", "+00:00"))
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError("timezone required")
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError("timezone-aware ISO-8601 required") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in _HEX for c in value)


def normalize_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Reject absent/ambiguous metadata instead of silently ignoring drift."""
    if not isinstance(metadata, Mapping) or set(metadata) != _METADATA_FIELDS:
        raise ValueError("all eight known metadata fields are required")
    result = dict(metadata)
    if result["kind"] != "regular_file":
        raise ValueError("only regular-file synthetic fixtures are supported")
    for key in ("size_bytes", "mtime_ns", "mode", "uid", "gid"):
        if type(result[key]) is not int or result[key] < 0:
            raise ValueError("invalid metadata integer")
    if result["mode"] > 0o7777:
        raise ValueError("invalid mode")
    for key in ("acl_sha256", "xattr_sha256"):
        if not _is_sha256(result[key]):
            raise ValueError("verified ACL/xattr digest mandatory; unknown means BLOCKED")
    return result


def make_fixture_record(*, source_ref: str, relative_path: str, source_version: str,
                        data: bytes, metadata: Mapping[str, Any], owner_ref: str,
                        access_level: str, verified_at: str, retention_days: int) -> dict[str, Any]:
    """Hash only caller-supplied synthetic data. Never read a path or persist bytes."""
    _validate_identity(source_ref, relative_path, source_version, owner_ref)
    if type(data) is not bytes:
        raise ValueError("fixture must be bytes")
    if len(data) > 1024 * 1024:
        raise ValueError("fixture too large")
    if access_level not in _ALLOWED_CLASSES:
        raise PermissionError("restricted/unknown data must never enter this index")
    if type(retention_days) is not int or not 1 <= retention_days <= 3650:
        raise ValueError("explicit bounded retention is required")
    canonical = _verified_at_utc(verified_at)
    meta = normalize_metadata(metadata)
    if meta["size_bytes"] != len(data):
        raise ValueError("metadata size does not match the fixture")
    record = {
        "schema_version": SCHEMA_VERSION,
        "source_ref": source_ref,
        "relative_path": relative_path,
        "source_version": source_version,
        "owner_ref": owner_ref,
        "access_level": access_level,
        "verified_at": canonical,
        "retention_days": retention_days,
        "evidence_scope": "synthetic_fixture_only_not_owner_device",
        "content_sha256": hashlib.sha256(data).hexdigest(),
        "metadata": meta,
        "metadata_sha256": _digest(meta),
    }
    record["record_sha256"] = _digest(record)
    return record


def _validate_record(record: dict[str, Any]) -> None:
    """Validate all caller-controlled fields, not only their recomputable hash."""
    if type(record) is not dict or set(record) != _RECORD_FIELDS:
        raise ValueError("invalid provenance schema")
    try:
        _validate_identity(record["source_ref"], record["relative_path"],
                           record["source_version"], record["owner_ref"])
        if (record["schema_version"] != SCHEMA_VERSION
                or record["evidence_scope"] != "synthetic_fixture_only_not_owner_device"
                or record["access_level"] not in _ALLOWED_CLASSES
                or type(record["retention_days"]) is not int
                or not 1 <= record["retention_days"] <= 3650
                or record["verified_at"] != _verified_at_utc(record["verified_at"])
                or not _is_sha256(record["content_sha256"])):
            raise ValueError("invalid provenance field")
        meta = normalize_metadata(record["metadata"])
        if record["metadata"] != meta or record["metadata_sha256"] != _digest(meta):
            raise ValueError("invalid metadata integrity")
    except (PermissionError, TypeError, ValueError) as exc:
        raise ValueError("invalid provenance record") from exc
    canonical = dict(record)
    digest = canonical.pop("record_sha256")
    if not _is_sha256(digest) or digest != _digest(canonical):
        raise ValueError("provenance integrity mismatch")


def build_index(records: list[dict[str, Any]], *, version: int,
                previous: dict[str, Any] | None = None) -> dict[str, Any]:
    """Immutable-by-value version chain. Version is a caller-controlled sequence."""
    if type(version) is not int or version < 1:
        raise ValueError("version must be a positive integer")
    if previous is None and version != 1:
        raise ValueError("genesis index must start at version 1")
    if previous is not None:
        _validate_index(previous)
        if version != previous["version"] + 1:
            raise ValueError("version must increment exactly once")
    if type(records) is not list or len(records) > _MAX_RECORDS:
        raise ValueError("synthetic fixture record count limit exceeded")
    items = {}
    for record in records:
        _validate_record(record)
        key = record["source_ref"] + "/" + record["relative_path"]
        if key in items:
            raise ValueError("duplicate source/path")
        items[key] = json.loads(json.dumps(record, ensure_ascii=False))
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "version": version,
        "previous_index_sha256": previous["index_sha256"] if previous else None,
        "entries": dict(sorted(items.items())),
    }
    snapshot["index_sha256"] = _digest(snapshot)
    return snapshot


def _validate_index(index: dict[str, Any]) -> None:
    if (type(index) is not dict or set(index) != _INDEX_FIELDS
            or index["schema_version"] != SCHEMA_VERSION
            or type(index["version"]) is not int or index["version"] < 1):
        raise ValueError("invalid index schema or version")
    prior = index["previous_index_sha256"]
    if (index["version"] == 1 and prior is not None) or (
            index["version"] > 1 and not _is_sha256(prior)):
        raise ValueError("invalid genesis/previous index link")
    entries = index["entries"]
    if type(entries) is not dict or len(entries) > _MAX_RECORDS:
        raise ValueError("invalid index entries")
    for key, record in entries.items():
        _validate_record(record)
        if key != record["source_ref"] + "/" + record["relative_path"]:
            raise ValueError("record identity mismatch")
    canonical = dict(index)
    actual_hash = canonical.pop("index_sha256")
    if not _is_sha256(actual_hash) or actual_hash != _digest(canonical):
        raise ValueError("index integrity mismatch")


def compare_indices(old: dict[str, Any], new: dict[str, Any]) -> dict[str, list[str]]:
    _validate_index(old)
    _validate_index(new)
    if new["version"] != old["version"] + 1 or new["previous_index_sha256"] != old["index_sha256"]:
        raise ValueError("broken version chain")
    a, b = old["entries"], new["entries"]
    both = sorted(a.keys() & b.keys())
    return {
        "added": sorted(b.keys() - a.keys()),
        "removed": sorted(a.keys() - b.keys()),
        "content_changed": [k for k in both if a[k]["content_sha256"] != b[k]["content_sha256"]],
        "metadata_changed": [k for k in both if a[k]["metadata_sha256"] != b[k]["metadata_sha256"]],
        "provenance_changed": [k for k in both if any(a[k][v] != b[k][v] for v in
                              ("source_version", "owner_ref", "access_level", "verified_at", "retention_days"))],
    }


def verify_index_chain(snapshots: list[dict[str, Any]], *,
                       expected_genesis_sha256: str,
                       expected_tip_sha256: str) -> dict[str, Any]:
    """Verify a bounded complete, externally anchored synthetic index history.

    The caller MUST acquire both expected hashes through an independently
    trusted channel. A self-supplied hash (from the same untrusted input)
    is not an authentication mechanism. No filesystem or network reads occur.
    """
    if (type(snapshots) is not list or not 1 <= len(snapshots) <= 128
            or not _is_sha256(expected_genesis_sha256)
            or not _is_sha256(expected_tip_sha256)):
        raise ValueError("a bounded history and two trusted SHA-256 anchors are required")
    previous = None
    for number, snapshot in enumerate(snapshots, 1):
        _validate_index(snapshot)
        if snapshot["version"] != number:
            raise ValueError("index history has a missing, replayed or reordered version")
        if number == 1:
            if snapshot["index_sha256"] != expected_genesis_sha256:
                raise ValueError("genesis differs from trusted anchor")
        elif snapshot["previous_index_sha256"] != previous["index_sha256"]:
            raise ValueError("index history contains a broken link")
        previous = snapshot
    if previous["index_sha256"] != expected_tip_sha256:
        raise ValueError("tip differs from trusted anchor or history is truncated")
    return {
        "schema_version": SCHEMA_VERSION,
        "history_validated": True,
        "snapshot_count": len(snapshots),
        "genesis_sha256": expected_genesis_sha256,
        "tip_sha256": expected_tip_sha256,
        "authorization_granted": False,
        "signed_identity_verified": False,
    }
