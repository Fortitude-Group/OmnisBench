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
