# AIME25 reasoning-budget optimization subsamples

Goal: optimize `reasoning_end_str` for shorter enforced reasoning budgets without spending compute on AIME25 items that rarely trigger the budget cutoff.

Current served-model evidence comes from 9 AIME25 repeats of `Jackrong/Qwopus3.6-27B-v2` using:

- seeds: `20260413` through `20260421`
- `thinking_token_budget=32768`
- budget hit definition: tokenizer-estimated reasoning tokens `>= 32768`

## Primary optimization set

Use these items for fast iteration on candidate `reasoning_end_str` values:

```text
12, 24, 27
```

Rationale: these items hit the reasoning budget frequently and are solved at least once, so they have room for measurable improvement.

| Item | Budget hits / 9 | Correct / 9 | Role |
|---:|---:|---:|---|
| 12 | 5/9 | 2/9 | high-trigger, sometimes recoverable |
| 24 | 5/9 | 4/9 | high-trigger, mixed outcome |
| 27 | 5/9 | 3/9 | high-trigger, mixed outcome |

Expected iteration cost at current full 32k budget, running the three items concurrently:

- mean wall estimate: ~21.7 minutes
- median wall estimate: ~22.5 minutes
- observed range: ~19.8–22.9 minutes

## Guardrail set

Check these every ~5 optimization iterations, not as the main optimization objective:

```text
1, 19
```

Rationale: these items often trigger the budget cap but are already solved reliably. They detect whether an optimized cutoff string harms successful budget-exhausted solves.

| Item | Budget hits / 9 | Correct / 9 | Role |
|---:|---:|---:|---|
| 1 | 7/9 | 9/9 | high-trigger correct control |
| 19 | 7/9 | 9/9 | high-trigger correct control |

Expected guardrail pass cost with both items concurrent:

- mean wall estimate: ~22.2 minutes
- max observed: ~23.2 minutes

## Excluded from first-pass optimization

Do not use these in the first optimization loop:

```text
13, 14, 29
```

Rationale: they are never solved in the observed repeats, so they may measure model incapability rather than cutoff-string quality.

| Item | Budget hits / 9 | Correct / 9 | Reason excluded |
|---:|---:|---:|---|
| 13 | 9/9 | 0/9 | always capped, always wrong |
| 14 | 5/9 | 0/9 | often capped, always wrong |
| 29 | 9/9 | 0/9 | always capped, always wrong |

These may be useful later as adversarial/hard holdout cases, but not for first-pass string optimization.

## Proposed loop

1. Run candidate string on optimization set: `12,24,27`.
2. Compare exact accuracy, budget-hit behavior, completion tokens, reasoning/output token split, and latency.
3. Every ~5 candidates, run guardrail set: `1,19`.
4. Promote candidates only if they improve/match optimization-set accuracy and do not regress guardrails.
