from __future__ import annotations

import json
from pathlib import Path

from rbo.baselines import default_baseline_specs
from rbo.bundle import write_run_bundle
from rbo.domain import render_reasoning_end_string, validate_transition_text


def test_transition_text_renders_close_token_and_rejects_think_tags() -> None:
    assert render_reasoning_end_string("") == "</think>"
    assert render_reasoning_end_string("I will answer now.") == "I will answer now.</think>"
    assert validate_transition_text("I will answer now.") == []
    assert validate_transition_text("bad </think>")
    assert validate_transition_text("bad <think>")


def test_default_baselines_cover_required_modes_and_roles() -> None:
    specs = default_baseline_specs(timestamp="20260526-1700", seeds=[20260413, 20260414])
    run_ids = [s.run_id for s in specs]

    assert len(specs) == 8
    assert any("prod-long_b8192_opt-12-24-27" in rid for rid in run_ids)
    assert any("prod-long_b8192_guard-1-19" in rid for rid in run_ids)
    assert any("plain-close_b8192_opt-12-24-27" in rid for rid in run_ids)
    assert any("server-prod-long_disabled_opt-12-24-27" in rid for rid in run_ids)
    assert any("no-reasoning-config_unlimited_guard-1-19" in rid for rid in run_ids)

    unlimited = next(s for s in specs if s.mode == "unlimited" and s.role == "opt")
    assert unlimited.serving.reasoning_parser is None
    assert unlimited.serving.reasoning_config is None

    disabled = next(s for s in specs if s.mode == "disabled" and s.role == "opt")
    assert disabled.serving.reasoning_config is not None
    assert disabled.request.chat_template_kwargs == {"enable_thinking": False}


def test_write_run_bundle_persists_manifest_rendered_config_and_ledger(tmp_path: Path) -> None:
    spec = default_baseline_specs(timestamp="20260526-1700", seeds=[20260413])[0]
    bundle_dir = write_run_bundle(tmp_path, spec)

    manifest = json.loads((bundle_dir / "manifest.json").read_text())
    assert manifest["run_id"] == spec.run_id
    assert manifest["storage_version"] == 1
    assert manifest["items"] == ["12", "24", "27"]
    assert manifest["seeds"] == [20260413]

    compose = (bundle_dir / "rendered" / "compose.yaml").read_text()
    assert "container_name: rbo-vllm" in compose
    assert '"30001:30000"' in compose
    assert "--reasoning-config" in compose

    request_config = json.loads((bundle_dir / "rendered" / "request_config.json").read_text())
    assert request_config["thinking_token_budget"] == 8192
    assert request_config["temperature"] == 0.95

    ledger_lines = (tmp_path / "index.jsonl").read_text().strip().splitlines()
    assert len(ledger_lines) == 1
    ledger = json.loads(ledger_lines[0])
    assert ledger["run_id"] == spec.run_id
    assert ledger["bundle_path"] == str(bundle_dir)
