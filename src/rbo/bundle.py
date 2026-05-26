from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .domain import RunSpec, ServingConfig


def write_run_bundle(runs_root: Path, spec: RunSpec) -> Path:
    runs_root.mkdir(parents=True, exist_ok=True)
    bundle_dir = runs_root / spec.run_id
    rendered_dir = bundle_dir / "rendered"
    raw_dir = bundle_dir / "raw"
    reports_dir = bundle_dir / "reports"
    traces_dir = bundle_dir / "traces"
    for path in (rendered_dir, raw_dir, reports_dir, traces_dir):
        path.mkdir(parents=True, exist_ok=True)

    _write_json(bundle_dir / "manifest.json", spec.to_manifest())
    (rendered_dir / "compose.yaml").write_text(render_compose(spec.serving), encoding="utf-8")
    _write_json(rendered_dir / "request_config.json", spec.request.to_request_fields())
    _write_json(rendered_dir / "generation_config.json", _minimal_generation_config())
    _write_json(rendered_dir / "reasoning_config.json", spec.serving.reasoning_config.to_json_obj() if spec.serving.reasoning_config else None)
    (rendered_dir / "compose.env.redacted").write_text(_redacted_env(), encoding="utf-8")
    (bundle_dir / "attempts.jsonl").touch()

    _append_ledger(runs_root / "index.jsonl", spec, bundle_dir)
    return bundle_dir


def render_compose(serving: ServingConfig) -> str:
    command = [
        serving.model_id,
        f"--served-model-name={serving.served_model_name}",
        "--generation-config=/srv/vllm",
        "--host=0.0.0.0",
        "--port=30000",
        f"--tensor-parallel-size={serving.tensor_parallel_size}",
        f"--max-num-seqs={serving.max_num_seqs}",
        f"--max-model-len={serving.max_model_len}",
        f"--max-num-batched-tokens={serving.max_num_batched_tokens}",
        "--enable-auto-tool-choice",
        f"--tool-call-parser={serving.tool_call_parser}",
    ]
    if serving.reasoning_parser:
        command.append(f"--reasoning-parser={serving.reasoning_parser}")
    if serving.reasoning_config:
        command.extend(["--reasoning-config", json.dumps(serving.reasoning_config.to_json_obj(), separators=(",", ":"))])
    command.extend(
        [
            "--default-chat-template-kwargs",
            json.dumps({"preserve_thinking": True}, separators=(",", ":")),
            "--trust-remote-code",
            f"--gpu-memory-utilization={serving.gpu_memory_utilization}",
            "--disable-custom-all-reduce",
            "--enable-prefix-caching",
            "--async-scheduling",
        ]
    )
    command_yaml = "\n".join(f"      - {json.dumps(arg)}" for arg in command)
    return f"""services:
  vllm:
    image: {serving.image}
    container_name: {serving.container_name}
    gpus: all
    ipc: host
    ports:
      - \"{serving.host_port}:30000\"
    volumes:
      - /home/will/.cache/huggingface:/root/.cache/huggingface
      - /home/will/.cache/vllm:/root/.cache/vllm
      - ./generation_config.json:/srv/vllm/generation_config.json:ro
    environment:
      HF_TOKEN:
      HUGGING_FACE_HUB_TOKEN:
      PYTORCH_CUDA_ALLOC_CONF: expandable_segments:True
      VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS: \"1\"
      ENABLE_TRIATTENTION: \"false\"
      NVIDIA_VISIBLE_DEVICES: all
      NVIDIA_DRIVER_CAPABILITIES: compute,utility
    command:
{command_yaml}
"""


def _append_ledger(path: Path, spec: RunSpec, bundle_dir: Path) -> None:
    record = {
        "type": "run_bundle",
        "run_id": spec.run_id,
        "bundle_path": str(bundle_dir),
        "role": spec.role,
        "mode": spec.mode,
        "string_label": spec.string_label,
        "items": list(spec.item_ids),
        "seeds": list(spec.seeds),
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _minimal_generation_config() -> dict[str, Any]:
    return {
        "temperature": 0.95,
        "top_k": 20,
        "top_p": 0.95,
        "min_p": 0.0,
        "repetition_penalty": 1.0,
    }


def _redacted_env() -> str:
    return """HF_TOKEN=<inherited-from-host-env-if-set>
HUGGING_FACE_HUB_TOKEN=<inherited-from-host-env-if-set>
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS=1
ENABLE_TRIATTENTION=false
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility
"""
