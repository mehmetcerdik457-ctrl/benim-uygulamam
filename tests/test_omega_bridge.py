"""Combined legacy + Android HTTP routes. Synthetic providers only, no live keys."""
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import omega_bridge
import server
from omega import gateway, owner_auth_v1


def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def der(key):
    return key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)


class SyntheticProvider:
    name = "openai"
    def __init__(self):
        self.calls = []
        self.actual = "synthetic-provider-snapshot"
    def configured(self):
        return True
    def candidates(self):
        return ("operator-selected-alias",)
    def reply(self, model, message, *, probe=False):
        self.calls.append((model, message, probe))
        return "SENTETİK YANIT", self.actual, 3


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    owner, device = ec.generate_private_key(ec.SECP256R1()), ec.generate_private_key(ec.SECP256R1())
    identity = hashlib.sha256(der(device)).hexdigest()
    fields = {"OMEGA_OWNER_ID": "synthetic-owner", "OMEGA_DEVICE_ID": identity,
              "OMEGA_OWNER_PUBLIC_DER_B64": b64(der(owner)), "OMEGA_DEVICE_PUBLIC_DER_B64": b64(der(device)),
              "OMEGA_NONCE_DB": str(tmp_path / "nonces.sqlite3"), "OMEGA_DATA_DB": str(tmp_path / "data.sqlite3"),
              "OPENAI_API_KEY": "synthetic-never-transmitted", "AI_BACKEND_PROXY_TOKEN": "legacy-synthetic-proxy",
              "OWNER_P256_PUBLIC_KEY_PEM": owner.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()}
    for name, value in fields.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(omega_bridge, "_SERVICE", None)
    monkeypatch.setattr(omega_bridge, "_CONFIG_HASH", None)
    provider = SyntheticProvider()
    omega_bridge._configured_service().provider = provider
    server._rate_buckets.clear()
    server.owner_p256._SEEN.clear()
    legacy_calls = []
    def legacy(*args):
        legacy_calls.append(True)
        return "LEGACY_SYNTHETIC", "legacy-model", "response_synthetic"
    monkeypatch.setattr(server, "call_openai", legacy)
    monkeypatch.setattr(server.Handler, "log_message", lambda *args: None)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    def sign(path, raw, *, delta=0, signed_path=None):
        timestamp, nonce = str(int(time.time()) + delta), uuid.uuid4().hex
        canonical = owner_auth_v1.canonical("POST", signed_path or path, raw, timestamp, nonce, "synthetic-owner", identity)
        return {"Content-Type": "application/json", "X-Omega-Owner-Id": "synthetic-owner", "X-Omega-Device-Id": identity,
                "X-Omega-Timestamp": timestamp, "X-Omega-Nonce": nonce,
                "X-Omega-Owner-Proof": b64(owner.sign(canonical, ec.ECDSA(hashes.SHA256()))),
                "X-Omega-Device-Proof": b64(device.sign(canonical, ec.ECDSA(hashes.SHA256())))}

    def post(path, body, headers=None):
        raw = gateway.json_bytes(body) if isinstance(body, dict) else body
        headers = sign(path, raw) if headers is None else headers
        request = urllib.request.Request("http://127.0.0.1:" + str(httpd.server_port) + path,
            data=raw, headers=headers, method="POST")
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)
    try:
        yield post, sign, provider, legacy_calls
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=3)


def test_android_contract_models_then_chat_without_proxy_secret(runtime):
    post, _, provider, legacy = runtime
    status, data = post(gateway.PREFIX + "models", {})
    assert status == 200 and data["contract"] == "OMEGA-OWNER-API-V1"
    model = data["models"][0]["id"]
    assert model == provider.actual and model != provider.candidates()[0]
    status, data = post(gateway.PREFIX + "chat", {"message": "Merhaba", "model": model, "include_memory": False})
    assert status == 200 and data["text"] == "SENTETİK YANIT" and data["latency_ms"] == 3
    assert data["model"] == model and not legacy


def test_legacy_proxy_keeps_own_authentication(runtime):
    post, _, provider, legacy = runtime
    assert post("/api/chat", {"message": "hello"}, headers={})[0] == 401
    status, data = post("/api/chat", {"message": "hello"}, headers={"X-MEH-Proxy-Token": "legacy-synthetic-proxy"})
    assert status == 200 and data["text"] == "LEGACY_SYNTHETIC"
    assert len(legacy) == 1 and not provider.calls


