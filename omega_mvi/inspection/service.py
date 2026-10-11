"""Safe one-screen read-only synthetic inspection; no caller identity or network."""
from omega_mvi.inspection.github_inventory import (
    TARGET_REPOSITORY, inventory_from_public_metadata_fixture,
)
from omega_mvi.inspection.redaction import redact_text
from omega_mvi.inspection.retrieval import SyntheticRetriever
from omega_mvi.inspection.pr_review import review_changed_files


def build_synthetic_snapshot():
    """Run the four offline modules together on explicitly fake input only."""
    public_fixture = {
        "full_name": TARGET_REPOSITORY,
        "name": TARGET_REPOSITORY.split("/", 1)[1],
        "private": False,
        "visibility": "public",
        "description": "SYNTHETIC FIXTURE; NOT CURRENT GITHUB STATE",
        "stargazers_count": 0, "forks_count": 0,
        "watchers_count": 0, "open_issues_count": 0,
    }
    inventory = inventory_from_public_metadata_fixture(public_fixture)
    fixture_value = "offline-demo-placeholder"
    redacted = redact_text("Authorization: Bearer " + fixture_value)
    if fixture_value in redacted or "[REDACTED_CREDENTIAL]" not in redacted:
        raise RuntimeError("Synthetic redaction self-check failed")
    # The fixed synthetic identity is never taken from a request and confers
    # no access to real stored documents, GitHub accounts or user assets.
    retriever = SyntheticRetriever(owner_id="synthetic-owner")
    results = retriever.retrieve(
        "exact source reference", requester_id="synthetic-owner",
    )
    summary = redact_text("Updated token handling and authorization checks")
    report = review_changed_files([{
        "path": "synthetic/changed.py",
        "sanitized_summary": summary,
        "start_line": 1, "end_line": 3,
    }])
    return {
        "mode": "synthetic-read-only",
        "fixture_only": True,
        "real_identity_verified": False,
        "execution_allowed": False,
        "inventory": inventory,
        "redaction": {"applied": True, "source_text_returned": False},
        "retrieval": {
            "citations": [item.source_ref for item in results],
            "real_documents_indexed": False,
        },
        "pr_review": {
            "categories": [item.category for item in report.findings],
            "advisory_only": report.advisory_only,
            "approval_authority": report.approval_authority,
        },
    }
