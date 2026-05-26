from __future__ import annotations

import json
import subprocess
import time
import urllib.request
from pathlib import Path


def conflicting_containers(docker_ps_output: str) -> list[str]:
    conflicts: list[str] = []
    for line in docker_ps_output.splitlines():
        parts = line.split("\t")
        if not parts:
            continue
        name = parts[0].strip()
        state = parts[1].strip().lower() if len(parts) > 1 else ""
        if name == "vllm" and state in {"running", "restarting", "paused"}:
            conflicts.append(name)
    return conflicts


def assert_no_conflicting_vllm() -> None:
    result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}\t{{.State}}"],
        check=True,
        text=True,
        capture_output=True,
    )
    conflicts = conflicting_containers(result.stdout)
    if conflicts:
        raise RuntimeError(
            "Everyday vLLM container is running and may occupy GPUs: "
            + ", ".join(conflicts)
            + ". Stop it yourself before running the experiment harness."
        )


def start_bundle_serving(bundle_dir: Path) -> None:
    assert_no_conflicting_vllm()
    rendered = bundle_dir / "rendered"
    log_path = bundle_dir / "raw" / "docker-compose-up.log"
    result = subprocess.run(
        ["docker", "compose", "-f", "compose.yaml", "up", "-d", "--force-recreate"],
        cwd=rendered,
        text=True,
        capture_output=True,
    )
    log_path.write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"docker compose up failed; see {log_path}")


def wait_ready(models_url: str, *, bundle_dir: Path, timeout_s: int = 900, interval_s: float = 5.0) -> None:
    deadline = time.monotonic() + timeout_s
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(models_url, timeout=10) as resp:  # noqa: S310 local/user endpoint
                payload = json.loads(resp.read().decode("utf-8"))
            raw = bundle_dir / "raw"
            raw.mkdir(exist_ok=True)
            (raw / "models.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return
        except Exception as exc:  # readiness loop intentionally broad
            last_error = repr(exc)
            time.sleep(interval_s)
    raise TimeoutError(f"vLLM did not become ready at {models_url}: {last_error}")
