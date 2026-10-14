"""Read-only CI route audit: no default routes in the disposable OMEGA API.

No outbound packets, DNS requests, firewall edits, or daemon changes.
Default-route absence is one check, NOT proof of complete egress prevention.
Never print routes, interfaces, container IDs, environment or Docker errors.
"""
import json
import subprocess


_CONTAINER_PROBE = r"""
import json
from pathlib import Path

def ipv4():
    try:
        lines = Path('/proc/net/route').read_text().splitlines()
        if not lines or 'Destination' not in lines[0]:
            return None
        for line in lines[1:]:
            cols = line.split()
            if len(cols) < 8:
                return None
            if cols[1] == '00000000' and cols[7] == '00000000':
                # A kernel reject default is not a usable route.
                flags = int(cols[3], 16)
                if flags & 0x200:
                    continue
                if cols[0] == 'lo':
                    return None
                return True
        return False
    except (OSError, ValueError):
        return None

def classify_ipv6_default(lines):
    # /proc/net/ipv6_route fields:
    # destination/prefix, source/prefix, gateway, metric, ref, use,
    # flags (hex), interface. Linux RTF_REJECT = 0x200.
    for line in lines:
        cols = line.split()
        if len(cols) < 10:
            return None
        if cols[0] == '0' * 32 and cols[1] == '00':
            try:
                flags = int(cols[8], 16)
            except ValueError:
                return None
            if flags & 0x200:
                continue  # Kernel intentionally rejects this default.
            if cols[9] == 'lo':
                return None  # Unusual non-reject localhost default.
            return True
    return False

def ipv6():
    try:
        lines = Path('/proc/net/ipv6_route').read_text().splitlines()
        return classify_ipv6_default(lines)
    except (OSError, ValueError):
        return None

print(json.dumps({'ipv4_default': ipv4(), 'ipv6_default': ipv6()}))
"""


def audit(runner=subprocess.run):
    try:
        proc = runner(["docker", "compose", "-f", "compose.omega.yml",
                       "exec", "-T", "api", "python", "-c", _CONTAINER_PROBE],
                      capture_output=True, text=True, check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return {"ipv4": "UNVERIFIED", "ipv6": "UNVERIFIED",
                "verdict": "BLOCKED_NOT_ACCEPTED"}
    if proc.returncode != 0 or not isinstance(proc.stdout, str) or len(proc.stdout) > 256:
        return {"ipv4": "UNVERIFIED", "ipv6": "UNVERIFIED",
                "verdict": "BLOCKED_NOT_ACCEPTED"}
    try:
        observed = json.loads(proc.stdout.strip())
    except (TypeError, ValueError):
        observed = {}
    if not isinstance(observed, dict) or set(observed) != {"ipv4_default", "ipv6_default"}:
        observed = {}
    def state(key):
        v = observed.get(key)
        return "PRESENT" if v is True else "ABSENT" if v is False else "UNVERIFIED"
    v4, v6 = state("ipv4_default"), state("ipv6_default")
    if "PRESENT" in (v4, v6):
        verdict = "UNSAFE_DEFAULT_ROUTE_PRESENT"
    elif v4 == "ABSENT" and v6 == "ABSENT":
        verdict = "PASS_ROUTES_ABSENT_NOT_FULL_EGRESS_OR_OWNER_ACCEPTANCE"
    else:
        verdict = "BLOCKED_NOT_ACCEPTED"
    return {"ipv4": v4, "ipv6": v6, "verdict": verdict}


def main():
    report = audit()
    print("OMEGA_EGRESS_ROUTE_IPV4=" + report["ipv4"])
    print("OMEGA_EGRESS_ROUTE_IPV6=" + report["ipv6"])
    print("OMEGA_EGRESS_ROUTE_VERDICT=" + report["verdict"])
    if report["verdict"] == "UNSAFE_DEFAULT_ROUTE_PRESENT":
        return 1
    return (0 if report["verdict"] ==
            "PASS_ROUTES_ABSENT_NOT_FULL_EGRESS_OR_OWNER_ACCEPTANCE" else 2)


if __name__ == "__main__":
    raise SystemExit(main())
