import base64
import hashlib
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from scripts.omega_signed_deployment_receipt import canonical, FIELDS
from scripts.omega_verify_local_bundle import verify_local_bundle, EvidenceBindingError, local_digest

class LocalBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = {"artifact": "app.bin", "smoke": "smoke.json", "rollback": "rollback.json"}
        for key, path in self.paths.items():
            (self.root / path).write_bytes(key.encode())
        self.owner, self.auditor = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
        self.commit = "a" * 40
        self.digest = local_digest(self.root, "app.bin")
        self.receipt = dict(schema="omega.deployment.receipt.v1", source_commit=self.commit,
                            artifact_sha256=self.digest, environment="staging",
                            deployment_id="synthetic", deployed_at="2026-11-17T00:00:00Z",
                            smoke_sha256=local_digest(self.root, "smoke.json"),
                            rollback_sha256=local_digest(self.root, "rollback.json"))
        message = canonical({k: self.receipt[k] for k in FIELDS})
        for role, key in (("owner", self.owner), ("auditor", self.auditor)):
            self.receipt[role + "_signature"] = base64.b64encode(key.sign(message)).decode()

    def pem(self, key):
        return key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)

    def verify(self):
        return verify_local_bundle(self.receipt, self.root, self.paths, self.pem(self.owner),
                                   self.pem(self.auditor), commit=self.commit,
                                   artifact_sha256=self.digest, environment="staging")

    def test_valid_synthetic_bundle_remains_denied(self):
        result = self.verify()
        self.assertTrue(result["local_evidence_hashes_verified"])
        self.assertFalse(result["production_accepted"])

    def test_tampered_artifact_rejected(self):
        (self.root / "app.bin").write_bytes(b"changed")
        with self.assertRaises(EvidenceBindingError):
            self.verify()

    def test_tampered_smoke_rejected(self):
        (self.root / "smoke.json").write_bytes(b"changed")
        with self.assertRaises(EvidenceBindingError):
            self.verify()

    def test_tampered_rollback_rejected(self):
        (self.root / "rollback.json").write_bytes(b"changed")
        with self.assertRaises(EvidenceBindingError):
            self.verify()

    def test_path_traversal_rejected(self):
        self.paths["artifact"] = "../app.bin"
        with self.assertRaises(EvidenceBindingError):
            self.verify()

    def test_symlink_rejected(self):
        (self.root / "alias.bin").symlink_to(self.root / "app.bin")
        self.paths["artifact"] = "alias.bin"
        with self.assertRaises(EvidenceBindingError):
            self.verify()

if __name__ == "__main__":
    unittest.main()
