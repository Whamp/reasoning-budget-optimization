# Reasoning budget optimization

Portable harness for evaluating vLLM/Qwen reasoning-budget transition text. The long-term goal is to find **Transition Text** that improves answer quality when vLLM enforces a reasoning cutoff, without accepting pathological reasoning latency.

## Current focus: baseline harness

The repo currently focuses on reproducible baseline runs, not candidate generation. v0 proves that we can clone the repo to `server60`, start an isolated `rbo-vllm` container, run fixed AIME25 baseline bundles, and record self-contained run artifacts.

GEPA/candidate search comes after this baseline path is proven.

## Domain language

See [`CONTEXT.md`](./CONTEXT.md) for the shared glossary. Key terms:

- **Transition Text**: phrase before `</think>`; this is what GEPA will eventually optimize.
- **Reasoning End String**: full forced string vLLM emits on budget exhaustion, including `</think>`.
- **Run Bundle**: reproducible artifact directory for one evaluated condition.
- **JSONL Ledger**: append-only `runs/index.jsonl` pointing to Run Bundles.
- **Reasoning Budget Mode**: `budgeted:<int>`, `disabled`, or `unlimited`.

## Server60 location

Recommended clone location on `server60`:

```bash
/home/will/inference/experiments/reasoning-budget-optimization
```

The harness owns its own experiment serving compose and uses:

- container name: `rbo-vllm`
- host API port: `30001`
- OpenAI-compatible endpoint: `http://localhost:30001/v1/chat/completions`

It fails fast if the everyday `vllm` container is running. Stop that service manually when you are ready to dedicate the GPUs to experiments.

## First baselines

Required first baseline matrix:

1. `prod-long` + `budgeted:8192`
2. `plain-close` + `budgeted:8192`
3. `server-prod-long` + `disabled`
4. `no-reasoning-config` + `unlimited`

Each baseline is split into separate Run Bundles for:

- optimization set: AIME25 items `12,24,27`
- guardrail set: AIME25 items `1,19`

Default seeds:

```text
20260413,20260414,20260415,20260416,20260417
```

## Usage

From a checkout:

```bash
python -m pytest -q

PYTHONPATH=src python -m rbo.cli init-baselines \
  --runs-root runs \
  --seeds 20260413,20260414,20260415,20260416,20260417
```

This creates eight grepable Run Bundles under `runs/` and appends entries to `runs/index.jsonl`.

Run one bundle, starting/recreating `rbo-vllm` from its rendered compose first. Use tokenizer support so plain-close runs can detect budget hits even when vLLM strips `</think>` from the parsed reasoning field:

```bash
uv run --extra tokenizer rbo run-bundle \
  runs/<run-id> \
  --start-serving \
  --tokenizer Jackrong/Qwopus3.6-27B-v2
```

Summarize all bundles:

```bash
PYTHONPATH=src python -m rbo.cli summarize --runs-root runs
```

## Run Bundle shape

```text
runs/<run-id>/
  manifest.json
  attempts.jsonl
  rendered/
    compose.yaml
    compose.env.redacted
    generation_config.json
    reasoning_config.json
    request_config.json
  raw/
    responses.jsonl
    models.json
    docker-compose-up.log
  reports/
    summary.json
    summary.md
  traces/
```

SQLite is intentionally not part of the v0 storage model. The existing historical SQLite file remains as imported design evidence only.

## Historical evidence

Existing imported 32768-budget evidence lives at:

```text
results/budget-optimization.sqlite3
```

It contains historical AIME25 runs for `Jackrong/Qwopus3.6-27B-v2` using the production long reasoning end string at `thinking_token_budget=32768`. Do not compare new 8192-budget candidates directly against this historical baseline except as coarse context.

Quick historical query:

```bash
sqlite3 results/budget-optimization.sqlite3 \
  'select * from string_eval_summary;'
```

## Candidate constraints for later GEPA work

Initial constraints for generated Transition Text:

- English only.
- Single sentence or sentence fragment.
- Must not include `<think>` or `</think>`; the harness appends `</think>`.
- Target <= 120 characters; hard cap <= 200 characters.
- Tell the model to stop exploring and produce the best final answer from current work.
- Avoid hidden-reasoning/meta/server language, benchmark names, item IDs, AIME, seeds, or subset details.
- Do not ask the model to restart solving from scratch.
