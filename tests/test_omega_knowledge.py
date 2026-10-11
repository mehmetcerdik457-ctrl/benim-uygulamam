import pytest

from omega_mvi.inspection.knowledge import (
    ControlledIndex, DocumentChange, MemoryEntry, MemoryLedger, ScopeError,
)
from omega_mvi.inspection.knowledge.code_graph import analyze_source
from omega_mvi.inspection.knowledge.benchmark import evaluate, synthetic_lexical_candidates

S = "synthetic://omega-knowledge/source-A"
T = "synthetic://omega-knowledge/source-B"
OWNER = "fixture-owner"

def index():
    return ControlledIndex(owner_id=OWNER, allowlisted_sources=(S, T))

def add(ix, doc="d1", text="quartz change graph", source=S, revision="r1"):
    return ix.rescan((DocumentChange(source, doc, revision, text),),
                     requester_id=OWNER, approved=True)

def test_incremental_rescan_version_change_and_noop():
    ix = index()
    assert add(ix).added == 1
    gen = ix.generation
    assert add(ix).unchanged == 1
    assert ix.generation == gen
    assert add(ix, revision="r2").updated == 1
    assert ix.generation == gen + 1
    assert ix.search("quartz", requester_id=OWNER)[0].revision == "r2"
    assert add(ix, text="quartz revision change").updated == 1

def test_full_batch_is_atomic_on_denial():
    ix = index()
    with pytest.raises(ScopeError, match="SOURCE_NOT_ALLOWED"):
        ix.rescan((DocumentChange(S,"ok","r1","valid synthetic text"),
                   DocumentChange("synthetic://not-approved","x","r1","valid")),
                  requester_id=OWNER, approved=True)
    assert ix.search("valid", requester_id=OWNER) == ()

def test_no_unapproved_or_foreign_access():
    ix = index()
    with pytest.raises(ScopeError, match="SCAN_APPROVAL_REQUIRED"):
        ix.rescan((DocumentChange(S,"a","r1","valid"),), requester_id=OWNER)
    with pytest.raises(ScopeError, match="OWNER_ACCESS_REQUIRED"):
        ix.rescan((), requester_id="stranger", approved=True)
    add(ix)
    with pytest.raises(ScopeError, match="OWNER_ACCESS_REQUIRED"):
        ix.search("quartz", requester_id="stranger")
    assert ix.context("quartz", requester_id=OWNER)

def test_delete_tombstone_blocks_id_and_same_content_under_another_id():
    ix = index()
    add(ix)
    ix.delete_document(S, "d1", requester_id=OWNER, approved=True)
    assert not ix.search("quartz", requester_id=OWNER)
    assert not ix.context("quartz", requester_id=OWNER)
    with pytest.raises(ScopeError, match="TOMBSTONE_DENIED"):
        add(ix)
    with pytest.raises(ScopeError, match="TOMBSTONE_DENIED"):
        add(ix, doc="new-id")
    assert add(ix, doc="fresh", source=T).added == 1

def test_revocation_invalidates_search_context_and_prevents_reingestion():
    ix = index()
    add(ix)
    ix.revoke_source(S, requester_id=OWNER, approved=True)
    assert not ix.search("quartz", requester_id=OWNER)
    assert not ix.context("quartz", requester_id=OWNER)
    with pytest.raises(ScopeError, match="SOURCE_REVOKED"):
        add(ix)
    with pytest.raises(ScopeError, match="SOURCE_REVOKED"):
        add(ix, doc="recreated")

def test_sensitive_content_and_queries_are_rejected_before_persisting():
    ix = index()
    with pytest.raises(ValueError, match="SENSITIVE_CONTENT_REJECTED"):
        add(ix, text="password: placeholder-value")
    assert ix.generation == 0
    add(ix)
    with pytest.raises(ValueError, match="SENSITIVE_QUERY_REJECTED"):
        ix.search("password: placeholder-value", requester_id=OWNER)

