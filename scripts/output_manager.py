"""Output naming and storage archival helpers."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


def slugify(value: str, fallback: str = "image") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip()).strip("-_")
    return cleaned[:64] or fallback


def make_output_filename(product: str, workflow: str, seed: int, *, date: str | None = None,
                         extension: str = ".png") -> str:
    date_part = date or datetime.now().strftime("%Y%m%d")
    # Metadata dates may be ISO values; output names intentionally use local calendar dates.
    date_part = date_part.split("T", 1)[0].replace("-", "")
    return f"{slugify(product)}_{slugify(workflow)}_{date_part}_seed{int(seed)}{extension}"


def write_output_bundle(source_image: str | Path, storage_root: str | Path, *, product: str,
                        workflow: str, seed: int, metadata: dict[str, Any],
                        category: str = "draft") -> tuple[Path, Path]:
    if category not in {"draft", "selected", "final"}:
        raise ValueError(f"Unsupported output category: {category}")
    directory = Path(storage_root) / "outputs" / category
    directory.mkdir(parents=True, exist_ok=True)
    filename = make_output_filename(product, workflow, seed, date=str(metadata.get("date", "")) or None)
    destination = directory / filename
    if destination.exists():
        # Keep previous results intact when the same seed is deliberately rerun.
        stem, suffix, index = destination.stem, destination.suffix, 2
        while destination.exists():
            destination = directory / f"{stem}_{index:02d}{suffix}"
            index += 1
    sidecar = destination.with_suffix(".json")
    shutil.copy2(source_image, destination)
    sidecar.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination, sidecar
