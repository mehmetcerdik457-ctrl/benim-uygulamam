"""Authoritative PostgreSQL + four-module runtime check on ONE Compose stack."""
import os
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.main import app
from db import store
from db.migrate import apply, assert_disposable_target


def test_same_runtime_postgres_controls_and_four_inspectors():
    url = os.environ.get("OMEGA_DATABASE_URL")
    marker = os.environ.get("OMEGA_TEST_DB_SENTINEL")
    if not url or not marker:
        if os.environ.get("OMEGA_REQUIRE_REAL_DB") == "1":
            pytest.fail("Disposable PostgreSQL and sentinel required")
        pytest.skip("Requires the isolated, real PostgreSQL Compose test job")

    with psycopg.connect(url, autocommit=True, connect_timeout=3) as conn:
        assert_disposable_target(url, marker, conn)
        apply(conn, "down", database_url=url, sentinel=marker)
        apply(conn, "up", database_url=url, sentinel=marker)
        try:
            tid = store.create(
                conn, "fixture-owner", uuid4(),
                {"kind": "inventory", "source": "synthetic"},
                budget_limit_minor=0,
                permissions=("inventory:read", "rag:read", "pr:read"),
            )
            row = store.get(conn, tid, owner="fixture-owner")
            assert row["state"] == "CREATED"
            assert row["budget_limit_minor"] == 0
            assert row["permissions"] == ["inventory:read", "rag:read", "pr:read"]

            client = TestClient(app)
            snapshot = client.get("/api/inspection/demo")
            assert snapshot.status_code == 200
            payload = snapshot.json()
            assert payload["inventory"]["repository"] == (
                "mehmetcerdik457-ctrl/benim-uygulamam"
            )
            assert len(payload["retrieval"]["citations"]) == 1
            assert payload["pr_review"]["approval_authority"] is False
            assert payload["redaction"]["applied"] is True
            assert payload["real_identity_verified"] is False
            assert client.post("/api/execute").status_code == 403

            store.advance(conn, tid, "PLANNED")
            store.advance(conn, tid, "APPROVAL_PENDING")
            with pytest.raises(psycopg.Error):
                store.advance(conn, tid, "RUNNING", "fake-approval")
            assert store.get(conn, tid, owner="fixture-owner")["state"] == (
                "APPROVAL_PENDING"
            )
        finally:
            apply(conn, "down", database_url=url, sentinel=marker)
