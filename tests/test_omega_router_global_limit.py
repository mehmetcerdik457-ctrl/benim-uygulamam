"""Cross-model concurrency regression: registered count is not running count."""
import asyncio

from omega_mvi.model_adapter.router import Completion, ModelProfile, ModelRouter, Privacy, RouteRequest


def test_one_global_slot_even_when_models_differ():
    shared = {"active": 0, "peak": 0}

    class Backend:
        def __init__(self, name):
            self.name = name

        def count_prompt_tokens(self, prompt, system_prompt):
            return 3

        async def generate(self, request, *, max_output_tokens):
            shared["active"] += 1
            shared["peak"] = max(shared["peak"], shared["active"])
            try:
                await asyncio.sleep(0.03)
                return Completion(self.name, "fixture", 3, 1)
            finally:
                shared["active"] -= 1

    def profile(name):
        return ModelProfile(name=name, tasks=frozenset({"chat"}),
                            max_privacy=Privacy.RESTRICTED, context_tokens=100,
                            output_tokens=10, max_retries=0)

    async def task():
        router = ModelRouter([(profile("a"), Backend("a")),
                              (profile("b"), Backend("b"))], global_concurrency=1)
        await asyncio.gather(*[
            router.generate(RouteRequest(task="chat", prompt="hello", max_output_tokens=2,
                                         allowed_models=frozenset({name})))
            for name in ("a", "b")])

    asyncio.run(task())
    assert shared == {"active": 0, "peak": 1}
