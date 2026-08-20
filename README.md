# OmnisBench

Open, reproducible benchmark for **LLM routing efficiency** — how close a routing
policy gets to the ideal quality-per-dollar frontier. Apache-2.0.

Prior art: RouterBench (Martian, arXiv:2403.12031). OmnisBench differs by being
live, cost-current, and continuously re-gradable (`omnisbench verify`).

## ⚠️ Security warning: untrusted code execution

`omnisbench run` executes **untrusted, model-generated Python** in order to grade
code tasks (the `code_unittest` grader). The v0 sandbox (`src/omnisbench/graders/sandbox.py`)
provides a fresh subprocess, a hard timeout, and a throwaway working directory —
but it does **NOT** provide network isolation, filesystem isolation, or memory/
resource limits. A malicious or buggy model response can still make outbound
network calls, read/write anything the host process can reach, or exhaust host
resources within the timeout window.

**Run `omnisbench run` inside a container or a disposable VM.** Full sandbox
hardening (network egress blocking, filesystem jail, resource limits) is a
tracked v1 item — it is not implemented yet, and no test in this repo asserts
isolation the code does not actually provide.

`omnisbench verify` does not execute untrusted code from a live model — it only
re-runs graders (including `code_unittest`, so the same untrusted-code caveat
above applies to the *response text already stored in* `results.json`) against
already-published, static data. The same sandboxing caveat applies: verify a
`results.json` you don't trust inside a container/VM too.

## Headline results (v0 — run 2026-08-19)

Suite: **HumanEval (164)** + **GSM8K (200)** = 364 objectively auto-graded items.
Candidate pool: `claude-opus-5`, `gpt-5`, `claude-haiku-4-5`, `gpt-5-nano`.
Pricing snapshot: `config/pricing/2026-08-18.yaml`. Full artifacts in `runs/2026-08-19/`.

| Policy | What it does | Task success | Cost / 1,000 requests |
|---|---|---:|---:|
| **oracle** | ideal per-request routing (cheapest model that *actually* solved each item) | **99.7%** | **$0.62** |
| always_big | always `claude-opus-5` (frontier) | 99.2% | $6.25 |
| random | uniform random over the pool | 96.2% | $4.01 |
| always_cheap | always `gpt-5-nano` (floor) | 94.5% | $0.43 |

**Ideal routing reaches 99.7% task success at ~90% lower cost than always using the frontier
model** — and every figure is reproducible offline: `omnisbench verify runs/2026-08-19` re-runs
the graders against the published responses and re-derives this table with **zero API calls**.

Read these numbers honestly:

- `oracle` is the **theoretical ceiling** of routing on this suite (chosen post-hoc, per item) —
  not a shippable router. It is the frontier a real router aims at; the gap between a real router
  and `oracle` is the real scorecard.
- On this suite the cheapest model alone (`gpt-5-nano`) already scores **94.5%**, so routing's
  realizable prize is recovering the last ~5 points of quality while staying ~10× cheaper than the
  frontier — not a magic 40–70% headline.
- Reasoning models were given a 4,096-token output budget; results reflect that budget.

Reproduce (needs `OPENAI_API_KEY` + `ANTHROPIC_API_KEY`):

```bash
pip install -e .
python scripts/prepare_datasets.py
python -m omnisbench.cli run    --config configs/v0.yaml --run runs/mine
python -m omnisbench.cli report --run runs/mine
python -m omnisbench.cli verify --run runs/mine   # zero-API re-grade of the published results
```

## Contamination and splits

HumanEval and GSM8K are old and widely republished, so the pool models have very likely seen the
graded examples. That can lift the absolute quality numbers and distort the per-model gap that
routing exploits, which was a fair point raised by readers. OmnisBench now reports it directly
instead of hiding it.

Each dataset carries a `contamination` tag in config (`likely_contaminated`, `fresh`, or the
default `unknown`). A run then produces, on top of the overall leaderboard:

- **A leaderboard per split.** The same policies are scored separately on the likely-contaminated
  tasks and on any fresh tasks, so you can see whether the routing story holds where the models
  could not have memorised the answer. The v0 suite is entirely `likely_contaminated`, and it says
  so.
- **Frontier escape rate per policy.** The fraction of a policy's requests that went to the
  frontier (most expensive) model. It is 0% for the cheap floor, 100% for always-frontier, and for
  a real router it is the escalation rate. This is the number that tends to drift once prompts get
  messier than a benchmark.

Both are re-derived from the stored items by `omnisbench verify`, so a faked split number or escape
rate fails verification the same way a tampered answer does.

### Adding a fresh, contamination-resistant split

A fresh split filters a dated dataset down to problems published after the models' training cutoff.
The `livecodebench` loader (`kind: livecodebench`) pulls LiveCodeBench, keeps the stdin/stdout
problems, stamps each task's release date, and `min_date` filters to the fresh ones. The
`livecodebench` grader runs each solution against the problem's test cases in the same sandbox as
the HumanEval grader, and `omnisbench verify` re-grades them offline. See
[`configs/livecodebench-fresh.example.yaml`](configs/livecodebench-fresh.example.yaml) for a
runnable config; it needs `pip install datasets`, provider keys, and a paid run to produce numbers.
Next on the roadmap: LiveCodeBench functional problems (implement-a-named-function), which are
skipped for now, and reading its compressed private test cases.

## `omnisbench verify`

`omnisbench verify` re-runs the graders against the published per-item
responses and re-derives the full leaderboard (quality + cost) with zero API
calls — anyone can reproduce and audit the numbers from `results.json` alone.
