# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
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
        path.write_text(
            json.dumps(
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
            ),
            encoding="utf-8",
        )
