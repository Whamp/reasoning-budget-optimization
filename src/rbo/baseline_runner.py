from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .runner import run_bundle
from .summary import format_summary_table, summarize_runs

Runner = Callable[..., dict[str, Any]]


def iter_bundle_paths(runs_root: Path, *, rerun: bool = False) -> list[Path]:
    ledger = runs_root / "index.jsonl"
    if not ledger.exists():
        raise FileNotFoundError(f"missing {ledger}; run `rbo init-baselines --runs-root {runs_root}` first")
    paths: list[Path] = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        bundle = Path(record["bundle_path"])
        if rerun or not (bundle / "reports" / "summary.json").exists():
            paths.append(bundle)
    return paths


def plan_baseline_suite(runs_root: Path, *, rerun: bool = False) -> list[str]:
    return [bundle.name for bundle in iter_bundle_paths(runs_root, rerun=rerun)]


def run_baseline_suite(
    runs_root: Path,
    *,
    tokenizer: Any | None,
    concurrency: int = 8,
    start_serving: bool = True,
    rerun: bool = False,
    progress_every: int = 1,
    runner: Runner = run_bundle,
) -> list[dict[str, Any]]:
    bundles = iter_bundle_paths(runs_root, rerun=rerun)
    if not bundles:
        print("No pending baseline bundles. Use --rerun to run completed bundles again.")
        return []

    summaries: list[dict[str, Any]] = []
    for index, bundle in enumerate(bundles, start=1):
        print(f"=== [{index}/{len(bundles)}] running {bundle.name} ===", flush=True)
        summary = runner(bundle, start_serving=start_serving, tokenizer=tokenizer, concurrency=concurrency, progress_every=progress_every)
        summaries.append(summary)
        print(format_summary_table(summarize_runs(runs_root)), end="", flush=True)
    return summaries