def test_memory_levels_explicit_evidence_and_no_silent_auto_promotion():
    ix = index()
    add(ix)
    ledger = MemoryLedger(ix)
    entry = MemoryEntry("m1", S, "d1", "quartz change graph is indexed",
                        "unverified_suggestion")
    ledger.record_suggestion(entry, requester_id=OWNER)
    assert ledger.trusted_context(requester_id=OWNER) == ()
    with pytest.raises(ValueError, match="FACT_APPROVAL_REQUIRED"):
        ledger.promote("m1", requester_id=OWNER, new_state="tested_solution",
                       approver_id="fixture-approver", evidence_ref="synthetic://tests/run-1")
    ledger.promote("m1", requester_id=OWNER, new_state="approved_fact",
                   approver_id="fixture-approver", evidence_ref="synthetic://review/1")
    assert ledger.trusted_context(requester_id=OWNER)[0].state == "approved_fact"
    ledger.promote("m1", requester_id=OWNER, new_state="tested_solution",
                   approver_id="fixture-approver", evidence_ref="synthetic://tests/run-1")
    assert ledger.trusted_context(requester_id=OWNER)[0].state == "tested_solution"
    ix.revoke_source(S, requester_id=OWNER, approved=True)
    assert ledger.trusted_context(requester_id=OWNER) == ()
    assert ledger.inspect(requester_id=OWNER) == ()

def test_memory_no_unauthorized_creation_and_no_pii():
    ix = index()
    add(ix)
    ledger = MemoryLedger(ix)
    with pytest.raises(ScopeError):
        ledger.record_suggestion(MemoryEntry("m",S,"d1","valid","unverified_suggestion"),
                                 requester_id="other")
    with pytest.raises(ValueError, match="SENSITIVE_MEMORY_REJECTED"):
        ledger.record_suggestion(MemoryEntry("m",S,"d1","test@example.com","unverified_suggestion"),
                                 requester_id=OWNER)

def test_static_python_graph_labels_dynamic_calls_and_callback_candidates():
    source = "import json\ndef outer(callback):\n    callback(1)\n    x = getattr(obj, 'run')\n    x()\n    return lambda z: z\n"
    edges = analyze_source("python", source)
    assert any(e.kind == "definition" and e.target == "outer" for e in edges)
    assert any(e.kind == "import" and e.target == "json" for e in edges)
    assert any(e.kind == "call" and e.target == "getattr" and e.confidence == "unknown" for e in edges)
    assert any(e.kind == "callback" and e.target == "<lambda>" for e in edges)

@pytest.mark.parametrize("language", ("javascript", "typescript"))
def test_js_ts_graph_is_heuristic_and_dynamic_unresolved(language):
    code = "function run() { handler(); thing[key](); }\nconst cb = (x) => x;\nsetTimeout((x) => x, 1);\n"
    edges = analyze_source(language, code)
    assert any(e.kind == "definition" and e.target == "run" for e in edges)
    assert any(e.kind == "callback_or_arrow_definition" and e.target == "cb" for e in edges)
    assert any(e.kind == "call_candidate" and e.target == "handler" for e in edges)
    assert any(e.kind == "dynamic_call" for e in edges)
    assert all(e.confidence in ("heuristic", "unknown") for e in edges)

def test_benchmark_smoke_does_not_claim_real_embedding_or_reranker():
    cands, cases = synthetic_lexical_candidates()
    rows = evaluate(cands, cases, limit=2, repetitions=2)
    assert len(rows) == 2
    assert all(row["kind"] == "lexical_baseline" for row in rows)
    assert all(0 <= row["recall_at_k"] <= 1 for row in rows)
    assert all(row["target_owner_device"] == "NOT_TESTED" for row in rows)

def test_revocation_and_deletion_require_explicit_approval():
    ix = index()
    add(ix)
    with pytest.raises(ScopeError, match="DELETE_APPROVAL_REQUIRED"):
        ix.delete_document(S, "d1", requester_id=OWNER)
    with pytest.raises(ScopeError, match="REVOCATION_APPROVAL_REQUIRED"):
        ix.revoke_source(S, requester_id=OWNER)
    assert ix.search("quartz", requester_id=OWNER)

