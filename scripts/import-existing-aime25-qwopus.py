#!/usr/bin/env python
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
if str(PROJECT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT / "src"))

from qwopus_eval.reasoning_budget_db import ExistingRunImport, import_existing_run  # noqa: E402
from qwopus_eval.token_report import load_tokenizer  # noqa: E402

DEFAULT_TRANSITION = "My reasoning budget is exhausted, but I have enough information to answer directly now."
DEFAULT_END_STR = DEFAULT_TRANSITION + "</think>"


def main() -> int:
    parser = argparse.ArgumentParser(description="Import existing Qwopus v2 AIME25 runs into the reasoning-budget optimization SQLite DB.")
    parser.add_argument("--db", type=Path, default=PROJECT / "reasoning-budget-optimization/results/budget-optimization.sqlite3")
    parser.add_argument("--model", default="Jackrong/Qwopus3.6-27B-v2")
    parser.add_argument("--tokenizer", default="Jackrong/Qwopus3.6-27B-v2")
    parser.add_argument("--thinking-token-budget", type=int, default=32768)
    parser.add_argument("--max-tokens", type=int, default=81920)
    parser.add_argument("--transition-text", default=DEFAULT_TRANSITION)
    parser.add_argument("--reasoning-end-str", default=DEFAULT_END_STR)
    parser.add_argument("--glob", default="home-aime25-seed-*-qwopus-v2-c8*.sqlite3")
    args = parser.parse_args()

    tokenizer = load_tokenizer(args.tokenizer)
    imported_total = 0
    run_count = 0
    for source_db in sorted((PROJECT / "checkpoints").glob(args.glob)):
        run_id = source_db.stem
        seed = _seed_from_run_id(run_id)
        if seed is None:
            continue
        if _source_has_run(source_db, run_id) == 0:
            continue
        imported = import_existing_run(
            ExistingRunImport(
                source_db=source_db,
                source_run_id=run_id,
                model=args.model,
                benchmark="aime25",
                seed=seed,
                thinking_token_budget=args.thinking_token_budget,
                max_tokens=args.max_tokens,
                reasoning_end_str=args.reasoning_end_str,
                transition_text=args.transition_text,
                tokenizer=tokenizer,
                notes="Imported from existing local AIME25 Qwopus v2 runs for reasoning_end_str optimization baseline.",
            ),
            args.db,
        )
        print(f"imported run_id={run_id} seed={seed} attempts={imported}")
        imported_total += imported
        run_count += 1
    print(f"done db={args.db} runs={run_count} attempts={imported_total}")
    return 0


def _seed_from_run_id(run_id: str) -> int | None:
    match = re.search(r"seed-(\d+)", run_id)
    return int(match.group(1)) if match else None


def _source_has_run(source_db: Path, run_id: str) -> int:
    con = sqlite3.connect(source_db)
    try:
        row = con.execute("SELECT count(*) FROM attempts WHERE run_id=?", (run_id,)).fetchone()
        return int(row[0])
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
