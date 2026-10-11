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
        if result[key] is not None and not _is_sha256(result[key]):
            raise ValueError("invalid metadata digest")
    return result


def make_fixture_record(*, source_ref: str, relative_path: str, source_version: str,
                        data: bytes, metadata: Mapping[str, Any], owner_ref: str,
                        access_level: str, verified_at: str, retention_days: int) -> dict[str, Any]:
    """Hash only caller-supplied synthetic data. Never read a path or persist bytes."""
    if not isinstance(source_ref, str) or not source_ref.startswith("synthetic://") or len(source_ref) > 256:
        raise PermissionError("live source not authorized; synthetic fixture only")
    if not isinstance(relative_path, str) or (not relative_path or len(relative_path) > 256
          or relative_path.startswith("/") or "\\" in relative_path
          or any(p in ("", ".", "..") for p in relative_path.split("/"))):
        raise ValueError("invalid relative path")
    if type(data) is not bytes:
        raise ValueError("fixture must be bytes")
    if len(data) > 1024 * 1024:
        raise ValueError("fixture too large")
    if not source_version or not isinstance(source_version, str) or len(source_version) > 128:
        raise ValueError("source version is required")
    if not owner_ref or not isinstance(owner_ref, str) or len(owner_ref) > 128:
        raise ValueError("opaque owner reference required")
    if access_level not in _ALLOWED_CLASSES:
        raise PermissionError("restricted/unknown data must never enter this index")
    if type(retention_days) is not int or not 1 <= retention_days <= 3650:
        raise ValueError("explicit bounded retention is required")
    try:
        dt = datetime.fromisoformat(verified_at.replace("Z", "+00:00"))
    except (TypeError, AttributeError, ValueError) as exc:
        raise ValueError("verified_at must be timezone-aware ISO-8601") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("verified_at must be timezone-aware")
    canonical = dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
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
    if (not isinstance(record, dict) or record.get("schema_version") != SCHEMA_VERSION
            or record.get("evidence_scope") != "synthetic_fixture_only_not_owner_device"
            or not str(record.get("source_ref", "")).startswith("synthetic://")
            or record.get("access_level") not in _ALLOWED_CLASSES
            or not _is_sha256(record.get("content_sha256"))
            or normalize_metadata(record.get("metadata")) != record.get("metadata")
            or record.get("metadata_sha256") != _digest(record["metadata"])):
        raise ValueError("invalid provenance record")
    canonical = dict(record)
    digest = canonical.pop("record_sha256", None)
    if not _is_sha256(digest) or digest != _digest(canonical):
        raise ValueError("provenance integrity mismatch")


def build_index(records: list[dict[str, Any]], *, version: int,
                previous: dict[str, Any] | None = None) -> dict[str, Any]:
    """Immutable-by-value version chain. Version is a caller-controlled sequence."""
    if type(version) is not int or version < 1:
        raise ValueError("version must be a positive integer")
    if previous is not None:
        _validate_index(previous)
        if version != previous["version"] + 1:
            raise ValueError("version must increment exactly once")
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
    if not isinstance(index, dict) or index.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("invalid index")
    canonical = dict(index)
    actual_hash = canonical.pop("index_sha256", None)
    if not _is_sha256(actual_hash) or actual_hash != _digest(canonical):
        raise ValueError("index integrity mismatch")
    if not isinstance(index.get("entries"), dict):
        raise ValueError("invalid entries")
    for key, record in index["entries"].items():
        _validate_record(record)
        if key != record["source_ref"] + "/" + record["relative_path"]:
            raise ValueError("record identity mismatch")


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
