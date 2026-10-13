"""Cross-specialist synthetic integration: NO LIVE IAM, networking, model or DB."""
import asyncio
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4
import pytest

from omega_mvi.inspection.provenance import make_fixture_record, build_index
from omega_mvi.inspection.provenance.policy import review_provenance_changes
from omega_mvi.inspection.knowledge import ControlledIndex, DocumentChange, ScopeError
from omega_mvi.security.offline_contract import SecurityDenied, require_live_identity, require_live_oidc
from omega_mvi.orchestration.offline import OfflineTask, OfflineMcpFixtureRegistry, run_offline
from omega_mvi.model_adapter.router import ModelRouter, RouteRequest, RouteDenied


def test_provenance_deletion_and_search_are_fail_closed_together():
    content = b"omega synthetic alpha"
    digest = sha256(b"").hexdigest()
    meta = dict(kind="regular_file", size_bytes=len(content), mtime_ns=1,
                mode=0o400, uid=1000, gid=1000, acl_sha256=digest,
                xattr_sha256=digest)
    record = make_fixture_record(source_ref="synthetic://omega-repo",
        relative_path="guide.md", source_version="v1", data=content,
        metadata=meta, owner_ref="owner:fixture", access_level="public",
        verified_at="2026-10-13T00:00:00Z", retention_days=30)
    old = build_index([record], version=1)
    new = build_index([], version=2, previous=old)
    decision = review_provenance_changes(old, new)
    assert decision["requires_external_review"] is True
    assert decision["approval_granted"] is False
    assert decision["deletion_authorized"] is False

    index = ControlledIndex(owner_id="fixture-owner",
                             allowlisted_sources={"synthetic://omega-repo"})
    change = DocumentChange("synthetic://omega-repo", "guide.md", "v1",
                            content.decode("utf-8"))
    with pytest.raises(ScopeError):
        index.rescan([change], requester_id="fixture-owner")
    index.rescan([change], requester_id="fixture-owner", approved=True)
    assert len(index.search("alpha", requester_id="fixture-owner")) == 1
    with pytest.raises(ScopeError):
        index.search("alpha", requester_id="stranger")
    generation, context = index.context_snapshot("alpha", requester_id="fixture-owner")
    assert context
    index.delete_document("synthetic://omega-repo", "guide.md",
                          requester_id="fixture-owner", approved=True)
    assert index.search("alpha", requester_id="fixture-owner") == ()
    assert index.context("alpha", requester_id="fixture-owner") == ()
    with pytest.raises(ScopeError):
        index.assert_context_current(generation, requester_id="fixture-owner")
    with pytest.raises(ScopeError):
        index.rescan([change], requester_id="fixture-owner", approved=True)


def test_unconfigured_live_identity_and_unregistered_mcp_deny():
    with pytest.raises(SecurityDenied):
        require_live_identity("synthetic-fixture")
    with pytest.raises(SecurityDenied):
        require_live_oidc("synthetic-jwt")
    task = OfflineTask(task_id=uuid4(), owner="fixture-owner", trace_id=uuid4(),
                       permissions=frozenset({"rag:read"}), budget_limit_minor=0,
                       deadline_utc=datetime.now(timezone.utc)+timedelta(minutes=1))
    report = run_offline(task, OfflineMcpFixtureRegistry())
    assert report.status == "DENIED"
    assert report.production_authorized is False


def test_model_router_cannot_infer_without_authorized_local_backend():
    router = ModelRouter([])
    request = RouteRequest(task="code", prompt="synthetic test only",
                           max_input_tokens=64, max_output_tokens=8,
                           max_total_tokens=72)
    with pytest.raises(RouteDenied):
        asyncio.run(router.generate(request))
