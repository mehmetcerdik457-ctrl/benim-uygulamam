# Owner P-256 signed chat contract

This change adds POST /api/v1/owner/chat to the existing private P1 backend.
It **does not** enroll or manufacture an owner credential, change Railway secrets,
or claim a live OpenAI provider response.

## Required server configuration

- OPENAI_API_KEY: existing Railway secret (preserved)
- AI_BACKEND_PROXY_TOKEN: existing private runtime-to-backend secret (preserved)
- OWNER_P256_PUBLIC_KEY_PEM: **owner-verified** P-256 SPKI PEM public key, provisioned separately after device/owner enrollment. Never derive it from an untrusted caller-supplied key, and never publish the private signing key.

The owner endpoint fails closed with 503 if the public key is not provisioned.
Existing POST /api/chat remains private proxy-authenticated and unchanged.

## Request

Use the existing private proxy header X-MEH-Proxy-Token, plus:

- X-MEH-Owner-Timestamp: 10-digit Unix timestamp in seconds (within 120s)
- X-MEH-Owner-Nonce: cryptographically random, base64url-safe 16–128 characters
- X-MEH-Owner-Signature: base64url-encoded DER ECDSA P-256/SHA-256 signature

The bytes signed, in order, are:

    b"MEHMET_OWNER_CHAT_V1\n" +
    timestamp_ascii + b"\n" +
    nonce_ascii + b"\n" +
    sha256(raw_http_body_bytes).hexdigest().encode("ascii")

The submitted JSON body uses the existing backend /api/chat schema.
Nonce replay is rejected, with atomic consumption and bounded in-process storage.
One-use nonces are **per backend process**: for multi-replica deployments,
replace in-memory nonce storage with an atomic shared data store before approval.

## Acceptance boundary

1. Local contract tests passing does not prove Android Keystore enrollment.
2. A Railway deployment does not prove a valid paid OpenAI provider response.
3. Production acceptance requires trusted owner public key enrollment,
   a verified server deployment, a signed Android hardware request,
   and a genuine OpenAI model response with HTTP 200.
4. Do not copy old API keys from documents into deployed secrets automatically.
