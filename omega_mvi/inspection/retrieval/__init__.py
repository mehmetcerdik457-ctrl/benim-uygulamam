"""Deterministic retrieval over synthetic OMEGA inspection fixtures."""

from dataclasses import dataclass
import re


class SecretInputError(ValueError):
    """Raised when an input appears to contain a credential or private key."""


@dataclass(frozen=True)
class RetrievalResult:
    text: str
    source_ref: str
    score: int


@dataclass(frozen=True)
class _FixtureDocument:
    owner_id: str
    text: str
    source_ref: str


_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{12,}|github_pat_[A-Za-z0-9_]{12,})\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{30,}\b"),
    re.compile(
        r"""(?i)\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|token|password|passwd|secret|client[_-]?secret|authorization)\b\s*["']?\s*[:=]\s*["']?[^\s"'`,;]{4,}"""
    ),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{8,}"),
)
_WORD_PATTERN = re.compile(r"[a-z0-9]+")
_FIXTURE_OWNER = "synthetic-owner"
_FIXTURE_DOCUMENTS = (
    _FixtureDocument(
        owner_id=_FIXTURE_OWNER,
        text=(
            "Synthetic fixture: owner authorization is required before retrieval. "
            "Unknown permissions are denied."
        ),
        source_ref="synthetic://omega-fixtures/owner-controls.md#access",
    ),
    _FixtureDocument(
        owner_id=_FIXTURE_OWNER,
        text=(
            "Synthetic fixture: citations preserve the exact source reference "
            "of each retrieved document."
        ),
        source_ref="synthetic://omega-fixtures/provenance.md#citations",
    ),
    _FixtureDocument(
        owner_id=_FIXTURE_OWNER,
        text=(
            "Synthetic fixture: secret-bearing input is rejected, and secret "
            "values are never indexed."
        ),
        source_ref="synthetic://omega-fixtures/privacy.md#secrets",
    ),
)


def _contains_secret(value: str) -> bool:
    return any(pattern.search(value) for pattern in _SECRET_PATTERNS)


def _words(value: str) -> set[str]:
    return set(_WORD_PATTERN.findall(value.casefold()))


class SyntheticRetriever:
    """Search fixed synthetic fixtures after verifying the requesting owner."""

    def __init__(self, owner_id: str):
        if not isinstance(owner_id, str) or not owner_id.strip():
            raise ValueError("OWNER_REQUIRED")
        if _contains_secret(owner_id):
            raise SecretInputError("SECRET_INPUT_REJECTED")
        self._owner_id = owner_id

    def retrieve(
        self, query: str, *, requester_id: str, limit: int = 5
    ) -> tuple[RetrievalResult, ...]:
        if not isinstance(requester_id, str) or requester_id != self._owner_id:
            raise PermissionError("OWNER_ACCESS_REQUIRED")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("QUERY_REQUIRED")
        if _contains_secret(query):
            raise SecretInputError("SECRET_INPUT_REJECTED")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("INVALID_RESULT_LIMIT")

        query_words = _words(query)
        ranked = []
        for position, document in enumerate(_FIXTURE_DOCUMENTS):
            if document.owner_id != requester_id:
                continue
            score = len(query_words & _words(document.text))
            if score:
                ranked.append((score, position, document))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return tuple(
            RetrievalResult(
                text=document.text,
                source_ref=document.source_ref,
                score=score,
            )
            for score, _, document in ranked[:limit]
        )
