"""Fail-closed host gateway tests: no external network, no credentials."""
import importlib.util
import io
import json
import sys
from pathlib import Path
from urllib.error import HTTPError

import pytest
import yaml

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from omega_host_gateway_acceptance import diagnose

spec=importlib.util.spec_from_file_location("omega_host_gateway", ROOT/"omega_host_gateway/gateway.py")
gateway=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)


class Response(io.BytesIO):
    status=200
    def __enter__(self): return self
    def __exit__(self,*args): self.close()


def test_gateway_exposes_only_approved_routes_and_no_client_headers():
    calls=[]
    def opener(req,timeout):
        calls.append((req.full_url, req.method, set(req.headers)))
        if req.full_url.endswith("/api/health"):
            return Response(b'{"mode":"mock","production_ready":false,"secret":"never-forward"}')
        raise HTTPError(req.full_url,403,"refused",None,io.BytesIO(b'{"error":"DENIED"}'))
    assert gateway._upstream_request("/api/health",opener=opener)==(
        200,b'{"mode":"mock","production_ready":false}')
    assert gateway._upstream_request("/api/execute",data=b"{}",opener=opener)==(
        403,b'{"error":"EXECUTION_DENIED"}')
    assert len(calls)==2
    assert all(url.startswith("http://api:8000/api/") for url,_,_ in calls)
    assert all("Authorization" not in headers and "Cookie" not in headers for _,_,headers in calls)


def test_gateway_fails_closed_if_upstream_executes():
    def opener(req,timeout): return Response(b'{"status":"ran"}')
    assert gateway._upstream_request("/api/execute",data=b"{}",opener=opener)==(
        503,b'{"error":"UPSTREAM_EXECUTION_POLICY_FAULT"}')


def test_gateway_no_unapproved_client_method_or_query():
    class Dummy(gateway.Handler):
        def __init__(self,method,path,body=b""):
            self.path=path
            self.headers={"Content-Length":str(len(body))}
            self.rfile=io.BytesIO(body)
            self.replies=[]
        def _reply(self,status,payload): self.replies.append((status,payload))
    for method,path,expected in [
        ("do_GET","/api/models",404),
        ("do_GET","/api/health?token=private",404),
        ("do_POST","/api/chat",403),
        ("do_POST","/api/v1/owner/chat",403),
        ("do_POST","/api/execute?next=https://example.invalid",403),
    ]:
        request=Dummy(method,path)
        getattr(request,method)()
        assert request.replies[0][0]==expected


def test_overlay_removes_api_port_and_never_publishes_database():
    source=(ROOT/"compose.omega-host.yml").read_text()
    assert "ports: !reset []" in source
    assert '127.0.0.1:18081:8080' in source
    assert "0.0.0.0" not in source
    assert "internal: false" in source # only host-facing gateway network
    assert "internal: true" in (ROOT/"compose.omega.yml").read_text()


def test_runner_diag_fails_closed_with_unknown_containers(monkeypatch):
    import omega_host_gateway_acceptance as a
    monkeypatch.setattr(a,"_container",lambda *args,**kwargs: None)
    assert a.diagnose()=="BLOCKED_INSPECT_UNAVAILABLE"


def test_runner_diag_rejects_direct_backend_host_mapping(monkeypatch):
    import omega_host_gateway_acceptance as a
    cases={"api":{"ports":{"8000/tcp":[{"HostIp":"127.0.0.1","HostPort":"18080"}]},
                  "internal":[True]},
           "db":{"ports":{},"internal":[True]},
           "host-gateway":{"ports":{"8080/tcp":[{"HostIp":"127.0.0.1","HostPort":"18081"}]},
                           "internal":[False,True]}}
    monkeypatch.setattr(a,"_container",lambda name,**kw: cases[name])
    assert a.diagnose()=="UNSAFE_DIRECT_HOST_MAPPING"


def test_runner_diag_rejects_publicly_published_gateway(monkeypatch):
    import omega_host_gateway_acceptance as a
    cases={"api":{"ports":{"8000/tcp":None},"internal":[True]},
           "db":{"ports":{"5432/tcp":None},"internal":[True]},
           "host-gateway":{"ports":{"8080/tcp":[{"HostIp":"0.0.0.0","HostPort":"18081"}]},
                           "internal":[False,True]}}
    monkeypatch.setattr(a,"_container",lambda name,**kw: cases[name])
    assert a.diagnose()=="UNSAFE_GATEWAY_BINDING"


def test_runner_diag_rejects_missing_isolation(monkeypatch):
    import omega_host_gateway_acceptance as a
    cases={"api":{"ports":{},"internal":[False]},
           "db":{"ports":{},"internal":[True]},
           "host-gateway":{"ports":{"8080/tcp":[{"HostIp":"127.0.0.1","HostPort":"18081"}]},
                           "internal":[False,True]}}
    monkeypatch.setattr(a,"_container",lambda name,**kw: cases[name])
    assert a.diagnose()=="UNSAFE_PRIVATE_NETWORK"
