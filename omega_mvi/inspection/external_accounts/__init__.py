"""Fail-closed, offline-first metadata boundary for OMEGA-011 and OMEGA-013.

No network clients or credential loading live here. The caller must separately
obtain explicit resource approval and supply a read-only page-fetch callback.
"""
from collections import Counter
import re
from urllib.parse import parse_qs, urlparse


class InventoryDenied(ValueError):
    """Unapproved resource or unsafe provider response."""


class InventoryIncomplete(RuntimeError):
    """Do not report a partial result as a complete inventory."""


_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
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
    for segment in link.split(","):
        if 'rel="next"' in segment:
            value = segment.strip().split(";", 1)[0].strip()
            if not (value.startswith("<") and value.endswith(">")):
                raise InventoryDenied("Malformed next Link")
            return value[1:-1]
    return None


def github_metadata_pages(fetch_page, repository, approved_repositories,
                          resource, *, max_pages=10):
    """Collect only PUBLIC repo branch names or fork names via exact allowlist.

    fetch_page(url) => {status: int, headers: dict, items: list}.
    On 403/429, missing pagination certainty, or a page limit: fail closed.
    A connector that hides headers cannot prove API quota; no quota claim made.
    """
    if (not isinstance(repository, str) or
            not _REPOSITORY.fullmatch(repository) or
            type(approved_repositories) not in (list, tuple, set, frozenset) or
            repository not in approved_repositories or resource not in _RESOURCE):
        raise InventoryDenied("GitHub resource not explicitly approved")
    if type(max_pages) is not int or not 1 <= max_pages <= 50:
        raise InventoryDenied("Invalid page ceiling")
    results = []
    for page in range(1, max_pages + 1):
        response = fetch_page(_page_url(repository, resource, page))
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
                if not _BRANCH.fullmatch(name) or ".." in name:
                    raise InventoryIncomplete("Unsafe branch name")
            elif not _REPOSITORY.fullmatch(name):
                raise InventoryIncomplete("Unsafe fork name")
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
    for page in pages:
        if type(page) is not dict or page.get("complete") is not True:
            raise InventoryIncomplete("Drive metadata page not proven complete")
        files = page.get("files")
        if type(files) is not list:
            raise InventoryIncomplete("Invalid Drive page")
        for item in files:
            if type(item) is not dict or folder_id not in item.get("parent_ids", []):
                raise InventoryDenied("Drive item outside allowed folder")
            ident, mime = item.get("id"), item.get("mime_type")
            if (type(ident) is not str or not 1 <= len(ident) <= 200
                    or not re.fullmatch(r"[A-Za-z0-9_-]+", ident)
                    or type(mime) is not str or not _MIME.fullmatch(mime)):
                raise InventoryIncomplete("Invalid Drive metadata")
            # No title, description, owners, paths, links or file bytes.
            index.append({"id": ident, "mime_type": mime})
    return {"complete": True, "item_count": len(index),
            "mime_counts": dict(Counter(i["mime_type"] for i in index)),
            "ephemeral_index": tuple(index), "content_downloads": 0}
