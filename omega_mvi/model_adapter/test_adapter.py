from .protocol import ModelAdapter, ModelRequest, ModelResponse
from .testing import DeterministicFakeModelAdapter


def test_fake_adapter_implements_provider_neutral_contract():
    adapter: ModelAdapter = DeterministicFakeModelAdapter(
        {"hello": "synthetic hello"}
    )

    assert adapter.generate(ModelRequest(prompt="hello")) == ModelResponse(
        text="synthetic hello",
        model="synthetic-fake",
    )


def test_fake_adapter_returns_deterministic_default_for_unmapped_prompts():
    adapter = DeterministicFakeModelAdapter(default_response="offline fixture")
    request = ModelRequest(prompt="not mapped", system_prompt="synthetic system")

    assert adapter.generate(request) == adapter.generate(request)
    assert adapter.generate(request).text == "offline fixture"


def test_fake_adapter_copies_configured_responses():
    responses = {"hello": "before"}
    adapter = DeterministicFakeModelAdapter(responses)
    responses["hello"] = "after"

    assert adapter.generate(ModelRequest(prompt="hello")).text == "before"
