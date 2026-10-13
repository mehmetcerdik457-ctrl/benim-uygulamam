"""Fail-closed, offline-first metadata boundary for OMEGA-011 and OMEGA-013.

No network clients or credential loading live here. The caller must separately
obtain explicit resource approval and supply a read-only page-fetch callback.
"""
from collections import Counter
import re
from urllib.parse import parse_qs, urlparse

from omega_mvi.inspection.redaction import redact_text


class InventoryDenied(ValueError):
    """Unapproved resource or unsafe provider response."""


class InventoryIncomplete(RuntimeError):
    """Do not report a partial result as a complete inventory."""


_OWNER = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\Z")
_REPO_SLUG = re.compile(r"[A-Za-z0-9_.-]{1,100}\Z")


def _safe_repository(name):
    """Canonical GitHub owner/repo only; never interpolate untrusted paths."""
    if type(name) is not str or len(name) > 140:
        return False
    parts = name.split("/")
    return (len(parts) == 2 and bool(_OWNER.fullmatch(parts[0]))
            and bool(_REPO_SLUG.fullmatch(parts[1]))
            and parts[1] not in (".", "..")
            and redact_text(name) == name)


def _safe_branch(name):
    return (type(name) is str and len(name) <= 200
            and bool(_BRANCH.fullmatch(name))
            and ".." not in name and redact_text(name) == name)
_RESOURCE = {"branches", "forks"}
_BRANCH = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./-]{0,199}\Z")
_MIME = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]*/[A-Za-z0-9][A-Za-z0-9.+-]*\Z")


def _page_url(repository, resource, page):
    return f"https://api.github.com/repos/{repository}/{resource}?per_page=100&page={page}"


def _assert_safe_next(url, repository, resource, expected_page):
    parts = urlparse(url)
    expected_path = f"/repos/{repository}/{resource}"
    params = parse_qs(parts.query, keep_blank_values=True)
    if (parts.scheme != "https" or parts.netloc != "api.github.com"
            or parts.path != expected_path or parts.fragment or parts.username
            or params != {"per_page": ["100"], "page": [str(expected_page)]}):
        raise InventoryDenied("Unsafe GitHub pagination destination")


def _next_link(headers):
    link = headers.get("link", headers.get("Link", ""))
    if type(link) is not str:
        raise InventoryIncomplete("Malformed pagination headers")
    matches = []
    for segment in link.split(","):
        parts = segment.strip().split(";")
        if any(part.strip() == 'rel="next"' for part in parts[1:]):
            value = parts[0].strip()
            if not (value.startswith("<") and value.endswith(">")):
                raise InventoryDenied("Malformed next Link")
            matches.append(value[1:-1])
    if len(matches) > 1:
        raise InventoryDenied("Ambiguous next Link")
    return matches[0] if matches else None


def github_metadata_pages(fetch_page, repository, approved_repositories,
                          resource, *, max_pages=10):
    """Collect only PUBLIC repo branch names or fork names via exact allowlist.

    fetch_page(url) => {status: int, headers: dict, items: list}.
    On 403/429, missing pagination certainty, or a page limit: fail closed.
    A connector that hides headers cannot prove API quota; no quota claim made.
    """
    if (not _safe_repository(repository) or
            type(approved_repositories) not in (list, tuple, set, frozenset) or
            repository not in approved_repositories or
            type(resource) is not str or resource not in _RESOURCE):
        raise InventoryDenied("GitHub resource not explicitly approved")
    if type(max_pages) is not int or not 1 <= max_pages <= 50:
        raise InventoryDenied("Invalid page ceiling")
    results = []
    seen_names = set()
    for page in range(1, max_pages + 1):
        try:
            response = fetch_page(_page_url(repository, resource, page))
        except Exception:
            # Some HTTP clients embed request headers, credentials or raw
            # payloads in exception messages. Never forward those to logs.
            raise InventoryIncomplete("GitHub metadata fetch failed") from None
        if type(response) is not dict:
            raise InventoryIncomplete("Missing GitHub response")
        status = response.get("status")
        if status in (403, 429):
            raise InventoryIncomplete("GitHub permission or rate limit block")
        if status != 200:
            raise InventoryIncomplete("GitHub response not verified")
        headers, items = response.get("headers"), response.get("items")
        if type(headers) is not dict or type(items) is not list or len(items) > 100:
            raise InventoryIncomplete("Missing headers or malformed page")
        if headers.get("x-ratelimit-remaining", headers.get("X-RateLimit-Remaining")) == "0":
            raise InventoryIncomplete("GitHub rate limit exhausted")
        for item in items:
            if type(item) is not dict:
                raise InventoryIncomplete("Malformed inventory item")
            name = item.get("name" if resource == "branches" else "full_name")
            if type(name) is not str:
                raise InventoryIncomplete("Missing item name")
            if resource == "branches":
                if not _safe_branch(name):
                    raise InventoryIncomplete("Unsafe or sensitive branch name")
            else:
                # A public source repository does NOT authorize private fork
                # disclosure. Require explicit provider public visibility.
                if not _safe_repository(name):
                    raise InventoryIncomplete("Unsafe or sensitive fork name")
                if item.get("private") is not False or item.get("visibility") != "public":
                    raise InventoryIncomplete("Fork public visibility not proven")
            if name in seen_names:
                raise InventoryIncomplete("Repeated inventory name across pages")
            seen_names.add(name)
            results.append(name)
        next_url = _next_link(headers)
        if next_url is not None:
            _assert_safe_next(next_url, repository, resource, page + 1)
        elif len(items) == 100:
            # Without Link/header certainty, exactly full pages are ambiguous.
            raise InventoryIncomplete("Pagination not proven complete")
        else:
            return {"repository": repository, "resource": resource,
                    "count": len(results), "names": tuple(results),
                    "complete": True, "pages": page, "api_quota": "UNKNOWN"}
    raise InventoryIncomplete("Page ceiling reached; no completeness claim")


