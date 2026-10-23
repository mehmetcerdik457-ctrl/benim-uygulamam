"""Synthetic runner-host probe tests: no live outbound connections."""
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from omega_probe_runner_loopback import BLOCKED,RUNNER_ONLY,probe

class Response(BytesIO):
    def __enter__(self):
        return self
    def __exit__(self,*args):
        self.close()

def test_isolated_compose_runner_host_unreachable_is_visible_blocker():
    def refuse(*args,**kwargs):
        raise URLError("synthetic blocked loopback")
    assert probe(opener=refuse)==BLOCKED
    assert "NOT_ACCEPTED" in BLOCKED

def test_when_runner_host_is_reachable_it_must_prove_execution_denied():
    def opener(request,**kwargs):
        if isinstance(request,str):
            return Response(b'{"mode":"mock","production_ready":false}')
        raise HTTPError("http://localhost.invalid",403,"DENIED",None,None)
    assert probe(opener=opener)==RUNNER_ONLY
    assert "NOT_OWNER" in RUNNER_ONLY

def test_incorrect_mode_is_never_reported_as_healthy():
    def fake(*args,**kwargs):
        return Response(b'{"mode":"production","production_ready":true}')
    with pytest.raises(AssertionError):
        probe(opener=fake)

def test_executable_endpoint_returning_2xx_is_security_failure():
    def fake(request,**kwargs):
        if isinstance(request,str):
            return Response(b'{"mode":"mock","production_ready":false}')
        return Response(b'{"status":"unexpected"}')
    with pytest.raises(AssertionError):
        probe(opener=fake)

def test_non_403_response_must_not_count_as_denied():
    def fake(request,**kwargs):
        if isinstance(request,str):
            return Response(b'{"mode":"mock","production_ready":false}')
        raise HTTPError("http://localhost.invalid",500,"error",None,None)
    with pytest.raises(AssertionError):
        probe(opener=fake)
