"""Read-only, SHA-pinned GitHub PR evidence gate; never publishes Checks or merges."""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

REPOSITORY = "mehmetcerdik457-ctrl/benim-uygulamam"
SHA = re.compile(r"[0-9a-f]{40}\Z")
RISK_PATH = re.compile(
    r"(^\.github/|(^|/)(auth|security|secrets?|polic(?:y|ies)|deploy|migration|"
    r"permissions?|credential|workflow|docker|compose)(/|[._-])|"
    r"\.env|(^|/)(Dockerfile|CODEOWNERS)$)", re.I
)
MAX_BYTES = 2_000_000
DOC_ONLY_PATH = re.compile(r"^(?:README|CHANGELOG)\.md$|^docs/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.md$", re.I)
# Default to high risk for code, config, infrastructure and unrecognized paths.
# Only allow-listed, documentation-only changes can be normal risk.


class EvidenceError(Exception):
    """Missing, stale, incomplete or unverifiable evidence."""


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise EvidenceError("Redirects are forbidden for evidence collection")


def _strict_list(page: object, *, limit: int = 100) -> list[dict[str, Any]]:
    if not isinstance(page, list) or len(page) >= limit:
        raise EvidenceError("Missing, invalid or possibly truncated evidence page")
    if any(not isinstance(item, dict) for item in page):
        raise EvidenceError("Malformed evidence record")
    return page


