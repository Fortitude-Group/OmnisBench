# Perturbation-gap contamination probe

Status: built. Run `omnisbench probe --config configs/probe-run.yaml`. First run in
`runs/probe-2026-08-23`, re-gradable with `omnisbench verify runs/probe-2026-08-23`.

## Why it exists

The split labels ("fresh", "likely_contaminated") are a judgement based on release dates. A reader
can't see how much a given model memorised. The perturbation gap turns that judgement into a
measured, per-model number you can check.

## What it measures

Score each model twice on the same set of tasks:

- on the original problem,
- on a reworded copy that keeps the answer and the test cases identical.

`gap = accuracy(original) - accuracy(perturbed)`, per model, per split.

A model that leaned on the memorised wording drops when you change it, so a large positive gap points
to contamination of that model on that set. A gap near zero means the score reflects capability, not
recall. The gap is a continuous value per model per split, not a pass or fail.

## The invariant that makes it valid

The perturbation must not change the correct output. For LiveCodeBench stdin problems the test cases
are (input, expected output) pairs. We keep those byte-identical and change only the problem statement
wording and the identifier names in the starter code. Grading stays exactly the same, so any accuracy
drop comes from the wording, not from a changed task.

## The perturbations (code tasks)

Applied to the statement and starter code, never the tests:

1. Rename identifiers in the statement and starter code (variables, function names, sample-variable
   names), consistently across the problem.
2. Paraphrase the prose of the statement, holding the constraints, limits and I/O format word-for-word
   where they carry meaning.
3. Reorder independent constraint lines and worked examples.
4. Swap the surface story (rename the "company", "robot" or "string" framing) while keeping the maths.

Each perturbed task records its strategy and a seed, so it reproduces, and the perturbed prompt gets
published in `results.json`.

## Generation and verification

Producing a paraphrase uses a model, which isn't deterministic across providers. So generation is a
one-time offline step whose output, the perturbed prompts, gets committed. `omnisbench verify` never
regenerates perturbations. It re-grades the stored model responses against the unchanged test cases,
the same way it handles the main run. The gap is a pure function of the stored pass/fail flags, so it
re-derives offline like every other number here.

## Guarding the probe against itself

A gap can also come from a bad rewording that makes the task harder or ambiguous. Two guards:

- Validation pass. A strong model, or a small human check, confirms each perturbed problem is still
  solvable and its answer is unchanged. Drop any perturbation that fails.
- Report the perturbed accuracy next to the original, not only the gap. A collapse on both reads as
  "the rewording broke it", which is different from "the model memorised the original".

## Output

Per (model, split): `n`, `acc_original`, `acc_perturbed`, `gap`, plus a per-item gap. Published in
`results.json` under `perturbation`, next to `date_margins`, and re-gradable with `omnisbench verify`.

## Config

A `perturbation` block on a dataset:

```yaml
perturbation:
  strategies: [rename_identifiers, paraphrase_statement, reorder_examples]
  seed: 0
  generator: { provider: anthropic, model_id: "claude-opus-5" }   # offline, one-time
```

The probe run scores the pool on the original and the perturbed variant, then reports the gap.

## Cost

It doubles inference on the probed set (original plus perturbed), plus a one-time generation cost. Run
it on the fresh set at a small N, capped the same way the fresh run is.

## How to read the result

A model with a 20-point gap on a set is telling you its score there rode on the exact wording, so trust
its number on that set less. A model with a 2-point gap earned its score. Publish both accuracies and
the gap, and let the reader weigh it.

## Runs

### Current: runs/probe-clean-2026-08-24

Generator claude-sonnet-5 (outside the scored pool), validation on. Eight fresh LiveCodeBench
problems, 6 kept (abc387_f and abc394_d dropped, no model solved their reworded copy).

| Model | Original | Reworded | Gap |
|---|---:|---:|---:|
| claude-opus-5 | 100.0% | 83.3% | +16.7pp |
| gpt-5 | 66.7% | 50.0% | +16.7pp |
| claude-haiku-4-5 | 66.7% | 33.3% | +33.3pp |
| gpt-5-nano | 66.7% | 16.7% | +50.0pp |

gpt-5-nano loses most of its score to rewording, so its number on these recent problems rode on the
exact phrasing. opus-5 and gpt-5 hold up best. Residual caveat: sonnet-5 is the same provider family
as opus-5 and haiku-4-5, so a fully cross-family generator would be cleaner still. Cost: $2.11 in new
calls, on top of the reused fresh-set inference.

### First draft: runs/probe-2026-08-23

Generator claude-opus-5, no validation. Superseded, because opus-5 rewrote its own problems. That
flattered its gap (+12.5pp there against +16.7pp here) and inflated gpt-5's (+50pp there against
+16.7pp here) through rewordings only opus-5 could parse.
