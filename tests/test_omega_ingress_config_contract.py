"""Prove the disposable ingress policy rejects unreviewed changes."""
from pathlib import Path
import pytest
from scripts.omega_ingress_config_gate import CONFIG, EXPECTED, accepted, inspect_file


def test_checked_in_nginx_policy_is_review_pinned():
    assert inspect_file(CONFIG)
    assert accepted(EXPECTED)


@pytest.mark.parametrize("modified", [
    EXPECTED + "\ninclude /etc/nginx/conf.d/*.conf;\n",
    EXPECTED.replace("proxy_pass_request_headers off;", "proxy_pass_request_headers on;"),
    EXPECTED.replace("limit_except GET HEAD { deny all; }", ""),
    EXPECTED.replace("proxy_set_header Authorization \"\";", ""),
    EXPECTED.replace("proxy_pass http://api:8000;", "proxy_pass http://external.invalid;"),
    EXPECTED.replace("access_log off;", "access_log /tmp/requests.log;"),
    EXPECTED.replace("listen 8080;", "listen 0.0.0.0:8080;"),
])
def test_unreviewed_nginx_changes_fail_closed(tmp_path: Path, modified: str):
    assert not accepted(modified)
    path = tmp_path / "nginx.conf"
    path.write_text(modified, encoding="utf-8")
    assert not inspect_file(path)


def test_missing_symlink_and_nonutf8_or_oversized_config_denied(tmp_path: Path):
    missing = tmp_path / "missing.conf"
    assert not inspect_file(missing)
    symlink = tmp_path / "symlink.conf"
    symlink.symlink_to(CONFIG)
    assert not inspect_file(symlink)
    bad = tmp_path / "bad.conf"
    bad.write_bytes(b"\xff")
    assert not inspect_file(bad)
    bad.write_bytes(b"A" * 4097)
    assert not inspect_file(bad)
