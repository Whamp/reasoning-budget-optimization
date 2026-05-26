from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from .baseline_runner import plan_baseline_suite, run_baseline_suite
from .baselines import default_baseline_specs
from .bundle import write_run_bundle
from .runner import run_bundle
from .summary import format_summary_table, summarize_runs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rbo")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init-baselines", help="Create the required first baseline Run Bundles.")
    init.add_argument("--runs-root", type=Path, default=Path("runs"))
    init.add_argument("--timestamp", default=None, help="Grepable timestamp prefix, e.g. 20260526-1700.")
    init.add_argument("--seeds", default="20260413,20260414,20260415,20260416,20260417")

    run = sub.add_parser("run-bundle", help="Run an existing Run Bundle.")
    run.add_argument("bundle", type=Path)
    run.add_argument("--endpoint", default="http://localhost:30001/v1/chat/completions")
    run.add_argument("--api-key", default="EMPTY")
    run.add_argument("--start-serving", action="store_true", help="Start/recreate rbo-vllm from the bundle's rendered compose first.")
    run.add_argument("--tokenizer", help="Optional Hugging Face tokenizer name/path for reasoning-token budget-hit detection.")
    run.add_argument("--concurrency", type=int, default=8, help="Concurrent requests within a Run Bundle; default 8.")
    run.add_argument("--progress-every", type=int, default=1, help="Print progress after every N completed attempts; default 1, 0 disables.")

    suite = sub.add_parser("run-baselines", help="Run all pending baseline Run Bundles from the ledger.")
    suite.add_argument("--runs-root", type=Path, default=Path("runs"))
    suite.add_argument("--tokenizer", default="Jackrong/Qwopus3.6-27B-v2", help="Hugging Face tokenizer name/path for budget-hit detection.")
    suite.add_argument("--concurrency", type=int, default=8, help="Concurrent requests within each Run Bundle; default 8.")
    suite.add_argument("--progress-every", type=int, default=1, help="Print progress after every N completed attempts; default 1, 0 disables.")
    suite.add_argument("--no-start-serving", action="store_true", help="Do not start/recreate rbo-vllm before each bundle.")
    suite.add_argument("--rerun", action="store_true", help="Run completed bundles again instead of skipping them.")
    suite.add_argument("--dry-run", action="store_true", help="List pending bundles without starting serving or sending requests.")

    summary = sub.add_parser("summarize", help="Summarize run bundles from a runs root.")
    summary.add_argument("--runs-root", type=Path, default=Path("runs"))
    summary.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "init-baselines":
        timestamp = args.timestamp or datetime.utcnow().strftime("%Y%m%d-%H%M")
        seeds = _parse_seeds(args.seeds)
        specs = default_baseline_specs(timestamp=timestamp, seeds=seeds)
        for spec in specs:
            bundle = write_run_bundle(args.runs_root, spec)
            print(bundle)
        return 0

    if args.command == "run-bundle":
        tokenizer = _load_tokenizer(args.tokenizer) if args.tokenizer else None
        summary = run_bundle(args.bundle, endpoint=args.endpoint, api_key=args.api_key, start_serving=args.start_serving, tokenizer=tokenizer, concurrency=args.concurrency, progress_every=args.progress_every)
        print(summary)
        return 0

    if args.command == "run-baselines":
        if args.dry_run:
            planned = plan_baseline_suite(args.runs_root, rerun=args.rerun)
            if not planned:
                print("No pending baseline bundles. Use --rerun to include completed bundles.")
            else:
                for run_id in planned:
                    print(run_id)
            return 0
        tokenizer = _load_tokenizer(args.tokenizer) if args.tokenizer else None
        run_baseline_suite(
            args.runs_root,
            tokenizer=tokenizer,
            concurrency=args.concurrency,
            start_serving=not args.no_start_serving,
            rerun=args.rerun,
            progress_every=args.progress_every,
        )
        return 0

    if args.command == "summarize":
        rows = summarize_runs(args.runs_root)
        if args.json:
            import json

            print(json.dumps(rows, indent=2, sort_keys=True))
        else:
            print(format_summary_table(rows), end="")
        return 0

    return 1


def _load_tokenizer(name: str):
    try:
        from transformers import AutoTokenizer
    except ImportError as exc:
        raise SystemExit("Install tokenizer support with: uv run --extra tokenizer ...") from exc
    return AutoTokenizer.from_pretrained(name, trust_remote_code=True)


def _parse_seeds(value: str) -> list[int]:
    seeds: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            seeds.extend(range(int(start), int(end) + 1))
        else:
            seeds.append(int(part))
    if not seeds:
        raise argparse.ArgumentTypeError("at least one seed is required")
    return seeds


if __name__ == "__main__":
    raise SystemExit(main())
