import pytest

from omega_mvi.inspection.retrieval import (
    SecretInputError,
    SyntheticRetriever,
)


def test_retrieval_requires_owner_before_returning_documents():
    retriever = SyntheticRetriever(owner_id="synthetic-owner")

    with pytest.raises(PermissionError, match="OWNER_ACCESS_REQUIRED"):
        retriever.retrieve("citations", requester_id="another-user")


def test_retrieval_preserves_fixture_source_reference():
    retriever = SyntheticRetriever(owner_id="synthetic-owner")

    results = retriever.retrieve("exact source reference", requester_id="synthetic-owner")

    assert results
    assert results[0].source_ref == (
        "synthetic://omega-fixtures/provenance.md#citations"
    )
    assert results[0].source_ref.startswith("synthetic://")


def test_unmatched_query_does_not_fabricate_citations():
    retriever = SyntheticRetriever(owner_id="synthetic-owner")

    assert retriever.retrieve(
        "quartz nebula", requester_id="synthetic-owner"
    ) == ()


@pytest.mark.parametrize(
    "query",
    [
        "api_key=super-secret-value",
        "token=example-placeholder",
        "authorization: bearer",
        "-----BEGIN " + "RSA PRIVATE KEY-----",
        "g" + "hp_abcdefghijklmnopqrstuv",
    ],
)
def test_secret_bearing_query_is_rejected_without_echoing_input(query):
    retriever = SyntheticRetriever(owner_id="synthetic-owner")

    with pytest.raises(SecretInputError) as error:
        retriever.retrieve(query, requester_id="synthetic-owner")

    assert str(error.value) == "SECRET_INPUT_REJECTED"