def drive_metadata_only(pages, *, approved_folder_ids, folder_id):
    """Return minimal ephemeral index; titles/contents/permissions excluded.

    pages are read-only metadata pages previously obtained under an explicitly
    approved folder (never from broad Drive search). No download is performed.
    """
    if (type(folder_id) is not str or not folder_id or
            type(approved_folder_ids) not in (list, tuple, set, frozenset)
            or folder_id not in approved_folder_ids):
        raise InventoryDenied("Drive folder not explicitly approved")
    index = []
    seen_ids = set()
    for page in pages:
        if type(page) is not dict or page.get("complete") is not True:
            raise InventoryIncomplete("Drive metadata page not proven complete")
        files = page.get("files")
        if type(files) is not list:
            raise InventoryIncomplete("Invalid Drive page")
        for item in files:
            if type(item) is not dict:
                raise InventoryIncomplete("Invalid Drive file metadata")
            parents = item.get("parent_ids")
            if (type(parents) not in (list, tuple) or len(parents) != 1
                    or parents[0] != folder_id):
                raise InventoryDenied("Drive item outside allowed folder")
            ident, mime = item.get("id"), item.get("mime_type")
            if (type(ident) is not str or not 1 <= len(ident) <= 200
                    or not re.fullmatch(r"[A-Za-z0-9_-]+", ident)
                    or type(mime) is not str or len(mime) > 255
                    or not _MIME.fullmatch(mime)):
                raise InventoryIncomplete("Invalid Drive metadata")
            if ident in seen_ids:
                raise InventoryIncomplete("Repeated Drive file ID")
            seen_ids.add(ident)
            # No title, description, owners, paths, links or file bytes.
            index.append({"id": ident, "mime_type": mime})
    return {"complete": True, "item_count": len(index),
            "mime_counts": dict(Counter(i["mime_type"] for i in index)),
            "ephemeral_index": tuple(index), "content_downloads": 0}


def drive_metadata_pages(fetch_page, *, approved_folder_ids, folder_id,
                         max_pages=10):
    """Fetch strictly approved folder metadata pages without returning item IDs.

    `fetch_page(folder_id, page_token)` MUST be an adapter restricted to an
    authorized Drive files.list metadata query for this exact folder. It must
    return {status: 200, files: [...], next_page_token: str | None,
            incomplete_search: False} using
    minimal fields. This layer cannot establish the adapter's OAuth scopes;
    it *does* fail closed on incomplete/duplicated/malformed pages.
    """
    if (type(folder_id) is not str or not folder_id or
            type(approved_folder_ids) not in (list, tuple, set, frozenset)
            or folder_id not in approved_folder_ids):
        raise InventoryDenied("Drive folder not explicitly approved")
    if type(max_pages) is not int or not 1 <= max_pages <= 50:
        raise InventoryDenied("Invalid Drive page ceiling")
    # Never accumulate provider pages with unrequested/sensitive extra fields.
    counts = Counter()
    seen_ids = set()
    total = 0
    seen_tokens = set()
    page_token = None
    for page_no in range(1, max_pages + 1):
        try:
            response = fetch_page(folder_id, page_token)
        except Exception:
            # Suppress provider-specific exception messages containing
            # private folder IDs or authentication material.
            raise InventoryIncomplete("Drive metadata fetch failed") from None
        if type(response) is not dict or response.get("status") != 200:
            raise InventoryIncomplete("Drive metadata response not verified")
        files = response.get("files")
        if response.get("incomplete_search") is not False:
            raise InventoryIncomplete("Drive provider reported incomplete/unknown search")
        if type(files) is not list or len(files) > 100:
            raise InventoryIncomplete("Invalid Drive metadata page size")
        if "next_page_token" not in response:
            raise InventoryIncomplete("Drive continuation status missing")
        next_token = response["next_page_token"]
        if next_token is not None:
            if (type(next_token) is not str or not
                    re.fullmatch(r"[A-Za-z0-9._~+/=-]{1,1024}", next_token)
                    or next_token == page_token or next_token in seen_tokens):
                raise InventoryIncomplete("Invalid/repeated Drive page token")
            seen_tokens.add(next_token)
        # Check this page before following its continuation. Keep only an
        # ephemeral ID set and MIME counters, never full raw provider pages.
        validated = drive_metadata_only(
            [{"complete": True, "files": files}],
            approved_folder_ids=approved_folder_ids, folder_id=folder_id)
        for item in validated["ephemeral_index"]:
            if item["id"] in seen_ids:
                raise InventoryIncomplete("Repeated Drive file ID")
            seen_ids.add(item["id"])
            counts[item["mime_type"]] += 1
            total += 1
        if next_token is None:
            return {"complete": True, "item_count": total,
                    "mime_counts": dict(counts), "pages": page_no,
                    "content_downloads": 0}
        page_token = next_token
    raise InventoryIncomplete("Drive metadata page ceiling reached")
