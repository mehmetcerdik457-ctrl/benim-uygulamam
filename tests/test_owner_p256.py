import base64
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import owner_p256 as p
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


def make_signed(body: bytes, timestamp="1700000000", nonce="nonce-for-test-0001", key=None):
    key = key or ec.generate_private_key(ec.SECP256R1())
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    sig = key.sign(p.signed_payload(timestamp, nonce, body), ec.ECDSA(hashes.SHA256()))
    headers = {"X-MEH-Owner-Timestamp": timestamp, "X-MEH-Owner-Nonce": nonce,
               "X-MEH-Owner-Signature": base64.urlsafe_b64encode(sig).decode().rstrip("=")}
    return public, headers, key


def test_valid_signature_and_replay(monkeypatch):
    p._SEEN.clear()
    body = b'{"message":"Merhaba"}'
    public, headers, _ = make_signed(body)
    monkeypatch.setenv("OWNER_P256_PUBLIC_KEY_PEM", public)
    assert p.verify(headers, body, now=1700000000)
    assert not p.verify(headers, body, now=1700000000)


def test_modified_message_denied(monkeypatch):
    p._SEEN.clear()
    body = b'{"message":"A"}'
    public, headers, _ = make_signed(body, nonce="nonce-for-test-0002")
    monkeypatch.setenv("OWNER_P256_PUBLIC_KEY_PEM", public)
    assert not p.verify(headers, b'{"message":"B"}', now=1700000000)
    assert p.verify(headers, body, now=1700000000)


def test_stale_and_missing_config_denied(monkeypatch):
    p._SEEN.clear()
    body = b'{}'
    public, headers, _ = make_signed(body, nonce="nonce-for-test-0003")
    monkeypatch.delenv("OWNER_P256_PUBLIC_KEY_PEM", raising=False)
    assert not p.verify(headers, body, now=1700000000)
    monkeypatch.setenv("OWNER_P256_PUBLIC_KEY_PEM", public)
    assert not p.verify(headers, body, now=1700000500)


def test_wrong_curve_denied(monkeypatch):
    p._SEEN.clear()
    body = b'{}'
    _, headers, _ = make_signed(body, nonce="nonce-for-test-0004")
    key = ec.generate_private_key(ec.SECP384R1())
    wrong = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    monkeypatch.setenv("OWNER_P256_PUBLIC_KEY_PEM", wrong)
    assert not p.verify(headers, body, now=1700000000)


def test_parallel_replay_single_success(monkeypatch):
    p._SEEN.clear()
    body = b'{}'
    public, headers, _ = make_signed(body, nonce="nonce-for-test-0005")
    monkeypatch.setenv("OWNER_P256_PUBLIC_KEY_PEM", public)
    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(lambda _: p.verify(headers, body, now=1700000000), range(20)))
    assert results.count(True) == 1
