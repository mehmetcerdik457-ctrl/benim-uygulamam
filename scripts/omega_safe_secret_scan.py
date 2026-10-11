"""Quiet Git credential guard: never emit a matched line, path or secret value."""
import subprocess
import sys

PATTERNS = (r"ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
            r"AKIA[0-9A-Z]{16}|sk-(proj-)?[A-Za-z0-9_-]{20,}|"
            r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY")

def scan_quiet(*, cwd=None, runner=subprocess.run):
    # No shell expansion and no line/filename output, even on a match.
    result=runner(["git","grep","-I","-q","-E",PATTERNS,"--","."],
                  cwd=cwd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
    if result.returncode==0:
        return False
    if result.returncode==1:
        return True
    return False  # Git errors fail closed as well.

def main():
    if not scan_quiet():
        print("OMEGA_SECRET_SCAN=BLOCKED")  # generic non-identifying status
        return 1
    print("OMEGA_SECRET_SCAN=PASS")
    return 0

if __name__=="__main__":
    sys.exit(main())
