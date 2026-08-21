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

## Headline results (run 2026-08-20)

The number that matters is the **fresh split**: LiveCodeBench problems published after the models'
training cutoff, so none of them can be sitting in the training data. That is where routing has to
earn its keep.

Fresh split, 15 tasks. Pool: `claude-opus-5`, `gpt-5`, `claude-haiku-4-5`, `gpt-5-nano`. Pricing
snapshot `config/pricing/2026-08-18.yaml`, output budget 16,384 tokens. Full artifacts in
`runs/fresh-16k-2026-08-20/`.

| Policy | What it does | Task success | Cost / 1,000 |
|---|---|---:|---:|
| **oracle** | ideal per-request routing (cheapest model that actually solved each item) | **93.3%** | **$53.30** |
| always_big | always `claude-opus-5` (frontier) | 86.7% | $138.10 |
| random | uniform random over the pool | 73.3% | $59.00 |
| always_cheap | always `gpt-5-nano` (floor) | 60.0% | $4.10 |

On problems the models cannot have memorised, ideal routing hits **93.3%**, above the frontier
model's 86.7%, at roughly **60% lower cost** than always calling it. No single model solves every
fresh problem, so routing to the best model per item beats any fixed choice on quality and price at
once. That is the prize, and it only shows up once the data is clean.

For contrast, the same policies on the **likely-contaminated** split (HumanEval + GSM8K, 20 tasks)
all land near **100%** quality: the models have seen those problems, every policy looks equally
good, and routing appears to save nothing. That flatness is an artefact of contamination. An earlier
contaminated-only run reported exactly that as a headline (oracle at 99.7%), which was misleading,
so the fresh split now leads.

Read these numbers honestly:

- **The sample is small.** 15 fresh tasks is a pilot that shows the method and the direction, not a
  final verdict. Widening the fresh set is the roadmap.
- `oracle` is the **theoretical ceiling** of routing, chosen after the fact per item, not a
  shippable router. The gap between a real router and `oracle` is the real scorecard.
- Every figure re-derives offline: `omnisbench verify runs/fresh-16k-2026-08-20` re-runs the graders
  against the published responses and rebuilds this table with **zero API calls**.

The larger contaminated-only baseline (HumanEval 164 + GSM8K 200) still lives in `runs/2026-08-19/`
for reference; its numbers are pinned near 100% for the reason above.

Reproduce (needs `OPENAI_API_KEY` + `ANTHROPIC_API_KEY`, `pip install datasets` for LiveCodeBench,
and a container per the warning above):

```bash
pip install -e .
python scripts/prepare_datasets.py
python -m omnisbench.cli run    --config configs/fresh-run.yaml --run runs/mine
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
  could not have memorised the answer. The headline run (`runs/fresh-16k-2026-08-20`) carries both,
  15 fresh and 20 likely-contaminated; the original `configs/v0.yaml` suite is entirely
  `likely_contaminated`, and its board says so.
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
The headline run in `runs/fresh-16k-2026-08-20/` is one such run, built from `configs/fresh-run.yaml`.
Next on the roadmap: LiveCodeBench functional problems (implement-a-named-function), which are
skipped for now, and reading its compressed private test cases.

## `omnisbench verify`

`omnisbench verify` re-runs the graders against the published per-item
responses and re-derives the full leaderboard (quality + cost) with zero API
calls — anyone can reproduce and audit the numbers from `results.json` alone.
