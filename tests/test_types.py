# SPDX-License-Identifier: Apache-2.0
from omnisbench.types import CompletionRequest, ModelRef


def test_modelref_key():
    assert ModelRef("openai", "gpt-x").key == "openai/gpt-x"


def test_cache_payload_is_stable_and_model_scoped():
    req = CompletionRequest(messages=[{"role": "user", "content": "hi"}], max_tokens=16)
    a = req.cache_payload(ModelRef("openai", "gpt-x"))
    b = req.cache_payload(ModelRef("openai", "gpt-x"))
    c = req.cache_payload(ModelRef("openai", "gpt-y"))
    assert a == b
    assert a != c
    assert a["provider"] == "openai" and a["model_id"] == "gpt-x"
