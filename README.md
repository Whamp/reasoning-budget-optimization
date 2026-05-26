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

Serving defaults for baseline throughput:

- `--max-num-seqs=8`
- request concurrency: `8`
- `--gpu-memory-utilization=0.9`
- budgeted serving cap: `--max-model-len=131072`, request `max_tokens=81920`
- disabled/unlimited serving cap: `--max-model-len=262144`, request `max_tokens=81920`

The existing 32768-budget evidence for selected items `1,12,19,24,27` had max observed total tokens `49984`, but Qwen's model card recommends maintaining at least 128K context to preserve thinking capabilities. The budgeted baseline therefore uses 128K rather than a tighter 65K cap. Disabled and unlimited baselines keep the full 262K context because disabled models can compensate by moving reasoning into visible output, and unlimited is the high-ceiling no-cutoff reference condition.

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

Preview pending baselines:

```bash
uv run rbo run-baselines --runs-root runs --dry-run
```

Run all pending baselines. This starts/recreates `rbo-vllm` from each bundle's rendered compose, uses request concurrency 8 inside each bundle, skips completed bundles by default, prints per-attempt progress with per-item budget-hit counters, and prints a summary after each bundle:

```bash
uv run --extra tokenizer rbo run-baselines \
  --runs-root runs \
  --tokenizer Jackrong/Qwopus3.6-27B-v2 \
  --concurrency 8 \
  --progress-every 1
```

Run one bundle manually if needed:

```bash
uv run --extra tokenizer rbo run-bundle \
  runs/<run-id> \
  --start-serving \
  --tokenizer Jackrong/Qwopus3.6-27B-v2 \
  --concurrency 8 \
  --progress-every 1
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
