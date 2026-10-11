"""Synthetic-only tests. Never place authentic secrets in fixtures or logs."""
import pytest

from omega_mvi.inspection.external_accounts import (
    InventoryDenied, InventoryIncomplete, drive_metadata_only,
    drive_metadata_pages, github_metadata_pages,
)
from omega_mvi.inspection.external_accounts.secret_findings import (
    classify_finding, record_remediation,
)

REPO = "mehmetcerdik457-ctrl/benim-uygulamam"


def _one_page_fetch(url):
    assert url == f"https://api.github.com/repos/{REPO}/branches?per_page=100&page=1"
    return {"status": 200, "headers": {"x-ratelimit-remaining": "42"},
            "items": [{"name": "main", "private_content": "never-copy"},
                      {"name": "topic/demo"}]}


def test_github_allowlisted_branches_strip_unexpected_metadata():
    result = github_metadata_pages(_one_page_fetch, REPO, {REPO}, "branches")
    assert result["names"] == ("main", "topic/demo")
    assert result["complete"] and result["count"] == 2
    assert result["api_quota"] == "UNKNOWN"
    assert "never-copy" not in repr(result)


def test_github_cross_repo_denied_without_fetch():
    def no_call(_):
        pytest.fail("Unauthorized callback invoked")
    with pytest.raises(InventoryDenied):
        github_metadata_pages(no_call, "outside/other", {REPO}, "branches")


def test_github_explicit_fork_metadata_only():
    def forks(_):
        return {"status": 200, "headers": {},
                "items": [{"full_name": "someone/public-fork",
                           "authorization": "never-copy"}]}
    result = github_metadata_pages(forks, REPO, {REPO}, "forks")
    assert result["names"] == ("someone/public-fork",)
    assert "never-copy" not in repr(result)


def test_github_rate_limited_fails_closed():
    def blocked(_):
        return {"status": 429, "headers": {"retry-after": "60"}, "items": []}
    with pytest.raises(InventoryIncomplete):
        github_metadata_pages(blocked, REPO, {REPO}, "branches")


def test_github_full_page_without_link_is_incomplete():
    def missing_link(_):
        return {"status": 200, "headers": {},
                "items": [{"name": f"branch-{n}"} for n in range(100)]}
    with pytest.raises(InventoryIncomplete, match="Pagination"):
        github_metadata_pages(missing_link, REPO, {REPO}, "branches")


def test_github_unsafe_next_link_rejected():
    def malicious(_):
        return {"status": 200, "headers": {
            "Link": '<https://other.invalid/steal?page=2>; rel="next"'},
            "items": [{"name": "main"}]}
    with pytest.raises(InventoryDenied):
        github_metadata_pages(malicious, REPO, {REPO}, "branches")


def test_github_two_pages_and_page_ceiling():
    def fetch(url):
        if url.endswith("page=1"):
            return {"status": 200, "headers": {"Link":
                f'<https://api.github.com/repos/{REPO}/branches?per_page=100&page=2>; rel="next"'},
                "items": [{"name": "one"}]}
        return {"status": 200, "headers": {}, "items": [{"name": "two"}]}
    actual = github_metadata_pages(fetch, REPO, {REPO}, "branches")
    assert actual["names"] == ("one", "two")
    assert actual["pages"] == 2
    with pytest.raises(InventoryIncomplete, match="ceiling"):
        github_metadata_pages(fetch, REPO, {REPO}, "branches", max_pages=1)


def test_drive_allowlisted_folder_strips_names_bytes_owners():
    item = {"id": "fake_id_01", "mime_type": "application/pdf",
            "parent_ids": ["approved_folder"],
            "title": "PRIVATE-NAME-SHOULD-NOT-APPEAR",
            "content": "SYNTHETIC-BYTES-NOT-ALLOWED",
            "permissions": [{"role": "owner"}]}
    result = drive_metadata_only([{"complete": True, "files": [item]}],
                                 approved_folder_ids={"approved_folder"},
                                 folder_id="approved_folder")
    assert result["item_count"] == 1
    assert result["content_downloads"] == 0
    assert result["ephemeral_index"] == (
        {"id": "fake_id_01", "mime_type": "application/pdf"},)
    assert "SYNTHETIC-BYTES" not in repr(result)
    assert "PRIVATE-NAME" not in repr(result)