def test_duplicate_batch_rejected_without_partial_mutations():
    ix = index()
    with pytest.raises(ValueError, match="DUPLICATE_ID_IN_SCAN"):
        ix.rescan((DocumentChange(S,"same","a","first"),
                   DocumentChange(S,"same","b","second")),
                  requester_id=OWNER, approved=True)
    assert ix.generation == 0

def test_memory_cannot_be_reintroduced_after_delete():
    ix = index()
    add(ix)
    ledger = MemoryLedger(ix)
    item = MemoryEntry("m", S, "d1", "quartz", "unverified_suggestion")
    ledger.record_suggestion(item, requester_id=OWNER)
    ix.delete_document(S, "d1", requester_id=OWNER, approved=True)
    assert ledger.inspect(requester_id=OWNER) == ()
    with pytest.raises(ScopeError, match="SOURCE_NOT_ACTIVE"):
        ledger.record_suggestion(MemoryEntry("m2",S,"d1","quartz","unverified_suggestion"),
                                 requester_id=OWNER)

def test_no_active_records_for_source_outside_allowlist():
    ix = index()
    with pytest.raises(ScopeError, match="SOURCE_NOT_ALLOWED"):
        ix.rescan((DocumentChange("synthetic://outside","doc","r1","hello"),),
                  requester_id=OWNER, approved=True)
    assert ix.context("hello", requester_id=OWNER) == ()

def test_existing_repo_python_pipeline_call_graph_without_executing_source():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    source = (root / "omega_mvi/inspection/pipeline.py").read_text(encoding="utf-8")
    edges = analyze_source("python", source)
    assert any(e.kind == "definition" and e.target == "inspect_offline_fixture" for e in edges)
    assert any(e.kind == "call" and e.target == "redact_text" for e in edges)
    assert any(e.kind == "call" and e.confidence == "syntax_only" for e in edges)

def test_existing_repo_dashboard_js_call_graph_preserves_uncertainty():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    source = (root / "omega_mvi/app/static/dashboard.js").read_text(encoding="utf-8")
    edges = analyze_source("javascript", source)
    assert any(e.kind == "definition" and e.target == "refresh" for e in edges)
    assert any(e.kind == "call_candidate" and e.target == "Promise.all" for e in edges)
    assert all(e.confidence != "resolved_runtime" for e in edges)


# Phase 2: complete-snapshot semantics, race safety, and stale-context barriers.
def test_full_snapshot_tombstones_missing_document_without_affecting_others():
    ix = index()
    ix.rescan((DocumentChange(S, "old", "r1", "quartz old revision"),
               DocumentChange(S, "keep", "r1", "amber keep revision")),
              requester_id=OWNER, approved=True)
    first = ix.generation
    result = ix.replace_source_snapshot(S, (DocumentChange(S, "keep", "r1", "amber keep revision"),),
                                        requester_id=OWNER, approved=True)
    assert (result.removed, result.unchanged) == (1, 1)
    assert ix.generation == first + 1
    assert ix.search("quartz", requester_id=OWNER) == ()
    assert [hit.document_id for hit in ix.search("amber", requester_id=OWNER)] == ["keep"]
    with pytest.raises(ScopeError, match="TOMBSTONE_DENIED"):
        add(ix, doc="old", text="quartz old revision")
    with pytest.raises(ScopeError, match="TOMBSTONE_DENIED"):
        add(ix, doc="recreated", text="quartz old revision")

def test_snapshot_same_content_rename_is_rejected_atomically():
    ix = index()
    add(ix)
    before = ix.generation
    with pytest.raises(ScopeError, match="TOMBSTONE_DENIED"):
        ix.replace_source_snapshot(S, (DocumentChange(S, "renamed", "r2", "quartz change graph"),),
                                   requester_id=OWNER, approved=True)
    assert ix.generation == before
    assert [hit.document_id for hit in ix.search("quartz", requester_id=OWNER)] == ["d1"]

