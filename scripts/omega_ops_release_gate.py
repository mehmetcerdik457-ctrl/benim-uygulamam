"""OMEGA-090 offline release regression comparison: NO deployment authority.

Inputs are untrusted, synthetic or independently collected summary records. Passing
this comparison does NOT verify signatures, owner identity, source provenance, or
unfreeze any service. No network, secrets, repository writes or output of input data.
"""
import re
from typing import Any

SHA = re.compile(r"[0-9a-f]{40}\Z")
REQUIRED = ("privacy_guard", "postgres_restore", "execution_denial",
            "regression_suite", "runner_host_acceptance")


def _valid_check(value: Any) -> bool:
    return (type(value) is dict
            and value.get("conclusion") == "success"
            and type(value.get("passed")) is int and value["passed"] >= 1
            and type(value.get("failed")) is int and value["failed"] == 0
            and type(value.get("skipped")) is int and value["skipped"] == 0)


def compare_untrusted_summaries(baseline: Any, candidate: Any) -> dict:
    """Fail closed; use fixed reason codes, never echo supplied strings."""
    reasons = []
    for name, doc in (("baseline", baseline), ("candidate", candidate)):
        if type(doc) is not dict:
            reasons.append(name + "_invalid")
            continue
        if not isinstance(doc.get("sha"), str) or not SHA.fullmatch(doc["sha"]):
            reasons.append(name + "_sha_invalid")
        if doc.get("scope") != "disposable-synthetic-ci":
            reasons.append(name + "_scope_invalid")
        if type(doc.get("checks")) is not dict:
            reasons.append(name + "_checks_invalid")
    if reasons:
        return {"comparison": "BLOCKED", "release_authorized": False,
                "reasons": sorted(set(reasons))}
    if baseline["sha"] == candidate["sha"]:
        reasons.append("same_sha_not_a_comparison")
    for name in REQUIRED:
        old = baseline["checks"].get(name)
        new = candidate["checks"].get(name)
        if not _valid_check(old):
            reasons.append(name + "_baseline_missing_or_unacceptable")
        if not _valid_check(new):
            reasons.append(name + "_candidate_missing_or_unacceptable")
        if _valid_check(old) and _valid_check(new) and new["passed"] < old["passed"]:
            reasons.append(name + "_test_count_regressed")
    return {"comparison": "BLOCKED" if reasons else "COMPARABLE_UNTRUSTED",
            "release_authorized": False,
            "reasons": sorted(set(reasons))}


if __name__ == "__main__":
    # An invocation without verifiably authenticated evidence ALWAYS remains frozen.
    print("OMEGA_RELEASE_GATE=FROZEN_NO_AUTHENTICATED_OWNER_OR_PROVENANCE")
    print("OMEGA_RELEASE_AUTHORIZED=FALSE")
