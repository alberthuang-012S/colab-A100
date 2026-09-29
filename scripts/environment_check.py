"""Inspect Python, PyTorch, CUDA, GPU, and the selected storage backend."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    from .common import DEFAULT_CONFIG, load_config, setup_logging
except ImportError:
    from common import DEFAULT_CONFIG, load_config, setup_logging


@dataclass
class EnvironmentReport:
    python_version: str
    pytorch_version: str | None
    torch_cuda_version: str | None
    torch_cuda_available: bool
    gpu_exists: bool
    gpu_name: str | None
    vram_gb: float | None
    nvidia_smi_cuda_version: str | None
    storage_mode: str
    storage_root: str
    storage_available: bool
    drive_connected: bool | None
    status: str
    warnings: list[str]


def _nvidia_smi_info() -> dict[str, Any]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return {}
    try:
        result = subprocess.run(
            [executable, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, check=True,
        )
        first_line = result.stdout.strip().splitlines()[0]
        name, memory = (part.strip() for part in first_line.split(",", maxsplit=1))
        version_result = subprocess.run([executable], capture_output=True, text=True, timeout=10)
        cuda_version = None
        for line in version_result.stdout.splitlines():
            if "CUDA Version:" in line:
                cuda_version = line.split("CUDA Version:", 1)[1].split("|", 1)[0].strip()
                break
        return {"name": name, "vram_gb": round(float(memory) / 1024, 2), "cuda": cuda_version}
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return {}


def detect_environment(config: dict[str, Any], storage_root: str | Path | None = None) -> EnvironmentReport:
    warnings: list[str] = []
    torch_version = None
    torch_cuda = None
    torch_cuda_available = False
    gpu_name = None
    vram_gb = None
    try:
        import torch  # type: ignore[import-not-found]

        torch_version = str(torch.__version__)
        torch_cuda = str(torch.version.cuda) if torch.version.cuda else None
        torch_cuda_available = bool(torch.cuda.is_available())
        if torch_cuda_available:
            device_index = torch.cuda.current_device()
            gpu_name = torch.cuda.get_device_name(device_index)
            vram_gb = round(torch.cuda.get_device_properties(device_index).total_memory / (1024**3), 2)
    except Exception as error:  # noqa: BLE001 - importing torch may fail on mismatched runtimes.
        warnings.append(f"PyTorch CUDA check failed: {error}")

    nvidia = _nvidia_smi_info()
    gpu_exists = bool(torch_cuda_available or nvidia)
    if not gpu_name and nvidia.get("name"):
        gpu_name = nvidia["name"]
    if vram_gb is None and nvidia.get("vram_gb") is not None:
        vram_gb = nvidia["vram_gb"]
    try:
        from .drive_manager import get_storage_mode, get_storage_root, is_storage_available
    except ImportError:
        from drive_manager import get_storage_mode, get_storage_root, is_storage_available

    storage_mode = get_storage_mode(config)
    root = Path(storage_root).expanduser() if storage_root else get_storage_root(config)
    storage_available = is_storage_available(config, root, storage_mode)
    if storage_mode == "ephemeral":
        drive_connected = None
    else:
        try:
            from .drive_manager import is_drive_connected
        except ImportError:
            from drive_manager import is_drive_connected
        drive_connected = is_drive_connected(config, root)

    if not gpu_exists:
        warnings.append("No GPU detected; model downloads and generation are disabled by the launcher.")
    elif not torch_cuda_available:
        warnings.append("A GPU may be visible, but PyTorch CUDA support is unavailable.")
    if storage_mode == "drive" and not drive_connected:
        warnings.append(f"Google Drive is not mounted or the configured project root is absent: {root}")
    if not storage_available:
        warnings.append(f"Storage root is unavailable or not writable: {root}")
    if config.get("install_flux") and vram_gb is not None and vram_gb < 20:
        warnings.append(
            f"FLUX HARDWARE WARNING: detected {vram_gb:g} GB VRAM (<20 GB); this runtime is not an A100 FLUX verification."
        )

    status = "READY" if gpu_exists and torch_cuda_available and storage_available else "WARNING"
    return EnvironmentReport(
        python_version=platform.python_version(), pytorch_version=torch_version,
        torch_cuda_version=torch_cuda, torch_cuda_available=torch_cuda_available,
        gpu_exists=gpu_exists, gpu_name=gpu_name, vram_gb=vram_gb,
        nvidia_smi_cuda_version=nvidia.get("cuda"), storage_mode=storage_mode,
        storage_root=str(root), storage_available=storage_available,
        drive_connected=drive_connected, status=status, warnings=warnings,
    )


def format_report(report: EnvironmentReport) -> str:
    lines = [
        "012S Environment Report",
        f"Python: {report.python_version}",
        f"PyTorch: {report.pytorch_version or 'Unavailable'}",
        f"PyTorch CUDA support: {'Yes' if report.torch_cuda_available else 'No'}",
        f"CUDA: {report.torch_cuda_version or report.nvidia_smi_cuda_version or 'Unavailable'}",
        f"GPU: {report.gpu_name or 'Not detected'}",
        f"VRAM: {report.vram_gb:g} GB" if report.vram_gb is not None else "VRAM: Unknown",
        f"Storage Mode: {report.storage_mode}",
        f"Storage Root: {report.storage_root}",
        f"Drive: {'NOT REQUIRED' if report.drive_connected is None else ('Connected' if report.drive_connected else 'Not connected')}",
        f"Status: {report.status}",
    ]
    lines.extend(f"WARNING: {warning}" for warning in report.warnings)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--storage-root", "--drive-root", dest="storage_root")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()
    config = load_config(args.config)
    report = detect_environment(config, args.storage_root)
    logger = setup_logging(Path(report.storage_root) / "logs")
    logger.info("Environment report: %s", format_report(report).replace("\n", " | "))
    print(json.dumps(asdict(report), indent=2) if args.json else format_report(report))
    return 0 if report.status == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
