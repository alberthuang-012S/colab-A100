"""Build stable, JSON-serializable sidecar metadata for generated images."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def now_iso(timezone_name: str = "Asia/Taipei") -> str:
    try:
        return datetime.now(ZoneInfo(timezone_name)).isoformat(timespec="seconds")
    except ZoneInfoNotFoundError:
        return datetime.now().astimezone().isoformat(timespec="seconds")


def build_metadata(*, prompt: str, negative_prompt: str = "", seed: int,
                   model: str, model_version: str, workflow: str,
                   workflow_version: str, width: int | None, height: int | None,
                   steps: int | None, guidance: float | None, sampler: str | None,
                   scheduler: str | None, gpu: str | None,
                   generated_at: str | None = None, timezone_name: str = "Asia/Taipei",
                   extra: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "seed": int(seed),
        "model": model,
        "model_version": model_version,
        "workflow": workflow,
        "workflow_version": workflow_version,
        "width": width,
        "height": height,
        "steps": steps,
        "cfg_guidance": guidance,
        "sampler": sampler,
        "scheduler": scheduler,
        "date": generated_at or now_iso(timezone_name),
        "gpu": gpu,
    }
    if extra:
        metadata["extra"] = extra
    return metadata
