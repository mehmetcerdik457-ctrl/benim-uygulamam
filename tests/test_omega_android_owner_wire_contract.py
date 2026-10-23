"""Exact byte-vector parity with the existing Android OmegaV1EnvelopeTest.java.

Android source: Gpt-asistan commit 639ac11db15ea658992c5b91b9c33c1a767902f6
Java test Git blob: c8726bffa22a498e65c000e4a450f173e62ed9bb
No Android Keystore or physical phone is executed by this Python test.
"""
import hashlib
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
import owner_auth_v1 as auth

NONCE="0123456789abcdef0123456789abcdef"
DEVICE="a"*64

def test_android_java_reference_exact_canonical_bytes():
    expected=(
        "OMEGA-OWNER-API-V1\\nPOST\\n/api/v1/owner/chat\\n"
        "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a\\n"
        "1792440000\\n"+NONCE+"\\nowner-test\\n"+DEVICE
    ).encode("utf-8")
    assert auth.canonical("POST",auth.PATH,b"{}","1792440000",NONCE,"owner-test",DEVICE)==expected

def test_signed_message_changes_when_body_changes():
    a=auth.canonical("POST",auth.PATH,b'{"a":1}',"1792440000",NONCE,"owner-test",DEVICE)
    b=auth.canonical("POST",auth.PATH,b'{"a":2}',"1792440000",NONCE,"owner-test",DEVICE)
    assert a!=b and hashlib.sha256(b'{"a":1}').hexdigest().encode() in a
