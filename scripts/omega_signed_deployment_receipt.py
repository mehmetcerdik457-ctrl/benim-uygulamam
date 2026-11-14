"""Verify dual-signed, artifact-bound deployment receipts; never authorize production.

Keys must be supplied from an independently trusted source. A valid signature
authenticates a receipt, NOT the truth of the deployment or test assertions.
"""
import base64
import json
import re
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
FIELDS = {"schema", "source_commit", "artifact_sha256", "environment",
          "deployment_id", "deployed_at", "smoke_sha256", "rollback_sha256"}
RECEIPT_FIELDS = FIELDS | {"owner_signature", "auditor_signature"}

class ReceiptError(ValueError):
    pass

def canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")

def verify_receipt(receipt, owner_key_pem, auditor_key_pem, *, commit, artifact_sha256, environment):
    """Return authenticated receipt metadata or raise ReceiptError.

    No trusted keys, signed receipt or exact target binding => failure.
    """
    if not isinstance(receipt, dict) or set(receipt) != RECEIPT_FIELDS:
        raise ReceiptError("invalid receipt fields")
    if receipt["schema"] != "omega.deployment.receipt.v1":
        raise ReceiptError("invalid receipt schema")
    if not isinstance(commit, str) or not HEX40.fullmatch(commit):
        raise ReceiptError("invalid expected commit")
    if not isinstance(artifact_sha256, str) or not HEX64.fullmatch(artifact_sha256):
        raise ReceiptError("invalid expected artifact digest")
    if (receipt["source_commit"], receipt["artifact_sha256"], receipt["environment"]) != (commit, artifact_sha256, environment):
        raise ReceiptError("receipt target mismatch")
    for field in ("smoke_sha256", "rollback_sha256"):
        if not isinstance(receipt[field], str) or not HEX64.fullmatch(receipt[field]):
            raise ReceiptError("invalid evidence digest")
    for field in ("environment", "deployment_id", "deployed_at"):
        value = receipt[field]
        if not isinstance(value, str) or not value.strip() or len(value) > 200:
            raise ReceiptError("invalid receipt metadata")
    try:
        owner = serialization.load_pem_public_key(owner_key_pem)
        auditor = serialization.load_pem_public_key(auditor_key_pem)
        if not isinstance(owner, Ed25519PublicKey) or not isinstance(auditor, Ed25519PublicKey):
            raise ReceiptError("Ed25519 public keys required")
        owner_raw = owner.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        auditor_raw = auditor.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        if owner_raw == auditor_raw:
            raise ReceiptError("owner and auditor keys must differ")
        message = canonical({k: receipt[k] for k in FIELDS})
        for role, key in (("owner", owner), ("auditor", auditor)):
            sig = base64.b64decode(receipt[role + "_signature"], validate=True)
            if len(sig) != 64:
                raise ReceiptError("invalid signature length")
            key.verify(sig, message)
    except (ValueError, TypeError, InvalidSignature, KeyError) as exc:
        raise ReceiptError("receipt signature verification failed") from exc
    return {"authenticated": True, "deployment_id": receipt["deployment_id"],
            "environment": environment, "production_accepted": False}
