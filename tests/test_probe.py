# SPDX-License-Identifier: Apache-2.0
import json
import textwrap

from omnisbench import cli
from omnisbench.cache import ResponseCache
from omnisbench.probe import generate_perturbations, perturbation_gaps, tag_originals
from omnisbench.providers.base import ProviderRegistry
from omnisbench.providers.mock import MockProvider
from omnisbench.runner import ItemResult
from omnisbench.types import ModelRef, TaskItem, Usage


def _ir(model, variant, base, passed):
    item_id = base if variant == "original" else f"{base}#pert"
    meta = {"variant": variant}
    if variant == "perturbed":
        meta["orig_id"] = base
    return ItemResult(policy="always", dataset="lcb", item_id=item_id, grader="livecodebench",
                      reference=[], meta=meta, response_text="", chosen_model=model, passed=passed,
                      cost_usd=0.0, input_tokens=0, output_tokens=0, latency_ms=0.0)


def test_perturbation_gap_per_model():
    results = [
        _ir("A", "original", "t1", True), _ir("A", "original", "t2", True),
        _ir("A", "perturbed", "t1", False), _ir("A", "perturbed", "t2", False),
        _ir("B", "original", "t1", True), _ir("B", "original", "t2", False),
        _ir("B", "perturbed", "t1", True), _ir("B", "perturbed", "t2", False),
    ]
    g = perturbation_gaps(results)
    assert g["A"]["acc_original"] == 1.0
    assert g["A"]["acc_perturbed"] == 0.0
    assert g["A"]["gap"] == 1.0
    assert g["A"]["n"] == 2
    assert g["B"]["gap"] == 0.0  # same pass pattern on both variants, no memorisation signal


def test_perturbation_gap_skips_model_missing_a_variant():
    assert perturbation_gaps([_ir("A", "original", "t1", True)]) == {}


def test_generate_perturbations_keeps_reference_and_tags(tmp_path):
    reg = ProviderRegistry()
    reg.register(MockProvider("anthropic", lambda req, m: ("REWORDED STATEMENT", Usage(10, 5))))
    items = [TaskItem("t1", "lcb", "original prompt", [{"input": "1", "output": "2"}],
                      "livecodebench", {"date": "2025-02-01"})]
    tag_originals(items)
    assert items[0].meta["variant"] == "original"

    pert = generate_perturbations(items, ModelRef("anthropic", "claude-opus-5"),
                                  reg, ResponseCache(tmp_path), 512)
    p = pert[0]
    assert p.id == "t1#pert"
    assert p.prompt == "REWORDED STATEMENT"
    assert p.reference == [{"input": "1", "output": "2"}]  # tests carried across unchanged
    assert p.meta["variant"] == "perturbed"
    assert p.meta["orig_id"] == "t1"
    assert p.meta["date"] == "2025-02-01"  # original meta inherited


def test_generate_perturbations_falls_back_to_original_on_empty(tmp_path):
    reg = ProviderRegistry()
    reg.register(MockProvider("anthropic", lambda req, m: ("   ", Usage(1, 1))))  # blank rewrite
    items = [TaskItem("t1", "lcb", "keep me", "ref", "livecodebench", {})]
    pert = generate_perturbations(items, ModelRef("anthropic", "x"), reg, ResponseCache(tmp_path))
    assert pert[0].prompt == "keep me"


def _probe_providers():
    def responder(req, m):
        if req.messages[0]["role"] == "system":  # a reword request
            return ("REWORDED " + req.messages[1]["content"], Usage(5, 5))
        perturbed = req.messages[0]["content"].startswith("REWORDED")
        if perturbed and m.model_id == "gpt-mid":  # this model only solves the memorised wording
            return ("wrong", Usage(5, 5))
        return ("paris", Usage(5, 5))
    reg = ProviderRegistry()
    reg.register(MockProvider("anthropic", responder))
    reg.register(MockProvider("openai", responder))
    return reg


def test_cmd_probe_end_to_end_and_verify(tmp_path):
    data = tmp_path / "fresh.jsonl"
    data.write_text(
        '{"id":"m1","prompt":"capital of France?","reference":"paris","grader":"exact_match","meta":{"date":"2025-02-01"}}\n'
        '{"id":"m2","prompt":"capital of France, again?","reference":"paris","grader":"exact_match","meta":{"date":"2025-03-01"}}\n',
        encoding="utf-8")
    cfg = tmp_path / "probe.yaml"
    cfg.write_text(textwrap.dedent(f"""
        run_date: "2026-08-23"
        pricing: "tests/fixtures/pricing/2026-08-18.yaml"
        datasets:
          - {{ kind: jsonl, name: mini, path: "{data.as_posix()}", seed: 0, contamination: fresh }}
        models:
          big: {{ provider: anthropic, model_id: "claude-big" }}
          mid: {{ provider: openai, model_id: "gpt-mid" }}
        probe:
          generator: {{ provider: anthropic, model_id: "claude-big" }}
    """), encoding="utf-8")
    run_dir = tmp_path / "run"
    assert cli.cmd_probe(str(cfg), str(run_dir), providers_override=_probe_providers()) == 0

    doc = json.loads((run_dir / "results.json").read_text())
    pert = doc["perturbation"]
    assert pert["openai/gpt-mid"]["gap"] == 1.0        # right on the original, wrong when reworded
    assert pert["anthropic/claude-big"]["gap"] == 0.0  # solves both, no memorisation signal
    assert cli.cmd_verify(str(run_dir)) == 0           # gaps re-derive from stored responses
