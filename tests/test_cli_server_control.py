from __future__ import annotations

import json
from pathlib import Path

from rbo.cli import main
from rbo.server_control import conflicting_containers


def test_init_baselines_cli_creates_eight_grepable_bundles(tmp_path: Path) -> None:
    exit_code = main(["init-baselines", "--runs-root", str(tmp_path), "--timestamp", "20260526-1700", "--seeds", "20260413,20260414"])

    assert exit_code == 0
    bundles = sorted(p.name for p in tmp_path.iterdir() if p.is_dir())
    assert len(bundles) == 8
    assert any("plain-close_b8192_opt-12-24-27_s20260413-20260414" in name for name in bundles)
    ledger = [json.loads(line) for line in (tmp_path / "index.jsonl").read_text().splitlines()]
    assert len(ledger) == 8


def test_conflicting_containers_detects_everyday_vllm_but_not_rbo() -> None:
    docker_ps = "vllm\trunning\nrbo-vllm\trunning\nother\texited\n"
    assert conflicting_containers(docker_ps) == ["vllm"]
