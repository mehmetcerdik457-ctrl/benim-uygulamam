"""Fail-closed static integrity gate for disposable OMEGA Nginx ingress.

A pinned template is *not* runtime isolation or owner-device acceptance.
Changes to the proxy policy require independent review and explicit template
updates. This program never invokes Nginx, reads secrets or opens sockets.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "omega_mvi" / "ingress" / "nginx.conf"
EXPECTED = "worker_processes 1;\npid /tmp/nginx.pid;\nevents { worker_connections 128; }\nhttp {\n  access_log off;\n  error_log /dev/stderr warn;\n  client_max_body_size 8k;\n  client_body_timeout 5s;\n  send_timeout 5s;\n  server {\n    listen 8080;\n    server_tokens off;\n    location / {\n      limit_except GET HEAD { deny all; }\n      proxy_pass http://api:8000;\n      proxy_connect_timeout 3s;\n      proxy_read_timeout 5s;\n      proxy_set_header Host localhost;\n      proxy_set_header X-Forwarded-For \"\";\n      proxy_set_header X-Forwarded-Host \"\";\n      proxy_set_header X-Forwarded-Proto \"\";\n      proxy_set_header Authorization \"\";\n      proxy_pass_request_headers off;\n    }\n  }\n}\n"


def accepted(contents: object) -> bool:
    return type(contents) is str and contents == EXPECTED


def inspect_file(path: Path = CONFIG) -> bool:
    try:
        # Deny substituted symlinks or oversized/replaced files without
        # printing attacker-controlled file contents or filesystem paths.
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 4096:
            return False
        payload = path.read_bytes()
        return len(payload) <= 4096 and payload == EXPECTED.encode("utf-8")
    except (OSError, ValueError, UnicodeError):
        return False


def main() -> int:
    passed = inspect_file()
    print("OMEGA_INGRESS_CONFIG=" + ("PASS_PINNED_DEMO" if passed else "DENIED_UNREVIEWED_CHANGE"))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
