"""Fail-closed tracked-filename guard with generic log output only."""
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
        name = raw.decode("utf-8", errors="surrogateescape")
        basename = name.rsplit("/", 1)[-1]
        if (basename == ".env" or basename.startswith(".env.")):
            if basename not in _ALLOWED_ENVS:
                return 1
        if _FORBIDDEN.search(name):
            return 1
    return 0


def main():
    status = scan()
    if status == 0:
        print("OMEGA_PRIVATE_FILENAME_GUARD=PASS")
    elif status == 1:
        print("Forbidden private-state filename detected.")
    else:
        print("Tracked filename enumeration failed; fail-closed.")
    return 0 if status == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
