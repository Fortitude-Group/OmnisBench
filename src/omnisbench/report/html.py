# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import html as _html


def pareto_front(points: list[tuple[float, float]]) -> list[int]:
    """Return indices non-dominated on (min cost, max quality)."""
    front: list[int] = []
    for i, (ci, qi) in enumerate(points):
        dominated = any(
            (cj <= ci and qj >= qi) and (cj < ci or qj > qi)
            for j, (cj, qj) in enumerate(points) if j != i
        )
        if not dominated:
            front.append(i)
    return front


def _svg(doc: dict) -> str:
    rows = doc["leaderboard"]
    if not rows:
        return "<svg width='600' height='300'></svg>"
    costs = [r["avg_cost_usd"] for r in rows]
    quals = [r["quality"] for r in rows]
    front = set(pareto_front(list(zip(costs, quals))))
    cmax = max(costs) or 1.0
    W, H, pad = 600, 300, 40
    dots = []
    for i, r in enumerate(rows):
        x = pad + (r["avg_cost_usd"] / cmax) * (W - 2 * pad)
        y = H - pad - r["quality"] * (H - 2 * pad)
        fill = "#2563eb" if i in front else "#9ca3af"
        dots.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='6' fill='{fill}'></circle>")
        dots.append(f"<text x='{x + 8:.1f}' y='{y:.1f}' font-size='11'>{_html.escape(r['policy'])}</text>")
    return (
        f"<svg width='{W}' height='{H}' role='img' aria-label='cost vs quality'>"
        f"<text x='{pad}' y='20' font-size='12'>quality ↑ / cost/task →  (blue = frontier)</text>"
        + "".join(dots) + "</svg>"
    )


def _leaderboard_table(rows: list[dict]) -> str:
    head = ("<tr><th>Policy</th><th>Kind</th><th>Quality</th><th>Avg $/task</th>"
            "<th>Quality/$</th><th>Frontier escape</th></tr>")
    body = "".join(
        f"<tr><td>{_html.escape(r['policy'])}</td><td>{r['kind']}</td>"
        f"<td>{r['quality']:.3f}</td><td>${r['avg_cost_usd']:.4f}</td>"
        f"<td>{r['quality_per_usd']:.2f}</td>"
        f"<td>{r.get('escape_rate', 0.0) * 100:.1f}%</td></tr>"
        for r in rows
    )
    return f"<table>{head}{body}</table>"


_SPLIT_LABEL = {
    "fresh": "Fresh (contamination-resistant)",
    "likely_contaminated": "Likely contaminated (HumanEval, GSM8K)",
    "unknown": "Unclassified",
}


def _splits(doc: dict) -> str:
    splits = doc.get("splits") or {}
    if len(splits) <= 1:
        return ""  # nothing to compare against; the overall board already says it all
    counts = doc.get("contamination_counts") or {}
    parts = ["<h2>By contamination split</h2>",
             ("<p>The same policies, scored separately on tasks the models may have trained on "
              "versus tasks they could not have seen. If the routing story only holds on the "
              "contaminated split, the split tables show it.</p>")]
    for split, rows in splits.items():
        label = _SPLIT_LABEL.get(split, split)
        n = counts.get(split)
        n_str = f" &middot; {n} tasks" if n is not None else ""
        parts.append(f"<h3>{_html.escape(label)}{n_str}</h3>{_leaderboard_table(rows)}")
    return "".join(parts)


def render_report(doc: dict) -> str:
    prov = doc.get("provenance", {})
    frontier = doc.get("frontier_model")
    css = (
        "body{font-family:system-ui,sans-serif;margin:2rem;background:#fff;color:#111}"
        "table{border-collapse:collapse;margin-top:1rem}td,th{border:1px solid #ddd;padding:.4rem .8rem}"
        "@media(prefers-color-scheme:dark){body{background:#0b0b0b;color:#eee}td,th{border-color:#333}}"
    )
    frontier_line = (
        f" &middot; Frontier model: <code>{_html.escape(str(frontier))}</code>" if frontier else ""
    )
    return (
        "<!doctype html><meta charset='utf-8'><title>OmnisBench Results</title>"
        f"<style>{css}</style>"
        "<h1>OmnisBench — Routing Efficiency</h1>"
        f"<p>Pricing snapshot: {_html.escape(str(prov.get('snapshot_date','?')))} &middot; "
        f"Run: {_html.escape(str(prov.get('run_date','?')))}{frontier_line}</p>"
        f"{_svg(doc)}"
        "<h2>Overall</h2>"
        f"{_leaderboard_table(doc['leaderboard'])}"
        f"{_splits(doc)}"
    )
