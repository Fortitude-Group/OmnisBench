# SPDX-License-Identifier: Apache-2.0
from omnisbench.report.html import pareto_front, render_report


def test_pareto_front_identifies_dominant_points():
    # (cost, quality): B dominates A (cheaper AND better); C is also non-dominated (cheapest)
    pts = [(0.05, 0.6), (0.03, 0.8), (0.01, 0.5)]
    front = set(pareto_front(pts))
    assert 1 in front  # (0.03, 0.8)
    assert 2 in front  # (0.01, 0.5)
    assert 0 not in front  # (0.05, 0.6) dominated by index 1


def test_render_report_contains_leaderboard_and_svg():
    doc = {
        "provenance": {"snapshot_date": "2026-08-18", "run_date": "2026-08-18"},
        "leaderboard": [
            {"policy": "oracle", "kind": "transparent", "n": 10, "quality": 0.9,
             "total_cost_usd": 0.2, "avg_cost_usd": 0.02, "quality_per_usd": 4.5},
        ],
        "items": [],
    }
    html = render_report(doc)
    assert "<svg" in html
    assert "oracle" in html
    assert "2026-08-18" in html
