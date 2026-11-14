import base64
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from scripts.omega_signed_deployment_receipt import canonical, verify_receipt, ReceiptError, FIELDS

class SignedDeploymentReceiptTests(unittest.TestCase):
    def setUp(self):
        self.owner = Ed25519PrivateKey.generate()
        self.auditor = Ed25519PrivateKey.generate()
        self.commit = "a" * 40
        self.digest = "b" * 64
        self.env = "staging"
        self.receipt = {
            "schema": "omega.deployment.receipt.v1",
            "source_commit": self.commit,
            "artifact_sha256": self.digest,
            "environment": self.env,
            "deployment_id": "fixture-123",
            "deployed_at": "2026-11-14T12:00:00Z",
            "smoke_sha256": "c" * 64,
            "rollback_sha256": "d" * 64,
        }
        self.sign()

    def pem(self, private):
        return private.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)

    def sign(self):
        message = canonical({k: self.receipt[k] for k in FIELDS})
        for role, key in (("owner", self.owner), ("auditor", self.auditor)):
            self.receipt[role + "_signature"] = base64.b64encode(key.sign(message)).decode()

    def verify(self, **overrides):
        args = dict(commit=self.commit, artifact_sha256=self.digest, environment=self.env)
        args.update(overrides)
        return verify_receipt(self.receipt, self.pem(self.owner), self.pem(self.auditor), **args)

    def test_valid_synthetic_receipt_not_production_accepted(self):
        verdict = self.verify()
        self.assertTrue(verdict["authenticated"])
        self.assertFalse(verdict["production_accepted"])

    def test_tampered_deployment_rejected(self):
        self.receipt["deployment_id"] = "altered"
        with self.assertRaises(ReceiptError):
            self.verify()

    def test_wrong_target_environment_rejected(self):
        with self.assertRaises(ReceiptError):
            self.verify(environment="production")

    def test_wrong_artifact_rejected(self):
        with self.assertRaises(ReceiptError):
            self.verify(artifact_sha256="e" * 64)

    def test_same_signer_rejected(self):
        with self.assertRaises(ReceiptError):
            verify_receipt(self.receipt, self.pem(self.owner), self.pem(self.owner),
                           commit=self.commit, artifact_sha256=self.digest, environment=self.env)

    def test_wrong_auditor_rejected(self):
        with self.assertRaises(ReceiptError):
            verify_receipt(self.receipt, self.pem(self.owner), self.pem(Ed25519PrivateKey.generate()),
                           commit=self.commit, artifact_sha256=self.digest, environment=self.env)

    def test_unsigned_extra_field_rejected(self):
        self.receipt["override"] = True
        with self.assertRaises(ReceiptError):
            self.verify()

    def test_malformed_base64_signature_rejected(self):
        self.receipt["owner_signature"] = "!!!not-base64!!!"
        with self.assertRaises(ReceiptError):
            self.verify()

    def test_missing_signature_rejected(self):
        del self.receipt["auditor_signature"]
        with self.assertRaises(ReceiptError):
            self.verify()

if __name__ == "__main__":
    unittest.main()