def test_drive_cross_folder_and_incomplete_page_denied():
    pages = [{"complete": True, "files": [{"id": "item_1",
              "mime_type": "text/plain", "parent_ids": ["other"]}]}]
    with pytest.raises(InventoryDenied):
        drive_metadata_only(pages, approved_folder_ids={"approved"},
                            folder_id="approved")
    with pytest.raises(InventoryDenied):
        drive_metadata_only([], approved_folder_ids={"approved"},
                            folder_id="not_approved")
    with pytest.raises(InventoryIncomplete):
        drive_metadata_only([{"complete": False, "files": []}],
                            approved_folder_ids={"approved"}, folder_id="approved")


@pytest.mark.parametrize("detector,provider", [
    ("github_pat", "GITHUB"), ("aws_access_key_id", "AWS"),
    ("google_api_key", "GOOGLE_CLOUD"), ("openai_api_key", "OPENAI"),
    ("slack_token", "SLACK"), ("generic_api_key", "UNKNOWN"),
])
def test_provider_is_detector_hint_only(detector, provider):
    finding = classify_finding(detector_id=detector,
                               source_path="synthetic/demo.txt",
                               line_number=3, risk="HIGH")
    assert finding.provider_type == provider
    assert finding.classification == "SUSPECTED_UNVERIFIED"
    assert finding.as_record()["remediation_status"] == "NOT_STARTED"
    assert set(finding.as_record()) == {
        "provider_type", "source_location", "source_line",
        "risk_level", "remediation_status", "classification"}


def test_secret_record_rejects_untrusted_path_and_invalid_risk():
    for path in ("../outside", "/etc/passwd", "demo space.txt"):
        with pytest.raises(ValueError):
            classify_finding(detector_id="github_pat", source_path=path,
                             line_number=1)
    with pytest.raises(ValueError):
        classify_finding(detector_id="github_pat", source_path="a.txt",
                         line_number=1, risk="CERTAIN")


def test_remediation_cannot_claim_revocation_without_evidence():
    f = classify_finding(detector_id="github_pat",
                         source_path="synthetic/demo.txt", line_number=1)
    with pytest.raises(PermissionError):
        record_remediation(f, "REVOKED_VERIFIED", owner_approved=True)
    with pytest.raises(PermissionError):
        record_remediation(f, "ROTATION_PLANNED")
    assert record_remediation(
        f, "OWNER_REVIEW_REQUIRED").remediation_status == "OWNER_REVIEW_REQUIRED"
    assert f.remediation_status == "NOT_STARTED"


def test_github_repeated_branch_name_fails_closed():
    def repeated(_):
        return {"status": 200, "headers": {},
                "items": [{"name": "main"}, {"name": "main"}]}
    with pytest.raises(InventoryIncomplete, match="Repeated"):
        github_metadata_pages(repeated, REPO, {REPO}, "branches")


def test_github_duplicate_next_link_denied():
    next_url = f"https://api.github.com/repos/{REPO}/branches?per_page=100&page=2"
    def ambiguous(_):
        return {"status": 200, "headers": {"link": (
            f'<{next_url}>; rel="next", <{next_url}>; rel="next"')},
                "items": [{"name": "main"}]}
    with pytest.raises(InventoryDenied, match="Ambiguous"):
        github_metadata_pages(ambiguous, REPO, {REPO}, "branches")


def test_github_quota_zero_denied_without_returning_results():
    def exhausted(_):
        return {"status": 200, "headers": {"X-RateLimit-Remaining": "0"},
                "items": [{"name": "main"}]}
    with pytest.raises(InventoryIncomplete, match="rate limit"):
        github_metadata_pages(exhausted, REPO, {REPO}, "branches")


