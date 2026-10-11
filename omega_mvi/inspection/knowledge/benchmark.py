"""Opt-in, offline benchmark; no real models are bundled or downloaded."""
from __future__ import annotations
from dataclasses import dataclass
from math import log2
import statistics
import time
import tracemalloc
from typing import Callable, Sequence

@dataclass(frozen=True)
class BenchmarkCase:
    query: str
    relevant_ids: frozenset[str]

@dataclass(frozen=True)
class Candidate:
    name: str
    kind: str  # lexical_baseline, embedding, reranker
    revision: str
    search: Callable[[str, int], Sequence[str]]

def _ndcg(ids, relevant, limit):
    ideal = min(len(relevant), limit)
    if not ideal:
        return 1.0
    dcg = sum(1 / log2(i + 2) for i, key in enumerate(ids[:limit]) if key in relevant)
    return dcg / sum(1 / log2(i + 2) for i in range(ideal))

def evaluate(candidates: Sequence[Candidate], cases: Sequence[BenchmarkCase], *,
             limit: int = 5, repetitions: int = 5) -> tuple[dict, ...]:
    """Observed Python wall time and traced allocations; NOT RSS/VRAM or device power."""
    if type(limit) is not int or limit < 1 or type(repetitions) is not int or repetitions < 1:
        raise ValueError("INVALID_BENCHMARK_PARAMETERS")
    if not cases or not candidates or any(not c.relevant_ids for c in cases):
        raise ValueError("CASES_AND_CANDIDATES_REQUIRED")
    reports = []
    for candidate in candidates:
        if candidate.kind not in {"lexical_baseline", "embedding", "reranker"} or not candidate.revision:
            raise ValueError("CANDIDATE_PROVENANCE_REQUIRED")
        latencies, recalls, ndcgs = [], [], []
        peak_python_bytes = 0
        for case in cases:
            ids = ()
            reference_ranking = None
            for _ in range(repetitions):
                tracemalloc.start()
                try:
                    started = time.perf_counter_ns()
                    ids = tuple(candidate.search(case.query, limit))
                    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
                    _, peak = tracemalloc.get_traced_memory()
                finally:
                    tracemalloc.stop()
                if (len(ids) > limit or any(type(item) is not str or not item for item in ids)
                        or len(ids) != len(set(ids))):
                    raise ValueError("INVALID_CANDIDATE_OUTPUT")
                if reference_ranking is None:
                    reference_ranking = ids
                elif ids != reference_ranking:
                    raise ValueError("UNSTABLE_RANKING")
                latencies.append(elapsed_ms)
                peak_python_bytes = max(peak_python_bytes, peak)
            recalls.append(len(set(ids[:limit]) & case.relevant_ids) / len(case.relevant_ids))
            ndcgs.append(_ndcg(ids, case.relevant_ids, limit))
        ordered = sorted(latencies)
        reports.append({
            "candidate": candidate.name, "kind": candidate.kind, "revision": candidate.revision,
            "number_of_cases": len(cases), "repetitions_per_case": repetitions,
            "recall_at_k": round(statistics.mean(recalls), 4),
            "ndcg_at_k": round(statistics.mean(ndcgs), 4),
            "latency_p50_ms": round(statistics.median(ordered), 4),
            "latency_p95_ms": round(ordered[max(0, int(len(ordered)*.95 + .999999)-1)], 4),
            "python_peak_traced_bytes": peak_python_bytes,
            "gpu_vram_bytes": "NOT_MEASURED", "process_rss_bytes": "NOT_MEASURED",
            "energy_joules": "NOT_MEASURED", "target_owner_device": "NOT_TESTED",
        })
    return tuple(reports)

def synthetic_lexical_candidates() -> tuple[tuple[Candidate, ...], tuple[BenchmarkCase, ...]]:
    docs = {
        "s1": "authorization owner source evidence",
        "s2": "index incremental change revision",
        "s3": "forget revoke cached retrieval",
    }
    def lexical_count(query: str, limit: int):
        tokens = set(query.lower().split())
        pairs = [(len(tokens & set(text.split())), key) for key, text in docs.items()]
        return [key for score, key in sorted(pairs, key=lambda x: (-x[0], x[1])) if score][:limit]
    def lexical_exact(query: str, limit: int):
        return [key for key, text in docs.items() if query.lower() in text][:limit]
    return (
        (Candidate("token_overlap", "lexical_baseline", "fixture-v1", lexical_count),
         Candidate("exact_phrase", "lexical_baseline", "fixture-v1", lexical_exact)),
        (BenchmarkCase("owner authorization", frozenset({"s1"})),
         BenchmarkCase("incremental change", frozenset({"s2"})),
         BenchmarkCase("revoke retrieval", frozenset({"s3"}))),
    )
