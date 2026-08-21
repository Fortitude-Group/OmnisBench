# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import html as _html

# Fortitude Omnis web livery: dark --ds-* token palette, Inter + JetBrains Mono (named first with
# system fallbacks so the report stays self-contained and offline-safe, no external font fetch).
_APEX = "https://fortitude-omnis.group"

_CSS = """
  :root {
    color-scheme: dark;
    --ds-bg:8 12 20; --ds-surface:14 20 32; --ds-surface2:20 30 47;
    --ds-border:30 45 69; --ds-border2:37 54 80;
    --ds-accent:45 212 191; --ds-bright:94 234 212;
    --ds-text:241 245 249; --ds-muted:166 180 200; --ds-dim:124 141 166;
    --ds-warning:251 191 36; --ds-success:52 211 153;
    --sans:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
    --mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  }
  * { box-sizing:border-box; }
  body {
    margin:0; min-height:100vh; font:15px/1.55 var(--sans); color:rgb(var(--ds-text));
    background:
      radial-gradient(60rem 30rem at 78% -12%, rgb(var(--ds-accent) / .10), transparent 60%),
      radial-gradient(48rem 24rem at 0% -4%, rgb(var(--ds-bright) / .06), transparent 55%),
      rgb(var(--ds-bg));
    background-attachment:fixed;
  }
  body::before {
    content:''; position:fixed; inset:0; z-index:-1; pointer-events:none;
    background-image:radial-gradient(rgb(var(--ds-border2) / .35) 1px, transparent 1px);
    background-size:22px 22px;
    -webkit-mask-image:linear-gradient(to bottom, black, transparent 72%);
    mask-image:linear-gradient(to bottom, black, transparent 72%);
  }
  a { color:rgb(var(--ds-accent)); text-decoration:none; }
  a:hover { color:rgb(var(--ds-bright)); }
  header {
    display:flex; gap:14px; align-items:baseline; flex-wrap:wrap;
    padding:20px 28px; border-bottom:1px solid rgb(var(--ds-border));
    background:rgb(var(--ds-surface) / .55);
  }
  .wordmark { font-size:19px; font-weight:800; letter-spacing:-.02em; }
  .wordmark .g { background:linear-gradient(90deg, rgb(var(--ds-bright)), rgb(var(--ds-accent)));
    -webkit-background-clip:text; background-clip:text; color:transparent; }
  .eyebrow { font-family:var(--mono); font-size:10.5px; font-weight:600; text-transform:uppercase;
    letter-spacing:.16em; color:rgb(var(--ds-accent)); background:rgb(var(--ds-accent) / .10);
    border:1px solid rgb(var(--ds-accent) / .28); padding:3px 9px; border-radius:999px; }
  .byline { font-size:12.5px; color:rgb(var(--ds-dim)); margin-left:auto; }
  .byline a { font-weight:600; }
  main { max-width:1000px; margin:0 auto; padding:26px 28px 8px; }
  .prov { color:rgb(var(--ds-dim)); font-size:13px; margin:0 0 22px; }
  .prov code { font-family:var(--mono); color:rgb(var(--ds-muted)); }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:16px; margin-bottom:26px; }
  .card { background:rgb(var(--ds-surface)); border:1px solid rgb(var(--ds-border)); border-radius:16px; padding:18px; }
  .card .n { font-size:27px; font-weight:800; letter-spacing:-.02em; }
  .card.accent .n { color:rgb(var(--ds-accent)); }
  .card .l { margin-top:6px; font-family:var(--mono); color:rgb(var(--ds-dim)); font-size:10.5px;
    text-transform:uppercase; letter-spacing:.12em; }
  .chart { background:rgb(var(--ds-surface)); border:1px solid rgb(var(--ds-border)); border-radius:16px;
    padding:12px 8px; margin-bottom:26px; overflow-x:auto; }
  svg { display:block; margin:0 auto; max-width:100%; height:auto; }
  h2 { font-size:15px; text-transform:uppercase; letter-spacing:.1em; color:rgb(var(--ds-muted));
    font-family:var(--mono); font-weight:600; margin:26px 0 10px; }
  h3 { font-size:13.5px; color:rgb(var(--ds-muted)); margin:18px 0 8px; }
  .panel { background:rgb(var(--ds-surface)); border:1px solid rgb(var(--ds-border)); border-radius:16px; overflow:hidden; }
  .tablewrap { overflow-x:auto; }
  table { width:100%; border-collapse:collapse; }
  th, td { text-align:left; padding:11px 14px; border-bottom:1px solid rgb(var(--ds-border));
    font-variant-numeric:tabular-nums; font-size:13.5px; white-space:nowrap; }
  th { font-family:var(--mono); color:rgb(var(--ds-dim)); font-weight:600; font-size:10.5px;
    text-transform:uppercase; letter-spacing:.1em; background:rgb(var(--ds-surface2) / .5); }
  tbody tr:last-child td { border-bottom:none; }
  tbody tr:hover td { background:rgb(var(--ds-surface2) / .4); }
  td.pol { font-family:var(--mono); font-weight:600; }
  td.num { font-family:var(--mono); }
  tr.is-front td.pol { color:rgb(var(--ds-accent)); }
  .front-tag { color:rgb(var(--ds-accent)); margin-right:6px; }
  .badge { padding:2px 9px; border-radius:999px; font-size:11px; font-family:var(--mono);
    background:rgb(var(--ds-surface2)); border:1px solid rgb(var(--ds-border2)); color:rgb(var(--ds-muted)); }
  .axis { stroke:rgb(var(--ds-border2)); stroke-width:1; }
  .grid { stroke:rgb(var(--ds-border) / .7); stroke-width:1; }
  .frontline { fill:none; stroke:rgb(var(--ds-accent) / .55); stroke-width:2; stroke-dasharray:4 4; }
  .dot-front { fill:rgb(var(--ds-accent)); }
  .dot-back { fill:rgb(var(--ds-dim)); }
  .lbl { fill:rgb(var(--ds-text)); font-family:var(--mono); font-size:11px; }
  .cap { fill:rgb(var(--ds-dim)); font-family:var(--mono); font-size:10px; letter-spacing:.08em; text-transform:uppercase; }
  .tick { fill:rgb(var(--ds-dim)); font-family:var(--mono); font-size:10px; }
  footer { max-width:1000px; margin:26px auto 0; padding:20px 28px 32px; border-top:1px solid rgb(var(--ds-border));
    color:rgb(var(--ds-dim)); font-size:12.5px; display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; }
  footer a { font-weight:600; }
"""


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
        return "<svg width='680' height='360' role='img' aria-label='cost vs quality'></svg>"
    costs = [r["avg_cost_usd"] for r in rows]
    quals = [r["quality"] for r in rows]
    front = set(pareto_front(list(zip(costs, quals))))

    W, H = 680, 360
    left, right, top, bottom = 66, 26, 34, 52
    cmin, cmax = min(costs), max(costs)
    qmin, qmax = min(quals), max(quals)
    # 8% padding on each axis so points never sit on the frame; guard the single-value case.
    cspan = (cmax - cmin) or (cmax or 1.0)
    qspan = (qmax - qmin) or (qmax or 1.0)
    c0, c1 = cmin - cspan * 0.08, cmax + cspan * 0.08
    q0, q1 = qmin - qspan * 0.08, qmax + qspan * 0.08

    def sx(c: float) -> float:
        return left + (c - c0) / (c1 - c0) * (W - left - right)

    def sy(q: float) -> float:
        return H - bottom - (q - q0) / (q1 - q0) * (H - top - bottom)

    parts = [f"<svg viewBox='0 0 {W} {H}' width='{W}' height='{H}' role='img' "
             f"aria-label='task quality versus cost per task, blue marks the efficiency frontier'>"]
    # axes
    parts.append(f"<line class='axis' x1='{left}' y1='{top}' x2='{left}' y2='{H - bottom}'/>")
    parts.append(f"<line class='axis' x1='{left}' y1='{H - bottom}' x2='{W - right}' y2='{H - bottom}'/>")
    # gridlines at the data extremes
    for q in (qmin, qmax):
        y = sy(q)
        parts.append(f"<line class='grid' x1='{left}' y1='{y:.1f}' x2='{W - right}' y2='{y:.1f}'/>")
        parts.append(f"<text class='tick' x='{left - 8}' y='{y + 3:.1f}' text-anchor='end'>{q * 100:.1f}%</text>")
    for c in (cmin, cmax):
        x = sx(c)
        parts.append(f"<text class='tick' x='{x:.1f}' y='{H - bottom + 16:.1f}' text-anchor='middle'>${c:.4f}</text>")
    # frontier line (through frontier points, ordered by cost)
    fpts = sorted((i for i in front), key=lambda i: costs[i])
    if len(fpts) >= 2:
        poly = " ".join(f"{sx(costs[i]):.1f},{sy(quals[i]):.1f}" for i in fpts)
        parts.append(f"<polyline class='frontline' points='{poly}'/>")
    # points + labels
    for i, r in enumerate(rows):
        x, y = sx(costs[i]), sy(quals[i])
        cls = "dot-front" if i in front else "dot-back"
        parts.append(f"<circle class='{cls}' cx='{x:.1f}' cy='{y:.1f}' r='{6 if i in front else 5}'/>")
        # label left of the point if it sits in the right third, else to the right
        if x > left + (W - left - right) * 0.66:
            parts.append(f"<text class='lbl' x='{x - 10:.1f}' y='{y + 3:.1f}' text-anchor='end'>{_html.escape(r['policy'])}</text>")
        else:
            parts.append(f"<text class='lbl' x='{x + 10:.1f}' y='{y + 3:.1f}'>{_html.escape(r['policy'])}</text>")
    # axis captions
    parts.append(f"<text class='cap' x='{(left + W - right) / 2:.1f}' y='{H - 6}' text-anchor='middle'>cost / task (USD) &#8594;</text>")
    parts.append(f"<text class='cap' x='16' y='{(top + H - bottom) / 2:.1f}' text-anchor='middle' "
                 f"transform='rotate(-90 16 {(top + H - bottom) / 2:.1f})'>&#8593; task quality</text>")
    parts.append("</svg>")
    return "".join(parts)


