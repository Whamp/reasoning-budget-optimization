# Reasoning budget optimization

Workspace for optimizing the Qwen/Qwopus `reasoning_end_str` transition phrase used when vLLM enforces a `thinking_token_budget`.

## Goal

Long-term goal: enforce shorter reasoning budgets while preserving task accuracy. We want a better transition phrase for the moment vLLM cuts off reasoning and injects a forced reasoning end, so the model uses its partial work to produce the best possible final answer instead of collapsing, rambling, or guessing poorly.

Current optimization target: AIME25 items that frequently hit the reasoning budget but are still solvable at least sometimes. Items that rarely hit the budget waste compute for this project because the optimized string is never injected. Items that always hit the budget and are never correct may also be poor first-pass targets because they may measure model incapability rather than string quality.

This workspace should support comparing multiple `reasoning_end_str` candidates across:

- reasoning budgets, starting with `thinking_token_budget=8192`;
- selected high-budget-hit AIME25 items;
- hit-conditioned accuracy, not just overall accuracy;
- token/latency costs;
- guardrails that catch regressions on budget-hit items the model already solves.

The existing 32768-budget data is imported as design evidence and historical baseline context. Candidate strings at 8192 require fresh baselines at that same budget.

Current production string:

```text
My reasoning budget is exhausted, but I have enough information to answer directly now.</think>
```

Transition phrase under optimization:

```text
My reasoning budget is exhausted, but I have enough information to answer directly now.
```

## Current database

SQLite DB:

```text
results/budget-optimization.sqlite3
```

Imported baseline evidence:

- model: `Jackrong/Qwopus3.6-27B-v2`
- benchmark: `aime25`
- seeds: `20260413` through `20260421`
- budget: `thinking_token_budget=32768`, `max_tokens=81920`
- reasoning end string: current production string above
- completed attempts: `270`
- aggregate: `222/270 = 82.22%`

Quick queries:

```bash
sqlite3 results/budget-optimization.sqlite3 \
  'select * from string_eval_summary;'

sqlite3 results/budget-optimization.sqlite3 \
  "select item_id, attempts, budget_hits, correct, wrong, hit_correct, hit_wrong from budget_hit_item_summary order by cast(item_id as int);"
```

## Selected subsets

Primary optimization items:

```text
12, 24, 27
```

Guardrail items:

```text
1, 19
```

See `notes/subsample-selection.md` for rationale and timing estimates.

## Baselines needed at 8192

We are moving optimization to:

```text
thinking_token_budget=8192
```

Before judging candidate strings, create baselines at the same budget:

1. current production phrase:
   `My reasoning budget is exhausted, but I have enough information to answer directly now.</think>`
2. plain end token only:
   `</think>`
3. reasoning disabled / no-reasoning baseline, if supported by the server/client stack.

Do not compare 8192-budget candidates against the existing 32768-budget baseline except for coarse context.

## Open implementation questions

### 1. Can `reasoning_end_str` be changed per request?

Current evidence from vLLM docs/code suggests `reasoning_end_str` is part of server/LLM `reasoning_config`, while `thinking_token_budget` is a per-request sampling parameter. That likely means testing a new `reasoning_end_str` requires a vLLM server restart with a new `--reasoning-config`.

Action: verify empirically before building orchestration. Try sending a request-level `reasoning_config` override and confirm whether vLLM accepts, rejects, or ignores it. If ignored/rejected, candidate evaluation needs server restart per string.

### 2. How should candidates be scored?

Score only after enough budget-hit attempts are observed per item. Proposed first pass:

- optimization set: `12,24,27`
- target: at least `3` budget hits per item for cheap screening, then `5` for stronger checks
- primary metric: accuracy among budget-hit attempts
- secondary metrics: overall accuracy, hit rate, reasoning/output/completion tokens, latency

### 3. Constraints for candidate transition phrases

Initial constraints for candidate generation:

- English only.
- Must be a single sentence or sentence fragment.
- Must not include the literal tokens `<think>` or `</think>`; the harness appends `</think>`.
- Prefer short strings: target <= 120 characters; hard cap <= 200 characters.
- Should tell the model to stop exploring and produce the best final answer from current work.
- Should avoid mentioning hidden reasoning, benchmark names, item IDs, AIME, seeds, or the optimization subset.
- Should not ask the model to restart solving from scratch.

### 4. Context for candidate-generating model / GEPA

Give the optimizer:

- task: AIME-style math; final answer must be boxed integer.
- mechanism: phrase is injected only when reasoning budget is exhausted, immediately before `</think>`.
- goal: preserve useful partial reasoning and force concise final-answer synthesis.
- constraints above.
- aggregate metrics only, not item-specific solutions, to reduce overfitting.
- optimization items are selected for high budget-hit frequency and mixed solvability, but candidate text must generalize to unseen math problems.

Hold out guardrail items `1,19` to detect regressions in budget-exhausted solves that were already correct.

## GEPA fit

DSPy/GEPA looks appropriate as a candidate-string optimizer because the object being optimized is natural-language program text. Treat `reasoning_end_str` transition text as the prompt/program parameter and use the harness metric as feedback.

Recommended shape:

1. Generate candidate transition phrase.
2. Restart/serve vLLM with candidate `reasoning_end_str` if per-request override is unavailable.
3. Run optimization subset until hit quota is met.
4. Return metric bundle to optimizer.
5. Periodically evaluate guardrails.
