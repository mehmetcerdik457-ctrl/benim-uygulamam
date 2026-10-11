"""Fail-closed tracker guard: no private filename, raw data or subprocess stderr in logs."""
import re
import subprocess

_FORBIDDEN = re.compile(
    r"(^|/)(id_(rsa|ed25519)|key\.properties|credentials[^/]*\.json|"
    r"service[-_]?account[^/]*\.json|.*\.(keystore|jks|pem|p12|pfx|db|sqlite|sqlite3))$"
)
_ALLOWED_ENVS = {".env.example", ".env.sample", ".env.template"}


def scan(directory="."):
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"], cwd=directory,
            check=False, capture_output=True,
        )
    except OSError:
        return 2
    if result.returncode != 0:
        return 2
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        filename = raw.decode("utf-8", errors="surrogateescape")
        basename = filename.rsplit("/", 1)[-1]
        if basename == ".env" or basename.startswith(".env."):
            if basename not in _ALLOWED_ENVS:
                return 1
        if _FORBIDDEN.search(filename):
            return 1
    return 0


def main():
    result = scan()
    if result == 0:
        print("OMEGA_PRIVATE_FILENAME_GUARD=PASS")
    elif result == 1:
        print("Private-state filename blocked.")
    else:
        print("Filename scan failed; fail-closed.")
    return 0 if result == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
