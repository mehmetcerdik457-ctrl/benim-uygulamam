"""Offline, synthetic-only knowledge safety primitives. Not a production IdP or RAG."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
from typing import Iterable

from omega_mvi.inspection.redaction import redact_text


class ScopeError(PermissionError):
    """Fail-closed access or approval denial, with no user data in messages."""


@dataclass(frozen=True)
class DocumentChange:
    source_ref: str
    document_id: str
    revision: str
    text: str


@dataclass(frozen=True)
class SearchHit:
    source_ref: str
    document_id: str
    revision: str
    text: str
    score: int


@dataclass(frozen=True)
class ScanOutcome:
    added: int = 0
    updated: int = 0
    unchanged: int = 0


_WORDS = re.compile(r"[a-z0-9]+")


def _terms(value: str) -> set[str]:
    return set(_WORDS.findall(value.casefold()))


class ControlledIndex:
    """In-memory fixture index; no filesystem, external access, DB or backup purge.

    Callers must supply an explicit, allowlisted synthetic source snapshot. Changes
    are atomic (validated before commit), and revoked/tombstoned identities NEVER
    reappear during scans, even when another identity has the same content.
    This is a *logical* barrier, not secure erasure or retroactive LLM forgetting.
    """

    def __init__(self, *, owner_id: str, allowlisted_sources: Iterable[str]):
        if not isinstance(owner_id, str) or not owner_id.strip():
            raise ValueError("OWNER_REQUIRED")
        sources = tuple(allowlisted_sources)
        if not sources or any(
            not isinstance(s, str) or not s.startswith("synthetic://") or
            not re.fullmatch(r"synthetic://[A-Za-z0-9/_.-]{1,150}", s) for s in sources
        ):
            raise ValueError("SYNTHETIC_SCOPE_REQUIRED")
        self._owner = owner_id
        self._allowed = frozenset(sources)
        self._records: dict[tuple[str, str], tuple[str, str, str]] = {}
        self._revoked_sources: set[str] = set()
        self._deleted_ids: set[tuple[str, str]] = set()
        self._deleted_fingerprints: dict[str, set[str]] = {}
        self._generation = 0

    @property
    def generation(self) -> int:
        """Monotonic number for caller-side context-cache invalidation."""
        return self._generation

    def _authorized(self, requester_id: str) -> None:
        # A matching ID string is a test-only stand-in, NEVER proof of identity.
        if type(requester_id) is not str or requester_id != self._owner:
            raise ScopeError("OWNER_ACCESS_REQUIRED")

    def _source_allowed(self, source_ref: str) -> None:
        if source_ref not in self._allowed:
            raise ScopeError("SOURCE_NOT_ALLOWED")
        if source_ref in self._revoked_sources:
            raise ScopeError("SOURCE_REVOKED")

    def rescan(self, changes: Iterable[DocumentChange], *, requester_id: str,
               approved: bool = False) -> ScanOutcome:
        self._authorized(requester_id)
        if approved is not True:
            raise ScopeError("SCAN_APPROVAL_REQUIRED")
        changes = tuple(changes)
        if len(changes) > 1000:
            raise ValueError("SCAN_BATCH_TOO_LARGE")
        staged: dict[tuple[str, str], tuple[str, str, str]] = {}
        seen: set[tuple[str, str]] = set()
        for item in changes:
            if not isinstance(item, DocumentChange):
                raise ValueError("INVALID_CHANGE")
            self._source_allowed(item.source_ref)
            if not all(type(field) is str and field.strip() for field in
                       (item.document_id, item.revision, item.text)):
                raise ValueError("INVALID_CHANGE")
            if any(len(field) > 200 for field in
                   (item.document_id, item.revision)) or len(item.text) > 100_000:
                raise ValueError("SCAN_LIMIT_EXCEEDED")
            # This synthetic service never indexes secret-like or PII-bearing data.
            if redact_text(item.text) != item.text:
                raise ValueError("SENSITIVE_CONTENT_REJECTED")
            key = (item.source_ref, item.document_id)
            if key in seen:
                raise ValueError("DUPLICATE_ID_IN_SCAN")
            seen.add(key)
            digest = sha256(item.text.encode("utf-8")).hexdigest()
            if key in self._deleted_ids or digest in self._deleted_fingerprints.get(item.source_ref, set()):
                raise ScopeError("TOMBSTONE_DENIED")
            staged[key] = (item.revision, item.text, digest)
        added = updated = unchanged = 0
        for key, record in staged.items():
            prior = self._records.get(key)
            if prior is None:
                added += 1
            elif prior == record:
                unchanged += 1
            else:
                updated += 1
        if added or updated:
            self._records.update(staged)
            self._generation += 1
        return ScanOutcome(added, updated, unchanged)

    def delete_document(self, source_ref: str, document_id: str, *, requester_id: str,
                        approved: bool = False) -> None:
        self._authorized(requester_id)
        if approved is not True:
            raise ScopeError("DELETE_APPROVAL_REQUIRED")
        if source_ref not in self._allowed:
            raise ScopeError("SOURCE_NOT_ALLOWED")
        key = (source_ref, document_id)
        prior = self._records.pop(key, None)
        self._deleted_ids.add(key)
        if prior is not None:
            self._deleted_fingerprints.setdefault(source_ref, set()).add(prior[2])
        self._generation += 1

    def revoke_source(self, source_ref: str, *, requester_id: str,
                      approved: bool = False) -> None:
        self._authorized(requester_id)
        if approved is not True:
            raise ScopeError("REVOCATION_APPROVAL_REQUIRED")
        if source_ref not in self._allowed:
            raise ScopeError("SOURCE_NOT_ALLOWED")
        self._revoked_sources.add(source_ref)
        for key in list(self._records):
            if key[0] == source_ref:
                self._records.pop(key)
                self._deleted_ids.add(key)
        self._generation += 1

    def is_active(self, source_ref: str, document_id: str, *, requester_id: str) -> bool:
        self._authorized(requester_id)
        return source_ref in self._allowed and source_ref not in self._revoked_sources and (
            source_ref, document_id) in self._records

    def search(self, query: str, *, requester_id: str, limit: int = 5) -> tuple[SearchHit, ...]:
        self._authorized(requester_id)
        if type(query) is not str or not query.strip():
            raise ValueError("QUERY_REQUIRED")
        if redact_text(query) != query:
            raise ValueError("SENSITIVE_QUERY_REJECTED")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("INVALID_LIMIT")
        terms = _terms(query)
        results = []
        for (source, identity), (revision, contents, _) in self._records.items():
            if source in self._revoked_sources:
                continue
            score = len(terms & _terms(contents))
            if score:
                results.append(SearchHit(source, identity, revision, contents, score))
        return tuple(sorted(results, key=lambda r: (-r.score, r.source_ref, r.document_id))[:limit])

    def context(self, query: str, *, requester_id: str) -> tuple[str, ...]:
        """New, access-checked context each call; no persistent LLM cache."""
        return tuple(hit.text for hit in self.search(query, requester_id=requester_id))


_ALLOWED_STATES = frozenset(("unverified_suggestion", "approved_fact", "tested_solution"))


@dataclass(frozen=True)
class MemoryEntry:
    entry_id: str
    source_ref: str
    document_id: str
    statement: str
    state: str
    evidence_ref: str | None = None
    approver_id: str | None = None


class MemoryLedger:
    """Provenance-bound, opt-in trust classification; never model training."""

    def __init__(self, index: ControlledIndex):
        self._index = index
        self._entries: dict[str, MemoryEntry] = {}

    def record_suggestion(self, entry: MemoryEntry, *, requester_id: str) -> None:
        if entry.state != "unverified_suggestion" or entry.evidence_ref or entry.approver_id:
            raise ValueError("NEW_MEMORY_MUST_BE_UNVERIFIED")
        if not entry.entry_id or not entry.statement or entry.entry_id in self._entries:
            raise ValueError("INVALID_ENTRY")
        if redact_text(entry.statement) != entry.statement:
            raise ValueError("SENSITIVE_MEMORY_REJECTED")
        if not self._index.is_active(entry.source_ref, entry.document_id,
                                     requester_id=requester_id):
            raise ScopeError("SOURCE_NOT_ACTIVE")
        self._entries[entry.entry_id] = entry

    def promote(self, entry_id: str, *, requester_id: str, new_state: str,
                approver_id: str, evidence_ref: str) -> None:
        self._index._authorized(requester_id)
        if new_state not in ("approved_fact", "tested_solution"):
            raise ValueError("INVALID_TRUST_TRANSITION")
        if type(approver_id) is not str or not approver_id.strip() or (
            type(evidence_ref) is not str or not evidence_ref.startswith("synthetic://")
            or not re.fullmatch(r"synthetic://[A-Za-z0-9/_.-]{1,150}", evidence_ref)
        ):
            raise ValueError("APPROVAL_EVIDENCE_REQUIRED")
        record = self._entries.get(entry_id)
        if record is None:
            raise KeyError("MEMORY_NOT_FOUND")
        if not self._index.is_active(record.source_ref, record.document_id,
                                     requester_id=requester_id):
            raise ScopeError("SOURCE_NOT_ACTIVE")
        if record.state == "tested_solution" or (record.state == "approved_fact" and new_state != "tested_solution"):
            raise ValueError("INVALID_TRUST_TRANSITION")
        if new_state == "tested_solution" and record.state != "approved_fact":
            raise ValueError("FACT_APPROVAL_REQUIRED")
        # The approver_id is metadata, not cryptographic identity verification.
        self._entries[entry_id] = MemoryEntry(record.entry_id, record.source_ref,
                                             record.document_id, record.statement,
                                             new_state, evidence_ref, approver_id)

    def trusted_context(self, *, requester_id: str) -> tuple[MemoryEntry, ...]:
        self._index._authorized(requester_id)
        return tuple(e for e in self._entries.values()
                     if e.state in ("approved_fact", "tested_solution")
                     and self._index.is_active(e.source_ref, e.document_id,
                                               requester_id=requester_id))

    def inspect(self, *, requester_id: str) -> tuple[MemoryEntry, ...]:
        self._index._authorized(requester_id)
        # Inactive entries are quarantined from all public-facing memory views.
        return tuple(e for e in self._entries.values()
                     if self._index.is_active(e.source_ref, e.document_id,
                                               requester_id=requester_id))
