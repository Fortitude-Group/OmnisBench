# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path

from .types import CompletionResponse, ModelRef, Usage


def cache_key(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class ResponseCache:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> CompletionResponse | None:
        path = self._path(key)
        if not path.exists():
            return None
        d = json.loads(path.read_text(encoding="utf-8"))
        return CompletionResponse(
            text=d["text"],
            model=ModelRef(d["provider"], d["model_id"]),
            usage=Usage(d["input_tokens"], d["output_tokens"]),
            latency_ms=d["latency_ms"],
            from_cache=True,
            raw=d.get("raw", {}),
        )

    def put(self, key: str, resp: CompletionResponse) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        blob = json.dumps(
            {
                "text": resp.text,
                "provider": resp.model.provider,
                "model_id": resp.model.model_id,
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
                "latency_ms": resp.latency_ms,
                "raw": resp.raw,
            },
            indent=2,
        )
        # Write to a temp file in the same directory then atomically replace the
        # final path, so an interrupted write can't leave a partial/corrupt JSON
        # file that would poison a later get().
        tmp_path = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
        tmp_path.write_text(blob, encoding="utf-8")
        os.replace(tmp_path, path)


class BudgetExceeded(RuntimeError):
    """Raised once a run's new (paid) responses have cost more than its spend cap."""


class BudgetedCache(ResponseCache):
    """A ResponseCache that keeps a running total of what new responses cost and stops the run
    once it passes ``max_usd``.

    Every paid call lands here through ``put``, so the total counts only real spend, never cache
    hits. The response that crosses the line is still stored (it's been paid for), then the run
    stops. The total lives in ``spend.json`` next to the cache, so re-running the same command
    resumes from the cache with the spend so far still counted.
    """

    def __init__(self, root: Path, cost, max_usd: float):
        super().__init__(root)
        self.cost = cost
        self.max_usd = float(max_usd)
        self._ledger = self.root.parent / "spend.json"
        self.spent_usd = 0.0
        if self._ledger.exists():
            self.spent_usd = float(json.loads(self._ledger.read_text(encoding="utf-8"))["spent_usd"])
        if self.spent_usd >= self.max_usd:
            raise BudgetExceeded(
                f"Spend so far ${self.spent_usd:.2f} is already at the ${self.max_usd:.2f} cap.")

    def put(self, key: str, resp: CompletionResponse) -> None:
        super().put(key, resp)
        # Price is a KeyError for an unpriced model, on purpose: spend we can't count isn't capped.
        self.spent_usd += self.cost.price(resp.model, resp.usage)
        self._ledger.parent.mkdir(parents=True, exist_ok=True)
        self._ledger.write_text(
            json.dumps({"spent_usd": round(self.spent_usd, 6), "max_usd": self.max_usd}), encoding="utf-8")
        if self.spent_usd > self.max_usd:
            raise BudgetExceeded(
                f"Spent ${self.spent_usd:.2f}, over the ${self.max_usd:.2f} cap. Stopped. "
                "Raise max_spend_usd and re-run the same command to carry on from the cache.")
