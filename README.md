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

_Headline results: added in Task 16._

## `omnisbench verify`

`omnisbench verify` re-runs the graders against the published per-item
responses and re-derives the full leaderboard (quality + cost) with zero API
calls — anyone can reproduce and audit the numbers from `results.json` alone.