def test_drive_metadata_pages_complete_two_page_counts_no_ids_or_titles():
    observed = []
    def fetch(folder_id, token):
        observed.append((folder_id, token))
        if token is None:
            return {"status": 200, "incomplete_search": False,
                    "files": [{"id": "file_one", "parent_ids": ["approved"],
                               "mime_type": "application/pdf",
                               "title": "PRIVATE FIRST TITLE"}],
                    "next_page_token": "nextToken2"}
        return {"status": 200, "incomplete_search": False,
                "files": [{"id": "file_two", "parent_ids": ["approved"],
                           "mime_type": "text/plain",
                           "title": "PRIVATE SECOND TITLE"}],
                "next_page_token": None}
    result = drive_metadata_pages(
        fetch, approved_folder_ids={"approved"}, folder_id="approved")
    assert observed == [("approved", None), ("approved", "nextToken2")]
    assert result == {
        "complete": True, "item_count": 2,
        "mime_counts": {"application/pdf": 1, "text/plain": 1},
        "pages": 2, "content_downloads": 0,
    }
    assert "file_one" not in repr(result)
    assert "PRIVATE" not in repr(result)
    assert "nextToken2" not in repr(result)


@pytest.mark.parametrize("bad", [
    {"status": 403, "files": [], "incomplete_search": False, "next_page_token": None},
    {"status": 200, "files": [], "next_page_token": None},
    {"status": 200, "files": [], "incomplete_search": True, "next_page_token": None},
    {"status": 200, "files": [], "incomplete_search": False},
    {"status": 200, "files": [], "incomplete_search": False, "next_page_token": ""},
])
def test_drive_metadata_pages_unknown_or_blocked_fails_closed(bad):
    with pytest.raises(InventoryIncomplete):
        drive_metadata_pages(lambda _f, _p: bad, approved_folder_ids={"approved"},
                             folder_id="approved")


def test_drive_metadata_pages_repeated_token_fails_closed():
    def repeated(_folder, _token):
        return {"status": 200, "files": [], "incomplete_search": False,
                "next_page_token": "sameToken"}
    with pytest.raises(InventoryIncomplete, match="token"):
        drive_metadata_pages(repeated, approved_folder_ids={"approved"},
                             folder_id="approved")


def test_drive_metadata_pages_repeated_id_fails_closed():
    def repeated(_folder, token):
        return {"status": 200, "incomplete_search": False,
                "files": [{"id": "file_repeat", "mime_type": "application/pdf",
                           "parent_ids": ["approved"]}],
                "next_page_token": "goNext" if token is None else None}
    with pytest.raises(InventoryIncomplete, match="Repeated Drive"):
        drive_metadata_pages(repeated, approved_folder_ids={"approved"},
                             folder_id="approved")


def test_drive_metadata_pages_does_not_call_unapproved_adapter():
    def forbidden(*_args):
        pytest.fail("Cannot call Drive without folder owner allowlist")
    with pytest.raises(InventoryDenied):
        drive_metadata_pages(forbidden, approved_folder_ids={"approved"},
                             folder_id="outside")


def test_drive_metadata_pages_rejects_second_page_scope_drift():
    def drift(_folder, token):
        return {"status": 200, "incomplete_search": False,
                "files": [] if token is None else [{
                    "id": "file_other", "mime_type": "text/plain",
                    "parent_ids": ["outside"]}],
                "next_page_token": "second" if token is None else None}
    with pytest.raises(InventoryDenied, match="outside"):
        drive_metadata_pages(drift, approved_folder_ids={"approved"},
                             folder_id="approved")


def test_drive_metadata_pages_page_limit_does_not_prove_completeness():
    def never_finishes(_folder, token):
        return {"status": 200, "incomplete_search": False, "files": [],
                "next_page_token": "page2" if token is None else "page3"}
    with pytest.raises(InventoryIncomplete, match="ceiling"):
        drive_metadata_pages(never_finishes, approved_folder_ids={"approved"},
                             folder_id="approved", max_pages=1)


def test_drive_metadata_rejects_string_parent_value():
    with pytest.raises(InventoryDenied):
        drive_metadata_only([{"complete": True, "files": [
            {"id": "file_one", "mime_type": "text/plain",
             "parent_ids": "approved"}]}],
            approved_folder_ids={"approved"}, folder_id="approved")


@pytest.mark.parametrize("closed_status", [
    "REVOKED_VERIFIED", "ROTATED_VERIFIED", "FALSE_POSITIVE_VERIFIED",
])
def test_provider_verification_cannot_be_forged_with_booleans(closed_status):
    f = classify_finding(detector_id="github_pat",
                         source_path="synthetic/demo.txt", line_number=1)
    with pytest.raises(PermissionError, match="attestation"):
        record_remediation(f, closed_status,
                           owner_approved=True, provider_verified=True)