def _leaderboard_table(rows: list[dict]) -> str:
    front = set(pareto_front(list(zip((r["avg_cost_usd"] for r in rows), (r["quality"] for r in rows)))))
    head = ("<tr><th>Policy</th><th>Kind</th><th>Quality</th><th>Avg $/task</th>"
            "<th>Quality/$</th><th>Frontier escape</th></tr>")
    body = []
    for i, r in enumerate(rows):
        tag = "<span class='front-tag'>&#9670;</span>" if i in front else ""
        cls = " class='is-front'" if i in front else ""
        body.append(
            f"<tr{cls}><td class='pol'>{tag}{_html.escape(r['policy'])}</td>"
            f"<td><span class='badge'>{_html.escape(str(r['kind']))}</span></td>"
            f"<td class='num'>{r['quality']:.3f}</td><td class='num'>${r['avg_cost_usd']:.4f}</td>"
            f"<td class='num'>{r['quality_per_usd']:.2f}</td>"
            f"<td class='num'>{r.get('escape_rate', 0.0) * 100:.1f}%</td></tr>"
        )
    return f"<div class='panel'><div class='tablewrap'><table>{head}{''.join(body)}</table></div></div>"


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
             ("<p class='prov'>The same policies, scored separately on tasks the models may have trained on "
              "versus tasks they could not have seen. If the routing story only holds on the "
              "contaminated split, the split tables show it.</p>")]
    for split, rows in splits.items():
        label = _SPLIT_LABEL.get(split, split)
        n = counts.get(split)
        n_str = f" &middot; {n} tasks" if n is not None else ""
        parts.append(f"<h3>{_html.escape(label)}{n_str}</h3>{_leaderboard_table(rows)}")
    return "".join(parts)