def test_snapshot_cross_source_and_unapproved_actions_fail_closed():
    ix = index()
    add(ix)
    with pytest.raises(ScopeError, match="SNAPSHOT_APPROVAL_REQUIRED"):
        ix.replace_source_snapshot(S, (), requester_id=OWNER)
    with pytest.raises(ValueError, match="INVALID_SNAPSHOT_SCOPE"):
        ix.replace_source_snapshot(S, (DocumentChange(T, "wrong", "r1", "clean"),),
                                   requester_id=OWNER, approved=True)
    assert ix.search("quartz", requester_id=OWNER)
    with pytest.raises(ScopeError, match="OWNER_ACCESS_REQUIRED"):
        ix.replace_source_snapshot(S, (), requester_id="foreign", approved=True)

def test_empty_complete_snapshot_removes_all_and_blocks_recreation():
    ix = index()
    add(ix)
    before = ix.generation
    result = ix.replace_source_snapshot(S, (), requester_id=OWNER, approved=True)
    assert result.removed == 1 and ix.generation == before + 1
    assert ix.context("quartz", requester_id=OWNER) == ()
    with pytest.raises(ScopeError, match="TOMBSTONE_DENIED"):
        add(ix)
    assert ix.replace_source_snapshot(S, (), requester_id=OWNER, approved=True).removed == 0

def test_retained_model_context_requires_fresh_generation_validation():
    ix = index()
    add(ix)
    generation, data = ix.context_snapshot("quartz", requester_id=OWNER)
    assert data == ("quartz change graph",)
    ix.assert_context_current(generation, requester_id=OWNER)
    with pytest.raises(ScopeError, match="STALE_CONTEXT"):
        ix.assert_context_current(True, requester_id=OWNER)
    ix.revoke_source(S, requester_id=OWNER, approved=True)
    with pytest.raises(ScopeError, match="STALE_CONTEXT"):
        ix.assert_context_current(generation, requester_id=OWNER)
    assert ix.context_snapshot("quartz", requester_id=OWNER)[1] == ()

def test_unrelated_source_is_not_globally_erased_by_scoped_tombstone():
    ix = index()
    add(ix)
    ix.delete_document(S, "d1", requester_id=OWNER, approved=True)
    assert add(ix, doc="another-source", source=T).added == 1
    assert [hit.source_ref for hit in ix.search("quartz", requester_id=OWNER)] == [T]

def test_threaded_rescan_then_revoke_cannot_leave_stale_hit(monkeypatch):
    import threading
    from omega_mvi.inspection import knowledge
    ix = index()
    entered = threading.Event()
    release = threading.Event()
    original = knowledge.redact_text
    failures = []

    def intercept(text):
        if text == "quartz concurrent":
            entered.set()
            if not release.wait(4):
                raise RuntimeError("test event timeout")
        return original(text)

    def scan():
        try:
            add(ix, text="quartz concurrent")
        except BaseException as exc:
            failures.append(exc)

    monkeypatch.setattr(knowledge, "redact_text", intercept)
    writer = threading.Thread(target=scan)
    writer.start()
    try:
        assert entered.wait(4), "scan never reached validation"
        revoker = threading.Thread(target=lambda: ix.revoke_source(S, requester_id=OWNER, approved=True))
        revoker.start()
    finally:
        release.set()
    writer.join(5)
    revoker.join(5)
    assert not writer.is_alive() and not revoker.is_alive()
    assert not failures
    assert ix.context("quartz", requester_id=OWNER) == ()
    with pytest.raises(ScopeError, match="SOURCE_REVOKED"):
        add(ix, text="quartz concurrent")

def test_memory_context_generation_fails_after_document_removed():
    ix = index()
    add(ix)
    ledger = MemoryLedger(ix)
    ledger.record_suggestion(MemoryEntry("m", S, "d1", "quartz", "unverified_suggestion"),
                             requester_id=OWNER)
    ledger.promote("m", requester_id=OWNER, new_state="approved_fact",
                   approver_id="fixture-reviewer", evidence_ref="synthetic://review/1")
    old_generation = ix.generation
    assert len(ledger.trusted_context(requester_id=OWNER)) == 1
    ix.replace_source_snapshot(S, (), requester_id=OWNER, approved=True)
    with pytest.raises(ScopeError, match="STALE_CONTEXT"):
        ix.assert_context_current(old_generation, requester_id=OWNER)
    assert ledger.trusted_context(requester_id=OWNER) == ()
