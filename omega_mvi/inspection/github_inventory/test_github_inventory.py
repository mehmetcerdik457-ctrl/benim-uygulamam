import pytest

from omega_mvi.inspection.github_inventory import (
    TARGET_REPOSITORY,
    inventory_from_public_metadata_fixture,
)


@pytest.fixture
def public_metadata():
    return {
        "full_name": TARGET_REPOSITORY,
        "name": "benim-uygulamam",
        "visibility": "public",
        "private": False,
        "description": "Public project metadata",
        "stargazers_count": 3,
        "forks_count": 2,
        "watchers_count": 4,
        "open_issues_count": 1,
        "owner": {"login": "owner"},
        "topics": ["not-in-inventory"],
        "token": "must-not-be-returned",
    }


def test_inventory_contains_only_allowlisted_public_metadata(public_metadata):
    inventory = inventory_from_public_metadata_fixture(public_metadata)

    assert inventory == {
        "repository": TARGET_REPOSITORY,
        "name": "benim-uygulamam",
        "visibility": "public",
        "description": "Public project metadata",
        "counts": {
            "stars": 3,
            "forks": 2,
            "watchers": 4,
            "open_issues": 1,
        },
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("full_name", "another-owner/another-repository"),
        ("private", True),
        ("visibility", "private"),
    ],
)
def test_rejects_out_of_scope_or_nonpublic_metadata(public_metadata, field, value):
    public_metadata[field] = value

    with pytest.raises(ValueError):
        inventory_from_public_metadata_fixture(public_metadata)


@pytest.mark.parametrize("count", [-1, True, "3", None])
def test_rejects_invalid_counts(public_metadata, count):
    public_metadata["stargazers_count"] = count

    with pytest.raises(ValueError):
        inventory_from_public_metadata_fixture(public_metadata)


def test_rejects_non_mapping_fixture():
    with pytest.raises(ValueError):
        inventory_from_public_metadata_fixture([])


def test_untrusted_public_description_is_redacted_at_source(public_metadata):
    canary = "gh" + "p_" + ("Q" * 23)  # synthetic pattern, not a real token
    email = "fictional.owner" + "@" + "example.invalid"
    public_metadata["description"] = "Public notes: " + canary + " / " + email
    inventory = inventory_from_public_metadata_fixture(public_metadata)
    assert canary not in inventory["description"]
    assert email not in inventory["description"]
    assert "[REDACTED" in inventory["description"]
    assert inventory["repository"] == TARGET_REPOSITORY
    assert public_metadata["description"].endswith(email)  # input not mutated


@pytest.mark.parametrize("invalid", [None, b"unexpected", 123, {}, ["invalid"]])
def test_fail_closed_if_sanitizer_returns_invalid_type(public_metadata, monkeypatch, invalid):
    import omega_mvi.inspection.github_inventory as gh_inventory
    public_metadata["description"] = "safe synthetic description"
    monkeypatch.setattr(gh_inventory, "redact_text", lambda _: invalid)
    with pytest.raises(PermissionError, match="METADATA_REDACTION_FAILED"):
        inventory_from_public_metadata_fixture(public_metadata)


def test_sanitizer_failure_cannot_include_sensitive_details(public_metadata, monkeypatch):
    import omega_mvi.inspection.github_inventory as gh_inventory
    canary = "never-copy-synthetic-sensitive-details"
    public_metadata["description"] = canary
    def unavailable(_):
        raise RuntimeError("private value: " + canary)
    monkeypatch.setattr(gh_inventory, "redact_text", unavailable)
    with pytest.raises(PermissionError, match="^METADATA_REDACTION_FAILED$") as exc:
        inventory_from_public_metadata_fixture(public_metadata)
    assert canary not in str(exc.value)
