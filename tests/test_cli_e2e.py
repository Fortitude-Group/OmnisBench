# SPDX-License-Identifier: Apache-2.0
import json

from omnisbench import cli
from omnisbench.providers.base import ProviderRegistry
from omnisbench.providers.mock import MockProvider
from omnisbench.types import Usage


def _providers():
    def responder(req, m):
        # big model always right; cheap model wrong on the math item
        content = req.messages[0]["content"]
        if "France" in content:
            return ("Paris", Usage(100, 5))
        return ("42" if m.model_id == "claude-big" else "0", Usage(100, 5))
    reg = ProviderRegistry()
    reg.register(MockProvider("anthropic", responder))
    reg.register(MockProvider("openrouter", responder))
    return reg


def test_run_report_verify_end_to_end(tmp_path):
    run_dir = tmp_path / "run"
    cli.cmd_run("tests/configs/e2e.yaml", str(run_dir), providers_override=_providers())
    doc = json.loads((run_dir / "results.json").read_text())
    assert doc["leaderboard"], "leaderboard should not be empty"
    # oracle quality must be >= any single always_* policy quality
    q = {r["policy"]: r["quality"] for r in doc["leaderboard"]}
    assert q["oracle"] >= q["always_cheap"]

    cli.cmd_report(str(run_dir))
    assert (run_dir / "report.html").exists()

    # verify must pass against the freshly written, cache-backed run (no providers used)
    assert cli.cmd_verify(str(run_dir)) == 0


def test_verify_catches_tampered_response(tmp_path):
    # A run whose results.json is genuinely honest passes verify.
    run_dir = tmp_path / "run"
    cli.cmd_run("tests/configs/e2e.yaml", str(run_dir), providers_override=_providers())
    results_path = run_dir / "results.json"
    doc = json.loads(results_path.read_text())

    # Corrupt one item's response_text to a WRONG answer, while leaving its
    # stored passed=True and the leaderboard numbers completely untouched.
    # A verify that only re-derives arithmetic from the stored `passed` flags
    # could never catch this — only a genuine re-grade of response_text can.
    target = None
    for it in doc["items"]:
        if it["dataset"] == "mini" and it["item_id"] == "m1":  # capital-of-France item
            target = it
            break
    assert target is not None, "expected an m1 item in results.json"
    assert target["passed"] is True

    target["response_text"] = "definitely not paris"
    # passed flag and leaderboard are deliberately left stale/untouched.
    results_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    assert cli.cmd_verify(str(run_dir)) != 0