@pytest.mark.parametrize("extra", [{"X-MEH-Proxy-Token": "legacy-synthetic-proxy"}, {"X-MEH-Owner-Timestamp": "1700000000"}])
def test_mixed_authentication_never_downgrades(runtime, extra):
    post, sign, provider, legacy = runtime
    path = gateway.PREFIX + "chat"
    headers = {**sign(path, b"{}"), **extra}
    status, data = post(path, b"{}", headers=headers)
    assert status == 403 and data["error"] == "MIXED_AUTH_PROTOCOL_DENIED"
    assert not provider.calls and not legacy


def test_partial_omega_header_does_not_fall_back(runtime):
    post, _, provider, legacy = runtime
    status, data = post(gateway.PREFIX + "chat", {}, headers={"Content-Type": "application/json", "X-Omega-Nonce": "bad"})
    assert status == 403 and data["error"] == "OWNER_AUTH_REQUIRED"
    assert not provider.calls and not legacy


def test_mixed_headers_on_legacy_route_are_also_denied(runtime):
    post, _, provider, legacy = runtime
    status, data = post("/api/chat", {"message": "hello"}, headers={
        "X-MEH-Proxy-Token": "legacy-synthetic-proxy", "X-Omega-Nonce": "malformed"})
    assert status == 403 and data["error"] == "MIXED_AUTH_PROTOCOL_DENIED"
    assert not provider.calls and not legacy


def test_missing_dual_enrollment_never_uses_legacy_key(runtime, monkeypatch):
    post, _, provider, legacy = runtime
    monkeypatch.delenv("OMEGA_OWNER_PUBLIC_DER_B64")
    status, data = post(gateway.PREFIX + "models", {})
    assert status == 503 and data["error"] == "OWNER_IDENTITY_NOT_PROVISIONED"
    assert not provider.calls and not legacy


def test_persistent_replay_after_service_recreation(runtime, monkeypatch):
    post, sign, provider, _ = runtime
    path = gateway.PREFIX + "models"
    headers = sign(path, b"{}")
    assert post(path, b"{}", headers=headers)[0] == 200
    monkeypatch.setattr(omega_bridge, "_SERVICE", None)
    monkeypatch.setattr(omega_bridge, "_CONFIG_HASH", None)
    omega_bridge._configured_service().provider = provider
    status, data = post(path, b"{}", headers=headers)
    assert status == 403 and data["error"] == "OWNER_AUTH_REPLAY_OR_STORAGE_DENIED"
    assert len(provider.calls) == 1


def test_full_signed_path_and_expiry_are_enforced(runtime):
    post, sign, provider, _ = runtime
    path = gateway.PREFIX + "models"
    assert post(path, b"{}", headers=sign(path, b"{}", delta=-120))[0] == 403
    assert post(path, b"{}", headers=sign(path, b"{}", signed_path=gateway.PREFIX + "chat"))[0] == 403
    assert post(path + "?ignored=no", b"{}", headers=sign(path, b"{}"))[0] == 404
    assert not provider.calls


def test_model_registry_and_memory_survive_distinct_expected_boundaries(runtime, monkeypatch):
    post, _, provider, _ = runtime
    assert post(gateway.PREFIX + "memory", {"action": "save", "text": "Kahvem şekersiz"})[0] == 200
    monkeypatch.setattr(omega_bridge, "_SERVICE", None)
    monkeypatch.setattr(omega_bridge, "_CONFIG_HASH", None)
    omega_bridge._configured_service().provider = provider
    status, data = post(gateway.PREFIX + "memory", {"action": "recall", "query": "şekersiz"})
    assert status == 200 and data["memories"][0]["text"] == "Kahvem şekersiz"
    assert post(gateway.PREFIX + "chat", {"message": "hello", "model": provider.actual})[0] == 409
    assert not provider.calls


def test_operator_selected_model_only(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "operator-selected-model")
    monkeypatch.setenv("OPENAI_ALLOWED_MODELS", "old-model-1,old-model-2")
    assert omega_bridge.RuntimeProvider().candidates() == ("operator-selected-model",)


def test_database_paths_need_existing_absolute_directories(runtime, monkeypatch):
    post, _, provider, _ = runtime
    monkeypatch.setattr(omega_bridge, "_SERVICE", None)
    monkeypatch.setattr(omega_bridge, "_CONFIG_HASH", None)
    monkeypatch.setenv("OMEGA_DATA_DB", "relative.sqlite3")
    status, data = post(gateway.PREFIX + "models", {})
    assert status == 503 and data["error"] == "OWNER_PERSISTENT_STORAGE_NOT_CONFIGURED"
    assert not provider.calls
