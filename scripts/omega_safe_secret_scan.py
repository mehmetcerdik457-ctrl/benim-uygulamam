"""Fail-closed, output-suppressed credential scan for tracked index AND worktree.

Neither matched bytes, paths, nor raw Git errors are printed. This is a
heuristic defense-in-depth guard, not a substitute for comprehensive scanning.
"""
import subprocess
import sys

PATTERNS = (r"ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
            r"AKIA[0-9A-Z]{16}|sk-(proj-)?[A-Za-z0-9_-]{20,}|"
            r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY")


def scan_quiet(*, cwd=None, runner=subprocess.run):
    # Git's index can contain different bytes from the checked-out working tree.
    # Both are scanned: otherwise a staged secret can evade worktree-only grep.
    for cached in (True, False):
        args=["git", "grep", "-a", "-q", "-E"]
        if cached:
            args.append("--cached")
        args.extend([PATTERNS, "--", "."])
        try:
            result=runner(args, cwd=cwd, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, check=False)
        except (OSError, subprocess.SubprocessError):
            return False
        if result.returncode not in (0, 1):
            return False
        if result.returncode==0:
            return False
    return True


def main():
    if not scan_quiet():
        print("OMEGA_SECRET_SCAN=BLOCKED")
        return 1
    print("OMEGA_SECRET_SCAN=PASS")
    return 0


if __name__=="__main__":
    sys.exit(main())
