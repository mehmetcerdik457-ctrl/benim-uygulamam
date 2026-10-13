"""Synthetic-only tests. Never place authentic secrets in fixtures or logs."""
import pytest

from omega_mvi.inspection.external_accounts import (
    InventoryDenied, InventoryIncomplete, drive_metadata_only,
    drive_metadata_pages, github_metadata_pages,
)
from omega_mvi.inspection.external_accounts.secret_findings import (
    SafeFinding, classify_finding, record_remediation,
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
                           "private": False, "visibility": "public",
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



def test_direct_finding_constructor_cannot_forge_verified_state():
    for closed_status in ("ROTATED_VERIFIED", "REVOKED_VERIFIED",
                          "FALSE_POSITIVE_VERIFIED", "ROTATION_PLANNED"):
        with pytest.raises(PermissionError, match="unverified"):
            SafeFinding(provider_type="GITHUB", source_location="synthetic/demo.txt",
                        source_line=1, risk_level="UNKNOWN",
                        remediation_status=closed_status)


def test_finding_constructor_rejects_forged_classification_provider_and_path():
    for changes in (
        {"classification": "PROVIDER_VERIFIED"},
        {"provider_type": "UNKNOWN_PRODUCTION_ACCOUNT"},
        {"source_location": "../owner_private"},
        {"source_line": True},
        {"risk_level": True},
    ):
        baseline = {
            "provider_type": "UNKNOWN", "source_location": "synthetic/demo.txt",
            "source_line": 1, "risk_level": "UNKNOWN",
            "remediation_status": "NOT_STARTED",
        }
        baseline.update(changes)
        with pytest.raises((ValueError, PermissionError)):
            SafeFinding(**baseline)


def test_non_private_synthetic_path_that_looks_like_token_is_rejected():
    # Generic errors intentionally do not reveal which secret-like pattern matched.
    with pytest.raises(ValueError, match="normalized relative source paths"):
        classify_finding(detector_id="unknown_detector",
                         source_path="synthetic/sk-example123.py",
                         line_number=1)


def test_caller_boolean_cannot_fake_approved_rotation_plan():
    record = classify_finding(detector_id="github_pat",
                              source_path="synthetic/demo.txt", line_number=1)
    with pytest.raises(PermissionError, match="Approval"):
        record_remediation(record, "ROTATION_PLANNED",
                           owner_approved=True, provider_verified=True)
    assert record.remediation_status == "NOT_STARTED"


def test_drive_metadata_requires_one_exact_parent():
    with pytest.raises(InventoryDenied):
        drive_metadata_only([{"complete": True, "files": [
            {"id": "example_1", "mime_type": "text/plain",
             "parent_ids": ["approved", "outside"]}]}],
            approved_folder_ids={"approved"}, folder_id="approved")


def test_drive_aggregate_discards_sensitive_provider_fields():
    def synthetic_adapter(folder, _token):
        assert folder == "approved"
        return {
            "status": 200, "incomplete_search": False, "next_page_token": None,
            "files": [{
                "id": "safeSyntheticFile", "mime_type": "application/pdf",
                "parent_ids": ["approved"],
                "title": "DO_NOT_PUBLISH_SYNTHETIC",
                "description": "DO_NOT_PUBLISH_SYNTHETIC",
                "content": "DO_NOT_PUBLISH_SYNTHETIC",
                "permissions": [{"type": "user", "role": "owner"}],
            }],
        }
    data = drive_metadata_pages(synthetic_adapter,
                                approved_folder_ids={"approved"},
                                folder_id="approved")
    assert data == {"complete": True, "item_count": 1,
                    "mime_counts": {"application/pdf": 1},
                    "pages": 1, "content_downloads": 0}
    assert "DO_NOT_PUBLISH_SYNTHETIC" not in repr(data)
    assert "safeSyntheticFile" not in repr(data)



def test_github_callback_failure_never_exposes_provider_exception_text():
    def raising_callback(_url):
        raise RuntimeError("SYNTHETIC_PRIVATE_PROVIDER_ERROR")
    with pytest.raises(InventoryIncomplete) as failure:
        github_metadata_pages(raising_callback, REPO, {REPO}, "branches")
    assert str(failure.value) == "GitHub metadata fetch failed"
    assert "SYNTHETIC_PRIVATE_PROVIDER_ERROR" not in str(failure.value)
    assert failure.value.__suppress_context__ is True


def test_drive_callback_failure_never_exposes_provider_exception_text():
    def raising_callback(_folder, _token):
        raise RuntimeError("SYNTHETIC_PRIVATE_FOLDER_ERROR")
    with pytest.raises(InventoryIncomplete) as failure:
        drive_metadata_pages(raising_callback,
                             approved_folder_ids={"approved"},
                             folder_id="approved")
    assert str(failure.value) == "Drive metadata fetch failed"
    assert "SYNTHETIC_PRIVATE_FOLDER_ERROR" not in str(failure.value)
    assert failure.value.__suppress_context__ is True


@pytest.mark.parametrize("bad_repo", (
    "owner/..", "owner/.", "owner/repo/extra", "owner//repo",
    "-invalid/repo", "owner/abc?query=bad", "owner/repo#fragment",
    "owner/" + "A" * 110,
))
def test_repository_url_path_and_slug_guards_reject_before_callback(bad_repo):
    def forbidden(_url):
        pytest.fail("Unapproved or path-like repository reached provider")
    with pytest.raises(InventoryDenied):
        github_metadata_pages(forbidden, bad_repo, {bad_repo}, "branches")


@pytest.mark.parametrize("entry", (
    {"full_name": "someone/private-fork", "private": True,
     "visibility": "private"},
    {"full_name": "someone/unknown-fork"},
    {"full_name": "someone/unverified-fork", "private": False},
    {"full_name": "someone/internal-fork", "private": False,
     "visibility": "internal"},
    {"full_name": "someone/..", "private": False,
     "visibility": "public"},
))
def test_fork_public_visibility_must_be_explicit_and_safe(entry):
    def unsafe(_url):
        return {"status": 200, "headers": {}, "items": [entry]}
    with pytest.raises(InventoryIncomplete):
        github_metadata_pages(unsafe, REPO, {REPO}, "forks")


def test_github_branch_name_with_credential_pattern_fails_closed():
    def leak(_url):
        # Fake test pattern only; no live credential used.
        return {"status": 200, "headers": {},
                "items": [{"name": "demo/ghp_example1234"}]}
    with pytest.raises(InventoryIncomplete, match="sensitive"):
        github_metadata_pages(leak, REPO, {REPO}, "branches")


def test_safe_public_fork_returns_only_public_name():
    def callback(_url):
        return {"status": 200, "headers": {}, "items": [{
            "full_name": "test-owner/test-repo", "private": False,
            "visibility": "public", "permissions": {"admin": True},
            "clone_url": "SYNTHETIC_SHOULD_NOT_LEAK"}]}
    result = github_metadata_pages(callback, REPO, {REPO}, "forks")
    assert result["names"] == ("test-owner/test-repo",)
    assert "SYNTHETIC_SHOULD_NOT_LEAK" not in repr(result)
    assert result["complete"] is True


def test_oversize_mime_metadata_is_not_accepted():
    fake = {"id": "syntheticid", "mime_type": "text/" + "a" * 256,
            "parent_ids": ["approved"]}
    with pytest.raises(InventoryIncomplete):
        drive_metadata_only([{"complete": True, "files": [fake]}],
                            approved_folder_ids={"approved"},
                            folder_id="approved")


def test_github_mixed_case_link_header_is_not_lost():
    second = f"https://api.github.com/repos/{REPO}/branches?per_page=100&page=2"
    urls = []
    def fetch(url):
        urls.append(url)
        if len(urls) == 1:
            return {"status": 200, "headers": {
                "LiNk": f'<{second}>; rel="next"'},
                "items": [{"name": "main"}]}
        return {"status": 200, "headers": {}, "items": [{"name": "test"}]}
    result = github_metadata_pages(fetch, REPO, {REPO}, "branches")
    assert result["pages"] == 2
    assert urls[-1] == second
    assert result["names"] == ("main", "test")


def test_github_mixed_case_zero_quota_is_not_ignored():
    def fetch(_):
        return {"status": 200, "headers": {"X-RaTeLiMiT-ReMaInInG": "00"},
                "items": [{"name": "main"}]}
    with pytest.raises(InventoryIncomplete, match="rate limit exhausted"):
        github_metadata_pages(fetch, REPO, {REPO}, "branches")


@pytest.mark.parametrize("header", (
    {"LINK": "garbage; rel='next'"},
    {"link": "garbage; rel=next"},
    {"link": ["untrusted-nontext-header"]},
    {"link": 'https://api.github.com/anything; rel="next"'},
    {"LiNk": "x", "link": "y"},
))
def test_ambiguous_or_noncanonical_link_is_not_silent_success(header):
    def fetch(_):
        return {"status": 200, "headers": header,
                "items": [{"name": "main"}]}
    with pytest.raises((InventoryDenied, InventoryIncomplete)):
        github_metadata_pages(fetch, REPO, {REPO}, "branches")


@pytest.mark.parametrize("bad_quota", ("NaN", "-1", "", " " * 2, 0, True))
def test_invalid_quota_header_fails_closed(bad_quota):
    def fetch(_):
        return {"status": 200, "headers": {"x-ratelimit-remaining": bad_quota},
                "items": [{"name": "main"}]}
    with pytest.raises(InventoryIncomplete, match="rate limit"):
        github_metadata_pages(fetch, REPO, {REPO}, "branches")


def test_ambiguous_quota_case_variations_fails_closed():
    def fetch(_):
        return {"status": 200, "headers": {
            "X-RateLimit-Remaining": "1",
            "x-ratelimit-remaining": "0"},
            "items": [{"name": "main"}]}
    with pytest.raises(InventoryIncomplete, match="Ambiguous"):
        github_metadata_pages(fetch, REPO, {REPO}, "branches")


def test_normal_long_repo_and_branch_names_are_not_secret_false_positives():
    def fetch(_url):
        return {"status": 200, "headers": {}, "items": [
            {"name": "omega/ui-security-and-ci-20261011"},
            {"name": "improve/metadata-pagination-long-branch-example"},
        ]}
    result = github_metadata_pages(fetch, REPO, {REPO}, "branches")
    assert result["count"] == 2
    assert result["names"] == (
        "omega/ui-security-and-ci-20261011",
        "improve/metadata-pagination-long-branch-example",
    )


def test_normal_public_long_fork_slug_is_not_secret_false_positive():
    fork = "example-owner/ordinary-project-repository-name-with-many-components"
    def fetch(_url):
        return {"status": 200, "headers": {}, "items": [{
            "full_name": fork, "private": False, "visibility": "public"}]}
    result = github_metadata_pages(fetch, REPO, {REPO}, "forks")
    assert result["names"] == (fork,)
