"""Offline import of public GitHub metadata obtained through an authorized connector.

No live HTTP, GitHub token, files, private repositories, or external provider call.
This input is a dated snapshot, not a permanently fresh/owner-authenticated index.
"""
from __future__ import annotations
import argparse
import json
import re
from datetime import date
from pathlib import Path
from omega_mvi.inspection.github_inventory import (
    TARGET_REPOSITORY, inventory_from_public_metadata_fixture,
)

SCHEMA = "omega-public-repository-snapshot-v1"
EXPECTED_URL = f"https://api.github.com/repos/{TARGET_REPOSITORY}"
FIELDS = frozenset(("full_name","name","visibility","private","description",
                    "stargazers_count","forks_count","watchers_count",
                    "open_issues_count"))


def import_snapshot(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != {"schema","provenance","metadata"}:
        raise ValueError("PUBLIC_SNAPSHOT_DENIED")
    if payload["schema"] != SCHEMA:
        raise ValueError("PUBLIC_SNAPSHOT_DENIED")
    source, metadata = payload["provenance"], payload["metadata"]
    if type(source) is not dict or type(metadata) is not dict:
        raise ValueError("PUBLIC_SNAPSHOT_DENIED")
    if set(source) != {"provider","source_url","read_date_utc",
                       "verified_main_head","mode","live_refresh_enabled"}:
        raise ValueError("PUBLIC_SNAPSHOT_DENIED")
    if (source["provider"] != "GitHub REST API"
        or source["source_url"] != EXPECTED_URL
        or source["mode"] != "public_read_only_connector_export"
        or source["live_refresh_enabled"] is not False
        or set(metadata) != FIELDS):
        raise ValueError("PUBLIC_SNAPSHOT_DENIED")
    sha = source["verified_main_head"]
    if not isinstance(sha,str) or re.fullmatch(r"[a-f0-9]{40}",sha) is None:
        raise ValueError("PUBLIC_SNAPSHOT_DENIED")
    day = source["read_date_utc"]
    if not isinstance(day,str):
        raise ValueError("PUBLIC_SNAPSHOT_DENIED")
    try:
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError("PUBLIC_SNAPSHOT_DENIED")
    except ValueError:
        raise ValueError("PUBLIC_SNAPSHOT_DENIED") from None
    try:
        filtered = inventory_from_public_metadata_fixture(metadata)
    except (TypeError,ValueError):
        raise ValueError("PUBLIC_SNAPSHOT_DENIED") from None
    return {"inventory":filtered,"provenance":{
        "source_url":EXPECTED_URL,"read_date_utc":day,
        "main_head_sha":sha,"snapshot_only":True},
        "secrets_indexed":False,"owner_execution_authorized":False}


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description="Import OMEGA public repository metadata")
    parser.add_argument("--snapshot",type=Path,required=True)
    opts=parser.parse_args(argv)
    try:
        if opts.snapshot.is_symlink() or opts.snapshot.stat().st_size > 8192:
            raise ValueError("PUBLIC_SNAPSHOT_DENIED")
        data=json.loads(opts.snapshot.read_text(encoding="utf-8"))
        result=import_snapshot(data)
    except (OSError, ValueError, UnicodeError, TypeError):
        print('{"error":"PUBLIC_SNAPSHOT_DENIED"}')
        return 2
    print(json.dumps(result,sort_keys=True,separators=(",",":")))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