def _strict_collection(page: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(page, dict) or type(page.get("total_count")) is not int:
        raise EvidenceError("Missing evidence collection count")
    items = page.get(key)
    if not isinstance(items, list) or page["total_count"] != len(items):
        raise EvidenceError("Truncated evidence collection")
    if len(items) > 100 or any(not isinstance(item, dict) for item in items):
        raise EvidenceError("Invalid evidence collection")
    return items


def _pr_identity(pr: object) -> tuple[object, ...]:
    """Stable identity throughout a GET-only evidence collection."""
    if not isinstance(pr, dict) or type(pr.get("number")) is not int or pr["number"] < 1:
        raise EvidenceError("Invalid PR number or metadata")
    head, base = pr.get("head"), pr.get("base")
    if not isinstance(head, dict) or not isinstance(base, dict):
        raise EvidenceError("PR head/base references missing")
    head_repo, base_repo = head.get("repo"), base.get("repo")
    if not isinstance(head_repo, dict) or not isinstance(base_repo, dict):
        raise EvidenceError("PR head/base repository missing")
    sha, base_sha = head.get("sha"), base.get("sha")
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise EvidenceError("Invalid PR HEAD SHA")
    if not isinstance(base_sha, str) or not SHA.fullmatch(base_sha):
        raise EvidenceError("Invalid PR base SHA")
    for value in (head.get("ref"), base.get("ref"), head_repo.get("full_name"),
                  base_repo.get("full_name")):
        if not isinstance(value, str) or not value:
            raise EvidenceError("Missing PR branch or repository identity")
    return (pr["number"], pr.get("state"), pr.get("draft"), sha,
            head.get("ref"), head_repo["full_name"], base_sha,
            base.get("ref"), base_repo["full_name"])


class GitHubReadOnlyClient:
    """Fixed GitHub API host and repository, GET only, no credential logging.

    Give this client only a repository-scoped read-only installation token.
    Never hand it the eventual Checks-write publisher token.
    """

    def __init__(self, token: str | None = None, *, repository: str = REPOSITORY):
        if repository != REPOSITORY:
            raise EvidenceError("Repository is outside allowlist")
        self._token = token
        self.repository = repository
        self._opener = build_opener(_NoRedirects())

    def _get(self, endpoint: str) -> Any:
        if not endpoint.startswith("/") or ".." in endpoint or "//" in endpoint:
            raise EvidenceError("Disallowed API endpoint")
        url = f"https://api.github.com/repos/{self.repository}{endpoint}"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "OMEGA-PR-ReadOnly-Gate",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            with self._opener.open(Request(url, headers=headers, method="GET"), timeout=12) as response:
                if response.status != 200:
                    raise EvidenceError("GitHub evidence request was not successful")
                body = response.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    raise EvidenceError("GitHub evidence exceeded size limit")
                return json.loads(body.decode("utf-8"))
        except (HTTPError, URLError, ValueError, UnicodeError, TimeoutError) as exc:
            raise EvidenceError("GitHub evidence unavailable") from exc

    def snapshot(self, number: int) -> dict[str, Any]:
        if type(number) is not int or number < 1:
            raise EvidenceError("Invalid pull request number")
        pr = self._get(f"/pulls/{number}")
        identity = _pr_identity(pr)
        if identity[0] != number or identity[5] != REPOSITORY or identity[8] != REPOSITORY:
            raise EvidenceError("PR/repository identity mismatch")
        sha = identity[3]
        files = self._get(f"/pulls/{number}/files?per_page=100")
        checks = self._get(f"/commits/{sha}/check-runs?per_page=100")
        actions = self._get(
            f"/actions/runs?head_sha={quote(sha)}&event=pull_request&per_page=100"
        )
        reviews = self._get(f"/pulls/{number}/reviews?per_page=100")
        branch = self._get("/branches/main")
        latest = self._get(f"/pulls/{number}")
        if _pr_identity(latest) != identity:
            raise EvidenceError("PR head, base, state or repository changed during reads")
        return {
            "pr": pr, "files": _strict_list(files),
            "checks": _strict_collection(checks, "check_runs"),
            "runs": _strict_collection(actions, "workflow_runs"),
            "reviews": _strict_list(reviews),
            "main": branch, "rechecked_sha": sha,
        }


@dataclass(frozen=True)
class GateVerdict:
    head_sha: str
    accepted: bool
    risk: str
    blockers: tuple[str, ...]
    authoritative: bool = False


def evaluate(
    evidence: Mapping[str, Any], *, expected_sha: str,
    trusted_check_app_id: int,
    required_checks: tuple[str, ...],
    authorized_human_reviewers: frozenset[str],
) -> GateVerdict:
    """Evaluate non-authoritative evidence; never treat this as a Check write."""
    if not isinstance(expected_sha, str) or not SHA.fullmatch(expected_sha):
        raise EvidenceError("Expected commit SHA is missing or invalid")
    if type(trusted_check_app_id) is not int or trusted_check_app_id <= 0:
        raise EvidenceError("Trusted check producer is unconfigured")
    if not required_checks or len(set(required_checks)) != len(required_checks):
        raise EvidenceError("Required checks unconfigured or duplicated")
    if not authorized_human_reviewers:
        raise EvidenceError("Human reviewer allowlist not configured")
    pr = evidence.get("pr")
    if not isinstance(pr, dict):
        raise EvidenceError("PR evidence missing")
    head, base = pr.get("head"), pr.get("base")
    if not isinstance(head, dict) or not isinstance(base, dict):
        raise EvidenceError("Missing PR refs")
    if head.get("sha") != expected_sha or evidence.get("rechecked_sha") != expected_sha:
        raise EvidenceError("Stale or changed PR HEAD")
    identity = _pr_identity(pr)
    if pr.get("state") != "open" or pr.get("draft") is not False:
        raise EvidenceError("PR not open and ready for review")
    if identity[5] != REPOSITORY or identity[8] != REPOSITORY:
        raise EvidenceError("Fork or untrusted base repository")
    if base.get("ref") != "main" and not str(base.get("ref", "")).startswith("omega/"):
        raise EvidenceError("Unexpected base branch")
    files = _strict_list(evidence.get("files"))
    if not files:
        raise EvidenceError("Empty diff")
    paths = []
    for file in files:
        path = file.get("filename")
        if not isinstance(path, str) or not path or len(path) > 500 or ".." in path.split("/"):
            raise EvidenceError("Unsafe filename in diff")
        patch = file.get("patch")
        if not isinstance(patch, str) or not patch.strip() or "@@" not in patch:
            raise EvidenceError("Missing, empty or truncated file patch")
        paths.append(path)
    risk = "NORMAL" if all(DOC_ONLY_PATH.fullmatch(p) for p in paths) else "HIGH"
    blockers: list[str] = []
    main = evidence.get("main")
    if not isinstance(main, dict) or main.get("name") != "main" or main.get("protected") is not True:
        blockers.append("MAIN_NOT_PROTECTED_OR_UNKNOWN")
    if base.get("ref") != "main":
        blockers.append("STACKED_PR_NOT_MAIN_ACCEPTANCE")
    elif not isinstance(main.get("commit"), dict) or main["commit"].get("sha") != base.get("sha"):
        blockers.append("BASE_SHA_NOT_CURRENT_MAIN")

    checks = _strict_list(evidence.get("checks"), limit=101)
    for name in required_checks:
        matches = [check for check in checks if check.get("name") == name]
        if not matches:
            blockers.append(f"REQUIRED_CHECK_MISSING:{name}")
            continue
        if len(matches) != 1:
            blockers.append(f"REQUIRED_CHECK_AMBIGUOUS:{name}")
            continue
        check = matches[0]
        if (check.get("head_sha") != expected_sha or not isinstance(check.get("app"), dict)
                or check["app"].get("id") != trusted_check_app_id):
            blockers.append(f"REQUIRED_CHECK_UNTRUSTED:{name}")
        if check.get("status") != "completed" or check.get("conclusion") != "success":
            blockers.append(f"REQUIRED_CHECK_NOT_SUCCESS:{name}")
    if any(c.get("head_sha") != expected_sha for c in checks):
        blockers.append("CHECK_HEAD_MISMATCH")
    if any(c.get("status") != "completed" or c.get("conclusion") != "success" for c in checks):
        blockers.append("NEGATIVE_OR_INCOMPLETE_CHECK_PRESENT")

    runs = _strict_list(evidence.get("runs"), limit=101)
    if not runs:
        blockers.append("NO_PR_WORKFLOW_RUNS")
    for run in runs:
        run_repo = run.get("head_repository")
        linked_prs = run.get("pull_requests")
        if not isinstance(run_repo, dict) or not isinstance(linked_prs, list):
            blockers.append("WORKFLOW_PR_IDENTITY_MISSING")
            continue
        same_pr = any(
            isinstance(link, dict)
            and link.get("number") == pr["number"]
            and isinstance(link.get("head"), dict)
            and link["head"].get("sha") == expected_sha
            and isinstance(link.get("base"), dict)
            and link["base"].get("sha") == base.get("sha")
            for link in linked_prs
        )
        if (run.get("head_sha") != expected_sha
                or run.get("event") != "pull_request"
                or run_repo.get("full_name") != REPOSITORY
                or not same_pr):
            blockers.append("WORKFLOW_NOT_LINKED_TO_EXACT_PR_AND_BASE")
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            blockers.append("FAILED_BLOCKED_OR_STALE_WORKFLOW_RUN")
    reviews = _strict_list(evidence.get("reviews"))
    if risk == "HIGH":
        if any(not isinstance(r.get("submitted_at"), str) or not r["submitted_at"]
               for r in reviews):
            blockers.append("REVIEW_TIMESTAMP_MISSING")
        else:
            latest_by_reviewer = {}
            for review in sorted(reviews, key=lambda r: r["submitted_at"]):
                user = review.get("user")
                if isinstance(user, dict) and isinstance(user.get("login"), str):
                    latest_by_reviewer[user["login"]] = review
            pr_user = pr.get("user")
            pr_author = pr_user.get("login") if isinstance(pr_user, dict) else None
            approvals = [
                r for login, r in latest_by_reviewer.items()
                if r.get("state") == "APPROVED"
                and r.get("commit_id") == expected_sha
                and login in authorized_human_reviewers
                and isinstance(r.get("user"), dict)
                and r["user"].get("type") == "User"
                and login != pr_author
            ]
            if not approvals:
                blockers.append("AUTHORIZED_SHA_BOUND_HUMAN_REVIEW_MISSING")
            if any(r.get("state") == "CHANGES_REQUESTED" for r in latest_by_reviewer.values()):
                blockers.append("OUTSTANDING_CHANGES_REQUESTED")
    return GateVerdict(expected_sha, not blockers, risk, tuple(dict.fromkeys(blockers)))
