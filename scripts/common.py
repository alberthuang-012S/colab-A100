"""Shared configuration, path, and logging helpers."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "system_config.json"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_CONFIG
    with config_path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    if not isinstance(config, dict):
        raise ValueError(f"Configuration must be a JSON object: {config_path}")
    return config


def configured_path(value: str | Path, *, env_name: str | None = None) -> Path:
    """Resolve config paths while allowing a Colab environment override."""
    raw = os.environ.get(env_name, str(value)) if env_name else str(value)
    return Path(raw).expanduser()


def setup_logging(log_dir: str | Path, name: str = "012s") -> logging.Logger:
    directory = Path(log_dir)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(directory / "setup.log", encoding="utf-8")
    except OSError:
        # On a local development machine the Colab Drive path is not writable.
        # Keep diagnostics in the repository instead of failing before the report.
        directory = PROJECT_ROOT / "logs"
        directory.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(directory / "setup.log", encoding="utf-8")
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def log_exception_summary(logger: logging.Logger, error: BaseException, *, cause: str, action: str) -> None:
    logger.error("ERROR SUMMARY: %s", error)
    logger.error("POSSIBLE CAUSE: %s", cause)
    logger.error("RECOMMENDED ACTION: %s", action)
