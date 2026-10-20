"""S10 UI and synthetic provenance contracts: no live account access."""
import shutil
import subprocess
from pathlib import Path

import pytest

from omega_mvi.inspection.retrieval import SyntheticRetriever, SecretInputError


def test_dashboard_source_contract_node():
    node = shutil.which("node")
    assert node is not None, "Node.js required to execute source guard contract"
    script = Path(__file__).with_name("ui_dashboard_source_guard.cjs")
    result = subprocess.run(
        [node, "--test", str(script)],
        capture_output=True, text=True, timeout=20, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_synthetic_retrieval_acl_rejects_wrong_and_missing_requester():
    search = SyntheticRetriever("synthetic-owner")
    with pytest.raises(PermissionError):
        search.retrieve("citations", requester_id="different-owner")
    with pytest.raises(PermissionError):
        search.retrieve("citations", requester_id="")


def test_synthetic_provenance_is_not_a_live_user_document():
    search = SyntheticRetriever("synthetic-owner")
    results = search.retrieve("citations source reference", requester_id="synthetic-owner")
    assert results
    assert all(item.source_ref.startswith("synthetic://omega-fixtures/")
               for item in results)
    with pytest.raises(SecretInputError):
        search.retrieve("Bearer ABCDEFGHIJKLMNOPQ", requester_id="synthetic-owner")

# Deleted-source invalidation requires a real corpus lifecycle, ACL and delete API.
# Those do not exist in this synthetic fixture, so this is NOT an acceptance test.
