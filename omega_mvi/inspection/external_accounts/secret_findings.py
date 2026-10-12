"""OMEGA-017/018: minimal classified findings, never credential values.

Only detector *identifiers* (not matches or raw excerpts) may reach this layer.
No state in this untrusted module can certify provider rotation/revocation.
"""
from dataclasses import dataclass, replace
import re

from omega_mvi.inspection.redaction import redact_text

# A detector name is a hint, not proof that a credential is real or active.
DETECTOR_PROVIDER = {
    "github_pat": "GITHUB",
    "github_oauth": "GITHUB",
    "gitlab_pat": "GITLAB",
    "google_api_key": "GOOGLE_CLOUD",
    "google_service_account_key": "GOOGLE_CLOUD",
    "aws_access_key_id": "AWS",
    "openai_api_key": "OPENAI",
    "slack_token": "SLACK",
    "huggingface_token": "HUGGING_FACE",
}
RISKS = frozenset(("UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"))
STATUSES = frozenset(("NOT_STARTED", "OWNER_REVIEW_REQUIRED",
                      "ROTATION_PLANNED", "ROTATED_VERIFIED",
                      "REVOKED_VERIFIED", "FALSE_POSITIVE_VERIFIED"))
_SAFE_STATUSES = frozenset(("NOT_STARTED", "OWNER_REVIEW_REQUIRED"))
_ALLOWED_PROVIDERS = frozenset(DETECTOR_PROVIDER.values()) | {"UNKNOWN"}
_SAFE_PATH = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\Z")


@dataclass(frozen=True)
class SafeFinding:
    provider_type: str
    source_location: str
    source_line: int
    risk_level: str
    remediation_status: str
    classification: str = "SUSPECTED_UNVERIFIED"

    def __post_init__(self):
        # Frozen dataclasses can still be directly constructed by arbitrary
        # callers. Enforce invariants there, not only in the helper factory.
        if (type(self.provider_type) is not str or
                self.provider_type not in _ALLOWED_PROVIDERS):
            raise ValueError("Provider type must be an allowlisted classification")
        if (type(self.source_location) is not str or
                not 1 <= len(self.source_location) <= 180 or
                not _SAFE_PATH.fullmatch(self.source_location) or
                ".." in self.source_location.split("/") or
                redact_text(self.source_location) != self.source_location):
            raise ValueError("Untrusted or sensitive source path")
        if type(self.source_line) is not int or self.source_line < 1:
            raise ValueError("Source line must be positive integer")
        if type(self.risk_level) is not str or self.risk_level not in RISKS:
            raise ValueError("Risk must be an explicit classification")
        if (type(self.remediation_status) is not str or
                self.remediation_status not in _SAFE_STATUSES):
            raise PermissionError("Only unverified remediation states are allowed")
        if self.classification != "SUSPECTED_UNVERIFIED":
            raise PermissionError("Real provider verification requires independent evidence")

    def as_record(self):
        # Fixed fields; impossible to include matched bytes in the record.
        return {key: getattr(self, key) for key in (
            "provider_type", "source_location", "source_line",
            "risk_level", "remediation_status", "classification")}


def classify_finding(*, detector_id, source_path, line_number, risk="UNKNOWN"):
    if type(detector_id) is not str or len(detector_id) > 80:
        raise ValueError("Detector identifier required")
    if (type(source_path) is not str or len(source_path) > 180
            or not _SAFE_PATH.fullmatch(source_path)
            or ".." in source_path.split("/")
            or redact_text(source_path) != source_path):
        raise ValueError("Only normalized relative source paths are accepted")
    if type(line_number) is not int or line_number < 1:
        raise ValueError("Source line must be positive integer")
    if risk not in RISKS:
        raise ValueError("Risk must be an explicit fixed classification")
    return SafeFinding(provider_type=DETECTOR_PROVIDER.get(detector_id, "UNKNOWN"),
                       source_location=source_path, source_line=line_number,
                       risk_level=risk, remediation_status="NOT_STARTED")


def record_remediation(finding, new_status, *, owner_approved=False,
                       provider_verified=False):
    """Record a decision; no API call, credential handling or actual revocation.

    Approval and verified outcomes are deliberately disabled until separate
    trusted authorization/attestation exists. Boolean flags are NOT proof.
    """
    if not isinstance(finding, SafeFinding) or new_status not in STATUSES:
        raise ValueError("Invalid finding/status")
    if new_status not in _SAFE_STATUSES:
        # Caller-supplied booleans are forgeable. Neither owner approval nor
        # provider verification may be asserted by this untrusted helper.
        raise PermissionError("Approval or attestation requires independent evidence")
    return replace(finding, remediation_status=new_status)
