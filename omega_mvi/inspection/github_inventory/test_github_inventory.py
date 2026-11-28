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
