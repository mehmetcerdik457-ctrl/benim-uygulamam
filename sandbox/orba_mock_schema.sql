-- Disposable local/CI PostgreSQL fixture only. Never apply to production.
CREATE TABLE sandbox_billing_events (
    provider TEXT NOT NULL CHECK(provider='local-mock'),
    event_id TEXT NOT NULL, owner_id TEXT NOT NULL, user_id TEXT NOT NULL,
    product_id TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN
    ('MOCK_PURCHASED','MOCK_RENEWED','MOCK_PENDING','MOCK_REFUNDED','MOCK_EXPIRED','MOCK_CANCELED')),
    fingerprint CHAR(64) NOT NULL, created_at TIMESTAMPTZ DEFAULT clock_timestamp(),
    PRIMARY KEY(provider,event_id)
);
CREATE TABLE sandbox_entitlements (
    owner_id TEXT NOT NULL, user_id TEXT NOT NULL, product_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('ACTIVE','INACTIVE')), last_event_id TEXT NOT NULL,
    PRIMARY KEY(owner_id,user_id,product_id)
);
