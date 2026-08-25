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

## Runs and the gap matrix

The pool spans two providers, so a single rewriter isn't neutral to all of it. We reword the whole pool
with two generators, one per family, and read each model's gap under each. That also shows how much the
rewriter, rather than the model, drives the gap.

### The gap matrix

24 fresh LiveCodeBench problems, reworded by claude-sonnet-5 and by gpt-5, validation on (drop any
rewrite no model in the pool can solve).

```text
gap when reworded by       sonnet-5    gpt-5
claude-opus-5                +20.0      +5.9
claude-haiku-4-5             +40.0      +5.9
gpt-5                        +20.0     +23.5
gpt-5-nano                   +20.0     +52.9
                             n=15       n=17
```

How to read it:

- gpt-5 gives up about 20 points under either rewriter. A gap that survives changing the rewriter is a
  real wording-reliance signal for that model on this set.
- Every other model's gap swings with the rewriter. The Anthropic models drop about 6 points under
  gpt-5's rewrites and 20 to 40 under sonnet's. gpt-5-nano does the reverse. sonnet is a harsher
  rewriter than gpt-5, and the two runs keep different validated subsets (15 vs 17 tasks), so at this N
  the rewriter and the surviving tasks move the number more than the model does.
- What holds across the board: every model loses at least 6 points when a fresh problem is reworded. A
  post-cutoff date keeps the exact problem out of training. The phrasing and structure are not. Read the
  split label as necessary and not sufficient.

Ranking the pool by memorisation needs a larger N and several rewriters per model, so the model's signal
separates from the rewriter's. That's the roadmap for the probe.

### The source runs

- `runs/probe-sonnet-24-2026-08-25`: generator claude-sonnet-5, cross-family for the OpenAI models. Kept
  15 of 24. VERIFY OK.
- `runs/probe-gpt5-24-2026-08-25`: generator gpt-5, cross-family for the Anthropic models. Kept 17 of 24.
  VERIFY OK.

Both re-derive with `omnisbench verify`.

### Earlier runs (superseded)

- `runs/probe-2026-08-23`: generator claude-opus-5, no validation. opus-5 rewrote its own problems, which
  flattered its gap. Kept for the record.
- `runs/probe-clean-2026-08-24` and `runs/probe-openai-2026-08-24`: the first cross-family pair, 8 tasks
  each. Too small. The single-rewriter gaps they reported (nano +50pp, the frontier near zero) didn't
  survive rewording the pool twice at a larger N. Superseded by the 24-task runs above.
