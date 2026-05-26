from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

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
        summary = run_bundle(args.bundle, endpoint=args.endpoint, api_key=args.api_key, start_serving=args.start_serving)
        print(summary)
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
