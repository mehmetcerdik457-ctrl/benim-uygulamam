"""Synthetic lexical smoke benchmark ONLY; not a real model benchmark."""
import json
from omega_mvi.inspection.knowledge.benchmark import evaluate, synthetic_lexical_candidates

if __name__ == "__main__":
    candidates, cases = synthetic_lexical_candidates()
    print(json.dumps({"scope": "synthetic_lexical_smoke_only",
                      "embedding_models": "SKIP_NOT_INSTALLED",
                      "reranker_models": "SKIP_NOT_INSTALLED",
                      "data": evaluate(candidates, cases)}, indent=2))
