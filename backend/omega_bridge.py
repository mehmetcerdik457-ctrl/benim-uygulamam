"""Add the Android dual-proof transport without weakening the legacy proxy API.

The two protocols are independent: no client receives the private proxy token,
and no legacy key or caller-supplied key is promoted into an OMEGA identity.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import threading

from omega import gateway, owner_auth_v1

_LOCK = threading.Lock()
_SERVICE = None
_CONFIG_HASH = None
_FIELDS = ("OMEGA_OWNER_ID", "OMEGA_DEVICE_ID", "OMEGA_OWNER_PUBLIC_DER_B64",
           "OMEGA_DEVICE_PUBLIC_DER_B64", "OMEGA_NONCE_DB", "OMEGA_DATA_DB")
_DEDICATED = {gateway.PREFIX + name for name in ("models", "memory", "history", "workers")}


class RuntimeProvider(gateway.OpenAIProvider):
    def candidates(self):
        # The existing service's operator-selected OPENAI_MODEL is the only
        # candidate. Historical, ignored OPENAI_ALLOWED_MODELS is not revived.
        model = os.getenv("OPENAI_MODEL", "gpt-4.1").strip()
        if not gateway.MODEL_ID.fullmatch(model):
            raise gateway.Denied("MODEL_CONFIGURATION_INVALID", 503)
        return (model,)


def _configured_service():
    global _SERVICE, _CONFIG_HASH
    if not owner_auth_v1.configured() or not os.getenv("OMEGA_DATA_DB", "").strip():
        raise gateway.Denied("OWNER_IDENTITY_NOT_PROVISIONED", 503)
    values = tuple(os.environ.get(name, "") for name in _FIELDS)
    fingerprint = hashlib.sha256("\0".join(values).encode()).hexdigest()
    with _LOCK:
        if _SERVICE is not None:
            if _CONFIG_HASH != fingerprint:
                raise gateway.Denied("OWNER_CONFIGURATION_RESTART_REQUIRED", 503)
            return _SERVICE
        nonce_path, data_path = (Path(os.environ[name]) for name in ("OMEGA_NONCE_DB", "OMEGA_DATA_DB"))
        for path in (nonce_path, data_path):
            if not path.is_absolute() or not path.parent.is_dir() or path.is_symlink():
                raise gateway.Denied("OWNER_PERSISTENT_STORAGE_NOT_CONFIGURED", 503)
        if nonce_path.resolve() == data_path.resolve():
            raise gateway.Denied("OWNER_PERSISTENT_STORAGE_NOT_CONFIGURED", 503)
        # Paths must be operator-provisioned on a persistent private volume.
        # Neither /tmp fallback nor an in-process replay cache is permitted.
        try:
            _SERVICE = gateway.Gateway(gateway.Store(str(data_path)), RuntimeProvider())
        except Exception:
            raise gateway.Denied("OWNER_PERSISTENT_STORAGE_UNAVAILABLE", 503) from None
        _CONFIG_HASH = fingerprint
        return _SERVICE


class OmegaRoutes:
    def send_json(self, status, data):
        # The existing handler already applies JSON/no-store/nosniff headers.
        self._send(status, {"contract": gateway.CONTRACT, **data})

    def handle_omega(self):
        path = self.path.split("?", 1)[0]
        omega_headers = any(name.lower().startswith("x-omega-") for name in self.headers)
        if path not in _DEDICATED and not omega_headers:
            return False
        try:
            # Prevent mixed-protocol requests from taking either weaker route.
            if any(name.lower().startswith("x-meh-owner-") or name.lower() == "x-meh-proxy-token"
                   for name in self.headers):
                raise gateway.Denied("MIXED_AUTH_PROTOCOL_DENIED", 403)
            if path not in _DEDICATED and path != gateway.PREFIX + "chat":
                raise gateway.Denied("ROUTE_NOT_FOUND", 404)
            service = _configured_service()
            self.connection.settimeout(10)
            gateway.handler_for(service).do_POST(self)
        except gateway.Denied as exc:
            self.send_json(exc.status, {"error": exc.code})
        finally:
            self.close_connection = True
        return True
