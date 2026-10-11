import pytest

from omega_mvi.inspection.redaction import redact_text


def test_redacts_plausible_credential_fragments():
    text = "keys: sk-example123, ghp-example123, and gsk-example123"

    redacted = redact_text(text)

    assert "sk-example123" not in redacted
    assert "ghp-example123" not in redacted
    assert "gsk-example123" not in redacted
    assert redacted.count("[REDACTED_CREDENTIAL]") == 3


def test_redacts_bearer_authorization_headers():
    text = "Authorization: " + "Bearer " + "synthetic" + "-bearer-value"

    redacted = redact_text(text)

    assert "synthetic-bearer-value" not in redacted
    assert "[REDACTED_CREDENTIAL]" in redacted


def test_redacts_email_addresses():
    redacted = redact_text("contact synthetic.user@example.invalid for details")

    assert "synthetic.user@example.invalid" not in redacted
    assert "[REDACTED_EMAIL]" in redacted


def test_redacts_labeled_unrecognized_sensitive_material():
    redacted = redact_text("recovery_code: synthetic recovery phrase")

    assert "synthetic recovery phrase" not in redacted
    assert redacted == "recovery_code: [REDACTED_CREDENTIAL]"


def test_fails_closed_on_unrecognized_opaque_fragments():
    fragment = "unknownSyntheticCredentialFragment0123456789"

    redacted = redact_text(f"payload={fragment}")

    assert fragment not in redacted
    assert "[REDACTED]" in redacted


def test_rejects_non_text_input():
    with pytest.raises(TypeError):
        redact_text(None)
