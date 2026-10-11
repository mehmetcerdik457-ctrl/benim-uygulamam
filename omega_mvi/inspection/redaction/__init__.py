import re

_REDACTED = "[REDACTED]"
_EMAIL_REDACTED = "[REDACTED_EMAIL]"
_CREDENTIAL_REDACTED = "[REDACTED_CREDENTIAL]"

_PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?"
    r"(?:-----END [A-Z0-9 ]*PRIVATE KEY-----|$)",
    re.DOTALL,
)
_AUTHORIZATION = re.compile(
    r"(\b(?:proxy-)?authorization\s*:\s*(?:bearer|basic)\s+)[^\s,;]+",
    re.IGNORECASE,
)
_BEARER = re.compile(r"(\bbearer\s+)[^\s,;]+", re.IGNORECASE)
_LABELED_CREDENTIAL = re.compile(
    r"(\b(?:api[\s_-]?key|access[\s_-]?token|refresh[\s_-]?token|"
    r"client[\s_-]?secret|password|passwd|secret|token|credential|"
    r"private[\s_-]?key|recovery[\s_-]?code|auth[\s_-]?token)\b\s*[:=]\s*)"
    r'(?:"[^"\r\n]*"|\'[^\'\r\n]*\'|[^\r\n;,]+)',
    re.IGNORECASE,
)
_EMAIL = re.compile(
    r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])",
    re.IGNORECASE,
)
_KNOWN_CREDENTIAL = re.compile(
    r"\b(?:"
    r"(?:sk|rk)[-_](?:live[-_])?[A-Z0-9_-]{4,}|"
    r"(?:gsk|ghp|gho|ghu|ghs|glpat|hf)[-_][A-Z0-9_-]{4,}|"
    r"github_pat_[A-Z0-9_]{4,}|"
    r"xox[baprs]-[A-Z0-9-]{4,}|"
    r"AIza[A-Z0-9_-]{8,}|"
    r"ya29\.[A-Z0-9_-]{8,}|"
    r"AKIA[A-Z0-9]{16}"
    r")\b",
    re.IGNORECASE,
)
_OPAQUE_FRAGMENT = re.compile(
    r"(?<![A-Z0-9])[A-Z0-9][A-Z0-9._~+/=-]{22,}[A-Z0-9](?![A-Z0-9])",
    re.IGNORECASE,
)


def redact_text(text: str) -> str:
    """Redact credential-like fragments and email addresses from text."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    text = _PRIVATE_KEY.sub(_CREDENTIAL_REDACTED, text)
    text = _AUTHORIZATION.sub(rf"\1{_CREDENTIAL_REDACTED}", text)
    text = _BEARER.sub(rf"\1{_CREDENTIAL_REDACTED}", text)
    text = _LABELED_CREDENTIAL.sub(rf"\1{_CREDENTIAL_REDACTED}", text)
    text = _EMAIL.sub(_EMAIL_REDACTED, text)
    text = _KNOWN_CREDENTIAL.sub(_CREDENTIAL_REDACTED, text)
    return _OPAQUE_FRAGMENT.sub(_REDACTED, text)


__all__ = ["redact_text"]
