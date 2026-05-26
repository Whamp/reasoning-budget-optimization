# Reasoning Budget Optimization

This context covers experiments that evaluate how server-enforced reasoning cutoffs affect model answer quality, latency, and token use. It separates the portable experiment harness from the GPU serving stack used to run model candidates.

## Language

**Experiment Harness**:
The portable system that defines experiments, runs evaluations, scores attempts, stores results, and drives optimizers.
_Avoid_: eval repo, scripts, runner when referring to the whole system

**Serving Stack**:
The Docker Compose based vLLM runtime that hosts a model behind an OpenAI-compatible API.
_Avoid_: server, endpoint when referring to the whole runtime configuration

**Experiment Serving Configuration**:
A reproducible serving configuration owned by this repo and rendered for an experiment run.
_Avoid_: production compose, mutable server config

**Experiment Serving Stack**:
The isolated Docker Compose runtime started by the Experiment Harness for evaluation, using container name `rbo-vllm` and API port `30001`.
_Avoid_: production vLLM, everyday service

**Reasoning End String**:
The complete string vLLM forces when a reasoning budget is exhausted, including any transition text and the reasoning close token.
_Avoid_: prompt, suffix

**Transition Text**:
The natural-language portion of the reasoning end string before the reasoning close token.
_Avoid_: end string when referring only to the natural-language phrase

**Reasoning Budget**:
The per-request maximum number of reasoning tokens allowed before vLLM forces the reasoning end string.
_Avoid_: token limit when referring specifically to thinking-token cutoff

**Reasoning Budget Mode**:
The run-level reasoning policy: `budgeted:<int>`, `unlimited`, or `disabled`.
_Avoid_: budget when referring to disabled or unlimited modes

**Cutoff-Capable Serving Configuration**:
An Experiment Serving Configuration that enables vLLM reasoning parsing and a server-scoped Reasoning End String so `thinking_token_budget` can force a reasoning cutoff.
_Avoid_: reasoning config when referring to the whole serving variant

**No-Reasoning-Config Serving Configuration**:
An Experiment Serving Configuration for unlimited reasoning baselines that removes vLLM reasoning-boundary intervention by omitting both `--reasoning-parser` and `--reasoning-config`.
_Avoid_: prod-long when referring to unlimited baseline serving identity

**Run Bundle**:
A directory containing the fully rendered configuration, raw responses, attempts, summaries, and logs for one evaluation run.
_Avoid_: run row, DB record when referring to reproducible artifacts

**JSONL Ledger**:
The append-only `runs/index.jsonl` file that records run-level facts and points to each Run Bundle.
_Avoid_: database, registry

**Run ID**:
A grepable identifier naming the evaluated condition for one Run Bundle, including model, string label, budget, item set, and seed set when practical.
_Avoid_: opaque UUID as the only run identifier

**Request Config**:
The explicit per-request decoding and reasoning-mode parameters used for an evaluation run.
_Avoid_: generation config when referring to authoritative eval sampling parameters

**Optimization Set**:
The AIME25 items used for fast iteration on transition-text quality: `12`, `24`, and `27`.
_Avoid_: training set when referring to the fixed first-pass eval subset

**Guardrail Set**:
The AIME25 items used to detect regressions on budget-exhausted solves that were already reliable: `1` and `19`.
_Avoid_: validation set when referring to this held-out regression subset

## Relationships

- An **Experiment Harness** owns one or more **Experiment Serving Configurations**.
- An **Experiment Serving Configuration** starts an **Experiment Serving Stack** for a specific model and server-scoped reasoning setup.
- The **Experiment Serving Stack** is isolated from the everyday **Serving Stack** by container name and port, but both contend for the same GPUs.
- The **Experiment Harness** fails fast when the everyday **Serving Stack** occupies GPUs; it does not stop that service automatically.
- A **Reasoning End String** contains optional **Transition Text** followed by the reasoning close token `</think>`.
- GEPA optimizes **Transition Text**; the **Experiment Harness** validates that it does not contain `<think>` or `</think>` and renders the **Reasoning End String** by appending `</think>`.
- The plain-close baseline is represented as empty **Transition Text** and **Reasoning End String** `</think>`.
- A **Reasoning Budget** is request-scoped, while a **Reasoning End String** is serving-scoped in the current vLLM deployment.
- **Reasoning Budget Mode** values are `budgeted:<int>` when a **Cutoff-Capable Serving Configuration** serves requests with `thinking_token_budget`, `unlimited` when a **No-Reasoning-Config Serving Configuration** serves requests without a forced cutoff, and `disabled` when a **Cutoff-Capable Serving Configuration** serves requests that explicitly disable thinking.
- The **Experiment Serving Stack** must not set a server-side default `thinking_token_budget`; that default cannot be reliably undone client-side and would invalidate `unlimited` runs.
- The `disabled` **Reasoning Budget Mode** uses the same **Cutoff-Capable Serving Configuration** as budgeted runs; only request-level chat-template kwargs disable thinking.
- The `unlimited` **Reasoning Budget Mode** uses a separate **No-Reasoning-Config Serving Configuration** so neither a reasoning parser nor a cutoff phrase participates in generation.
- A **Run Bundle** is the canonical reproducibility artifact for one evaluated condition: one serving configuration, one request decoding configuration, one reasoning budget mode, one item set, and one seed set. Budgeted and disabled Run Bundles also record the server-side **Reasoning End String**; unlimited Run Bundles record `no-reasoning-config` instead.
- A **Run Bundle** may contain multiple attempts across the seed set; each attempt records its individual seed.
- The **Request Config** is authoritative for eval decoding parameters; any mounted generation config is recorded but should stay minimal and stable.
- The **JSONL Ledger** indexes **Run Bundles** and is the v0 storage model; SQLite is deferred unless query needs justify it.
- A **Run ID** should be human-readable and grepable; timestamps may prefix it, but an opaque UUID should not be the only identifier.
- The first 8192 baseline uses the **Optimization Set** plus **Guardrail Set**, not all AIME25 items.
- Required first baselines are `prod-long` with `budgeted:8192`, `plain-close` with `budgeted:8192`, `disabled`, and `unlimited`.
- For `disabled` baseline identities, use `server-prod-long` to record the server-side **Reasoning End String** even though request-level thinking is disabled and transition text is not the measured variable.
- For `unlimited` baseline identities, use a serving-config label that records `no-reasoning-config` rather than `server-prod-long`.
- **Optimization Set** and **Guardrail Set** evaluations use separate **Run Bundles** because they have different roles and promotion semantics.

## Example dialogue

> **Dev:** "Can this experiment change the phrase without touching the production vLLM repo?"
> **Domain expert:** "Yes. The **Experiment Harness** renders its own **Experiment Serving Configuration**, restarts the **Experiment Serving Stack**, and records the resulting **Reasoning End String** with the run."

## Flagged ambiguities

- "server" can mean the physical `server60` machine, the vLLM Docker container, or the OpenAI-compatible endpoint. Use **Serving Stack** for the Docker Compose runtime and endpoint URL for the API surface.