def _cards(rows: list[dict]) -> str:
    if not rows:
        return ""
    peak = max(rows, key=lambda r: r["quality"])
    best = max(rows, key=lambda r: r["quality_per_usd"])
    front = pareto_front(list(zip((r["avg_cost_usd"] for r in rows), (r["quality"] for r in rows))))

    def card(value: str, label: str, accent: bool = False) -> str:
        cls = "card accent" if accent else "card"
        return f"<div class='{cls}'><div class='n'>{value}</div><div class='l'>{label}</div></div>"

    return (
        "<div class='cards'>"
        + card(f"{peak['quality'] * 100:.1f}%", f"peak quality &middot; {_html.escape(peak['policy'])}", accent=True)
        + card(f"{best['quality_per_usd']:.2f}", f"best quality/$ &middot; {_html.escape(best['policy'])}")
        + card(f"{len(front)}", "policies on the frontier")
        + "</div>"
    )


def render_report(doc: dict) -> str:
    prov = doc.get("provenance", {})
    frontier = doc.get("frontier_model")
    frontier_line = (
        f" &middot; Frontier model: <code>{_html.escape(str(frontier))}</code>" if frontier else ""
    )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>OmnisBench Results</title>"
        f"<style>{_CSS}</style></head><body>"
        "<header>"
        "<span class='wordmark'>Omnis<span class='g'>Bench</span></span>"
        "<span class='eyebrow'>Routing Efficiency Benchmark</span>"
        f"<span class='byline'>by <a href='{_APEX}' target='_blank' rel='noopener'>Fortitude Omnis</a></span>"
        "</header>"
        "<main>"
        f"<p class='prov'>Pricing snapshot: <code>{_html.escape(str(prov.get('snapshot_date', '?')))}</code> "
        f"&middot; Run: <code>{_html.escape(str(prov.get('run_date', '?')))}</code>{frontier_line}</p>"
        f"{_cards(doc['leaderboard'])}"
        f"<div class='chart'>{_svg(doc)}</div>"
        "<h2>Overall</h2>"
        f"{_leaderboard_table(doc['leaderboard'])}"
        f"{_splits(doc)}"
        "</main>"
        "<footer>"
        f"<span>A <a href='{_APEX}' target='_blank' rel='noopener'>Fortitude Omnis</a> product.</span>"
        "<span style='font-family:var(--mono)'>OmnisBench &middot; routing efficiency</span>"
        "</footer>"
        "</body></html>"
    )
