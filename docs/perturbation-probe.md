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

## Runs and the cross-family view

The pool spans two providers, so no single generator is cross-family to all of it. We rework with one
generator per family and read each model's gap from the run whose generator is a different provider.

### Cross-family gap

Each model reworded by a model from the other provider, validation on.

| Model | Reworded by | Original | Reworded | Gap |
|---|---|---:|---:|---:|
| claude-opus-5 | gpt-5 | 100.0% | 85.7% | +14.3pp |
| gpt-5 | claude-sonnet-5 | 66.7% | 50.0% | +16.7pp |
| claude-haiku-4-5 | gpt-5 | 42.9% | 42.9% | +0.0pp |
| gpt-5-nano | claude-sonnet-5 | 66.7% | 16.7% | +50.0pp |

gpt-5-nano loses most of its score to the cross-family rewrite, and it drops as hard under the other
generator (+71.4pp), so that signal holds. opus-5 and gpt-5 hold up well. haiku shows no gap under
gpt-5 rewording and +33.3pp under sonnet, so at 6 to 7 tasks per model it sits in the noise. The read
that survives: the smallest model's recent score leans on the wording, the frontier models earn theirs.

### The two source runs

- `runs/probe-clean-2026-08-24`: generator claude-sonnet-5, cross-family for the OpenAI models. Kept 6
  of 8 tasks. $2.11.
- `runs/probe-openai-2026-08-24`: generator gpt-5, cross-family for the Anthropic models. Kept 7 of 8.
  $1.98.

Both re-derive with `omnisbench verify`.

### First draft: runs/probe-2026-08-23 (superseded)

Generator claude-opus-5, no validation. opus-5 rewrote its own problems, which flattered its gap and
inflated gpt-5's through rewordings only opus-5 could parse. Kept for the record.
