from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ItemProgress:
    attempts: int = 0
    budget_hits: int = 0
    correct: int = 0
    hit_correct: int = 0


@dataclass
class ProgressReporter:
    run_id: str
    total: int
    every: int = 1
    started_at: float = field(default_factory=time.monotonic)
    completed: int = 0
    correct: int = 0
    budget_hits: int = 0
    hit_correct: int = 0
    by_item: dict[str, ItemProgress] = field(default_factory=dict)

    def record(self, row: dict[str, Any]) -> None:
        self.completed += 1
        item_id = str(row.get("item_id", "?"))
        item = self.by_item.setdefault(item_id, ItemProgress())
        item.attempts += 1

        if row.get("correct"):
            self.correct += 1
            item.correct += 1
        if row.get("budget_hit"):
            self.budget_hits += 1
            item.budget_hits += 1
            if row.get("correct"):
                self.hit_correct += 1
                item.hit_correct += 1

        if self.every > 0 and (self.completed == 1 or self.completed == self.total or self.completed % self.every == 0):
            self.print(row)

    def print(self, row: dict[str, Any]) -> None:
        elapsed = max(time.monotonic() - self.started_at, 0.001)
        per_min = self.completed * 60 / elapsed
        remaining = max(self.total - self.completed, 0)
        eta_min = remaining / per_min if per_min > 0 else 0.0
        item_hits = ",".join(
            f"{item_id}:{p.budget_hits}/{p.attempts}"
            for item_id, p in sorted(self.by_item.items(), key=lambda kv: _item_sort_key(kv[0]))
        )
        print(
            "[progress] "
            f"run={self.run_id} completed={self.completed}/{self.total} "
            f"last_item={row.get('item_id')} seed={row.get('seed')} "
            f"correct={self.correct} budget_hits={self.budget_hits} hit_correct={self.hit_correct} "
            f"last_budget_hit={bool(row.get('budget_hit'))} method={row.get('hit_detection_method')} "
            f"latency_ms={row.get('latency_ms')} elapsed_min={elapsed / 60:.1f} eta_min={eta_min:.1f} "
            f"item_hits={item_hits}",
            flush=True,
        )


def _item_sort_key(value: str) -> tuple[int, str]:
    try:
        return (int(value), value)
    except ValueError:
        return (10**9, value)
