"""OMEGA-092 fixture-only telemetry contract. No exporter, Grafana or live data."""
import math
from typing import Any

# Lower-cardinality, allowlisted sample types; real source and dashboard remain NOTRUN.
BOUNDS = {
    "omega_http_errors_total": (0, 1000000000),
    "omega_http_latency_p95_ms": (0, 60000),
    "omega_task_queue_depth": (0, 100000),
    "omega_model_latency_p95_ms": (0, 60000),
    "omega_model_errors_total": (0, 1000000000),
    "omega_cpu_usage_percent": (0, 100),
    "omega_memory_bytes": (0, 10**13),
    "omega_gpu_memory_bytes": (0, 10**13),
    "omega_disk_free_bytes": (0, 10**16),
}
_FIELDS = frozenset(("name", "value", "observed_at", "origin"))


def validate_synthetic_samples(samples: Any, now: int) -> dict:
    """Reject labels, private metadata, missing/stale and nonfinite samples.

    The returned verdict is solely a fixture contract: never accept production.
    """
    reasons = []
    if type(now) is not int or now <= 0:
        return {"fixture": "BLOCKED", "grafana_accepted": False, "reason": "clock_invalid"}
    if type(samples) not in (list, tuple) or len(samples) != len(BOUNDS):
        return {"fixture": "BLOCKED", "grafana_accepted": False, "reason": "sample_count_invalid"}
    names = set()
    for sample in samples:
        if type(sample) is not dict or set(sample.keys()) != _FIELDS:
            reasons.append("unexpected_fields")
            continue
        name = sample.get("name")
        if type(name) is not str or name not in BOUNDS or name in names:
            reasons.append("metric_invalid_or_duplicate")
            continue
        names.add(name)
        if sample["origin"] != "synthetic-disposable-only":
            reasons.append("origin_invalid")
        timestamp = sample["observed_at"]
        if type(timestamp) is not int or not 0 <= now - timestamp <= 120:
            reasons.append("timestamp_stale_or_future")
        value = sample["value"]
        low, high = BOUNDS[name]
        # Check bounds before floating conversion, so huge integers cannot overflow
        # math.isfinite() and bypass the fail-closed result.
        if (type(value) not in (float, int) or not low <= value <= high
                or (type(value) is float and not math.isfinite(value))):
            reasons.append("value_invalid")
    if len(names) != len(BOUNDS):
        reasons.append("missing_metric")
    return {"fixture": "BLOCKED" if reasons else "VALID_SYNTHETIC_ONLY",
            "grafana_accepted": False,
            "reason": ",".join(sorted(set(reasons))) if reasons else "none"}


if __name__ == "__main__":
    print("OMEGA_GRAFANA_REAL_METRICS=NOTRUN")
    print("OMEGA_GRAFANA_ACCEPTED=FALSE")
