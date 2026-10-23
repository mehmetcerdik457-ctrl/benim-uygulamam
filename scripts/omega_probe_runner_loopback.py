"""Probe CI-runner host loopback without changing the isolated Compose network.

This is NEVER evidence for the owner's own machine. Failure to connect remains an
explicit acceptance BLOCKER, not a disabled security guard or a successful test
of localhost availability. The backend health is asserted in separate Compose
steps, so an unavailable host route cannot silently validate a broken API.
"""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE="http://127.0.0.1:18080"
BLOCKED="OMEGA_RUNNER_HOST_LOOPBACK=BLOCKED_NOT_ACCEPTED"
RUNNER_ONLY="OMEGA_RUNNER_HOST_LOOPBACK=PASS_RUNNER_ONLY_NOT_OWNER"

def probe(opener=urlopen):
    try:
        with opener(BASE+"/api/health",timeout=6) as response:
            data=json.load(response)
    except (URLError,TimeoutError,ConnectionRefusedError):
        return BLOCKED
    if data.get("mode")!="mock" or data.get("production_ready") is not False:
        raise AssertionError("unexpected public readiness")
    request=Request(BASE+"/api/execute",data=b"{}",method="POST",
                    headers={"Content-Type":"application/json"})
    try:
        with opener(request,timeout=6):
            raise AssertionError("execution unexpectedly succeeded")
    except HTTPError as error:
        if error.code!=403:
            raise AssertionError("execution did not deny") from None
    except (URLError,TimeoutError,ConnectionRefusedError):
        raise AssertionError("post request not verified") from None
    return RUNNER_ONLY

def main():
    try:
        result=probe()
    except (AssertionError,ValueError,TypeError,KeyError):
        print("OMEGA_RUNNER_HOST_LOOPBACK=UNSAFE")
        return 1
    print(result)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
