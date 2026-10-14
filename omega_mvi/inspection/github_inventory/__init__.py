"""Build a narrow, sanitized inventory from public GitHub metadata.

Public metadata is untrusted input. Return redacted fields so all callers
receive the same safety boundary, not just the current HTTP handler.
"""
from omega_mvi.inspection.redaction import redact_text

TARGET_REPOSITORY = "mehmetcerdik457-ctrl/benim-uygulamam"
_COUNT_FIELDS = {
    "stars": "stargazers_count",
    "forks": "forks_count",
    "watchers": "watchers_count",
    "open_issues": "open_issues_count",
}


def inventory_from_public_metadata_fixture(metadata):
    """Return allowlisted metadata for this repository, without making requests."""
    if type(metadata) is not dict:
        raise ValueError("A public repository metadata fixture is required")

    if (
        metadata.get("full_name") != TARGET_REPOSITORY
        or metadata.get("name") != TARGET_REPOSITORY.split("/", 1)[1]
        or metadata.get("visibility") != "public"
        or metadata.get("private") is not False
    ):
        raise ValueError("Fixture is not public metadata for the authorized repository")

    description = metadata.get("description")
    if description is not None:
        if type(description) is not str:
            raise ValueError("Repository description must be a string or null")
        try:
            safe_description = redact_text(description)
        except Exception:
            # Do not propagate provider text or sanitizer exception details.
            raise PermissionError("METADATA_REDACTION_FAILED") from None
        if type(safe_description) is not str:
            raise PermissionError("METADATA_REDACTION_FAILED")
        description = safe_description

    counts = {}
    for output_name, fixture_name in _COUNT_FIELDS.items():
        count = metadata.get(fixture_name)
        if type(count) is not int or count < 0:
            raise ValueError("Repository counts must be non-negative integers")
        counts[output_name] = count

    return {
        "repository": TARGET_REPOSITORY,
        "name": metadata["name"],
        "visibility": "public",
        "description": description,
        "counts": counts,
    }
