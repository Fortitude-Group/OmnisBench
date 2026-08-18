# SPDX-License-Identifier: Apache-2.0
from omnisbench.cache import ResponseCache
from omnisbench.policies.openrouter_auto import OpenRouterAutoPolicy
from omnisbench.providers.base import ProviderRegistry
from omnisbench.types import CompletionResponse, ModelRef, TaskItem, Usage


class RawMock:
    name = "openrouter"

    def complete(self, req, model):
        return CompletionResponse("ok", model, Usage(9, 3), 1.0, False, {"model": "deepseek/deepseek-chat"})


def test_opaque_policy_records_reported_model(tmp_path):
    reg = ProviderRegistry()
    reg.register(RawMock())
    p = OpenRouterAutoPolicy("openrouter_auto")
    out = p.run(TaskItem("t", "ds", "q", "x", "exact_match", {}), reg, ResponseCache(tmp_path))
    assert p.kind == "opaque"
    assert out.chosen_model == ModelRef("openrouter", "deepseek/deepseek-chat")
    assert out.usage == Usage(9, 3)
