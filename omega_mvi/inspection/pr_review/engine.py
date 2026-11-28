"""Offline, advisory review of sanitized changed-file summaries."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
import re


@dataclass(frozen=True)
class Citation:
    path: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class Finding:
    category: str
    title: str
    guidance: str
    citation: Citation


@dataclass(frozen=True)
class ReviewReport:
    findings: tuple[Finding, ...]
    advisory_only: bool = True
    approval_authority: bool = False


_RULES = (
    (
        "security",
        "Review sensitive-data handling",
        "Confirm credentials and secret values are not exposed in prompts, logs, reports, or persistence.",
        re.compile(r"\b(?:secret|token|password|credential|api[ -]?key|private[ -]?key)\b", re.I),
    ),
    (
        "authorization",
        "Review authorization boundaries",
        "Verify access checks deny unknown or out-of-scope permissions.",
        re.compile(r"\b(?:authori[sz]ation|permission|access control|acl|scope)\b", re.I),
    ),
    (
        "input_validation",
        "Review input validation",
        "Check malformed and untrusted input is rejected safely.",
        re.compile(r"\b(?:input validation|validate|validation|sanitize|parse|deserialize)\b", re.I),
    ),
    (
        "reliability",
        "Review failure handling",
        "Check error, timeout, and retry paths remain bounded and observable.",
        re.compile(r"\b(?:exception|error handling|retry|timeout|failure)\b", re.I),
    ),
    (
        "concurrency",
        "Review concurrent behavior",
        "Check shared state and ordering remain safe under concurrent operations.",
        re.compile(r"\b(?:concurren(?:t|cy)|race condition|locking|thread.safe)\b", re.I),
    ),
)


def _validate_changed_file(item: object) -> tuple[str, str, Citation]:
    if not isinstance(item, Mapping):
        raise ValueError("Each changed-file summary must be a mapping.")
    if set(item) != {"path", "sanitized_summary", "start_line", "end_line"}:
        raise ValueError("Changed-file summaries must use only the supported fields.")

    path = item.get("path")
    summary = item.get("sanitized_summary")
    start_line = item.get("start_line")
    end_line = item.get("end_line")
    if not isinstance(path, str) or not path or len(path) > 500:
        raise ValueError("A repository-relative file path is required.")
    parsed_path = PurePosixPath(path)
    if (
        path.startswith("/")
        or "\\" in path
        or any(part in {".", ".."} for part in path.split("/"))
        or str(parsed_path) != path
        or any(ord(char) < 32 for char in path)
    ):
        raise ValueError("File paths must be normalized and repository-relative.")
    if not isinstance(summary, str) or not summary.strip() or len(summary) > 4000:
        raise ValueError("A non-empty sanitized summary of at most 4000 characters is required.")
    if (
        type(start_line) is not int
        or type(end_line) is not int
        or start_line < 1
        or end_line < start_line
    ):
        raise ValueError("A valid one-based line span is required.")
    return path, summary, Citation(path, start_line, end_line)


def review_changed_files(
    changed_files: Iterable[Mapping[str, object]],
) -> ReviewReport:
    """Create advisory findings without accessing repositories or external services.

    Each item must contain `path`, `sanitized_summary`, `start_line`, and
    `end_line`. The supplied span is used verbatim as the citation; no source
    files or raw diffs are read.
    """
    if isinstance(changed_files, (str, bytes, Mapping)):
        raise ValueError("Changed files must be an iterable of sanitized summaries.")

    validated = [_validate_changed_file(item) for item in changed_files]
    findings = tuple(
        Finding(category, title, guidance, citation)
        for _, summary, citation in validated
        for category, title, guidance, pattern in _RULES
        if pattern.search(summary)
    )
    return ReviewReport(findings=findings)
