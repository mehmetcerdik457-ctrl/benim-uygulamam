"""Fixed offline inspection pipeline. Output cannot grant authority."""
from dataclasses import asdict
from omega_mvi.inspection.github_inventory import inventory_from_public_metadata_fixture, TARGET_REPOSITORY
from omega_mvi.inspection.redaction import redact_text
from omega_mvi.inspection.retrieval import SyntheticRetriever
from omega_mvi.inspection.pr_review import review_changed_files

PUBLIC_FIXTURE = {
    "full_name": TARGET_REPOSITORY, "name": "benim-uygulamam",
    "visibility": "public", "private": False,
    "description": "Synthetic offline repository fixture",
    "stargazers_count": 0, "forks_count": 0,
    "watchers_count": 0, "open_issues_count": 0,
}

def inspect_offline_fixture():
    """Exercise ALL four modules in sequence, never a user-controlled input."""
    repository = inventory_from_public_metadata_fixture(dict(PUBLIC_FIXTURE))
    # Public repository metadata can contain copied credentials or PII.
    # Sanitize before the result is passed to HTTP or downstream models.
    description = repository.get("description")
    if description is not None:
        sanitized = redact_text(description)
        if not isinstance(sanitized, str):
            raise PermissionError("REDACTION_FAILED")
        repository["description"] = sanitized
    # Redact BEFORE passing a summary to the advisory review engine.
    redacted = redact_text("Review authorization scope and synthetic " +
                           "Bearer " + "synthetic-opaque-value")
    if "synthetic-opaque-value" in redacted:
        raise PermissionError("REDACTION_FAILED")
    retriever = SyntheticRetriever(owner_id="synthetic-owner")
    sources = retriever.retrieve("citations source reference",
                                 requester_id="synthetic-owner", limit=2)
    if not sources or any(not x.source_ref.startswith("synthetic://") for x in sources):
        raise PermissionError("CITED_RETRIEVAL_FAILED")
    report = review_changed_files([{
        "path": "synthetic/fixture.py",
        "sanitized_summary": "Review authorization scope after validation",
        "start_line": 1, "end_line": 2,
    }])
    return {
        "mode": "synthetic_offline_only",
        "repository": repository,
        "redaction_applied": "[REDACTED_CREDENTIAL]" in redacted,
        "sources": [{"ref": item.source_ref, "score": item.score} for item in sources],
        "review": [{"category": item.category,
                    "source_path": item.citation.path,
                    "line_start": item.citation.start_line,
                    "line_end": item.citation.end_line} for item in report.findings],
        "authority": "none",
        "production_ready": False,
    }
