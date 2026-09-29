"""Clone/update ComfyUI, install its requirements, configure model paths, and launch."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    from .common import DEFAULT_CONFIG, load_config, log_exception_summary, setup_logging
    from .drive_manager import get_storage_root, install_extra_model_paths
except ImportError:
    from common import DEFAULT_CONFIG, load_config, log_exception_summary, setup_logging
    from drive_manager import get_storage_root, install_extra_model_paths


class ComfySetupError(RuntimeError):
    pass


def ensure_comfyui_repo(repo_url: str, destination: str | Path, logger: Any = None) -> Path:
    path = Path(destination)
    if not (path / ".git").exists():
        if path.exists() and any(path.iterdir()):
            raise ComfySetupError(f"ComfyUI path exists but is not a Git checkout: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", repo_url, str(path)], check=True)
        if logger:
            logger.info("Cloned ComfyUI into %s", path)
    else:
        subprocess.run(["git", "-C", str(path), "pull", "--ff-only"], check=True)
        if logger:
            logger.info("Updated ComfyUI checkout at %s", path)
    return path


def install_requirements(comfyui_dir: str | Path, python_executable: str = sys.executable,
                         logger: Any = None) -> None:
    requirements = Path(comfyui_dir) / "requirements.txt"
    if not requirements.is_file():
        raise ComfySetupError(f"ComfyUI requirements file is missing: {requirements}")
    subprocess.run(
        [python_executable, "-m", "pip", "install", "--disable-pip-version-check", "-r", str(requirements)],
        check=True,
    )
    if logger:
        logger.info("ComfyUI dependencies installed from %s", requirements)


def prepare_comfyui(config: dict[str, Any], storage_root: str | Path, *, skip_dependencies: bool = False,
                    logger: Any = None) -> Path:
    comfy = ensure_comfyui_repo(
        str(config["comfyui_repo_url"]), config.get("comfyui_dir", "/content/ComfyUI"), logger,
    )
    install_extra_model_paths(comfy, storage_root)
    (comfy / "custom_nodes").mkdir(parents=True, exist_ok=True)
    if not skip_dependencies:
        install_requirements(comfy, logger=logger)
    return comfy


def launch_comfyui(comfyui_dir: str | Path, config: dict[str, Any], *, background: bool = True,
                   log_path: str | Path | None = None) -> subprocess.Popen[bytes] | None:
    host = str(config.get("comfyui_host", "0.0.0.0"))
    port = int(config.get("comfyui_port", 8188))
    command = [sys.executable, "main.py", "--listen", host, "--port", str(port)]
    cwd = Path(comfyui_dir)
    if background:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/system_stats", timeout=2) as response:
                if response.status == 200:
                    return None
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        output = open(log_path, "ab") if log_path else subprocess.DEVNULL
        return subprocess.Popen(command, cwd=cwd, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
    subprocess.run(command, cwd=cwd, check=True)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--storage-root", "--drive-root", dest="storage_root")
    parser.add_argument("--skip-dependencies", action="store_true")
    parser.add_argument("--foreground", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    root = get_storage_root(config, args.storage_root)
    logger = setup_logging(root / "logs")
    try:
        comfy = prepare_comfyui(config, root, skip_dependencies=args.skip_dependencies, logger=logger)
        output_log = root / "logs" / "comfyui.log"
        process = launch_comfyui(comfy, config, background=not args.foreground, log_path=output_log)
        if process:
            (root / "metadata" / "comfyui.pid").write_text(str(process.pid), encoding="utf-8")
        logger.info("ComfyUI launch requested at %s:%s", config.get("comfyui_host"), config.get("comfyui_port"))
        print(f"ComfyUI started. Local UI: http://127.0.0.1:{config.get('comfyui_port', 8188)}")
        print(f"ComfyUI log: {output_log}")
        print("In Colab, display the URL with google.colab.output.eval_js('google.colab.kernel.proxyPort(8188)').")
        return 0
    except Exception as error:  # noqa: BLE001
        log_exception_summary(
            logger, error,
            cause="Git access, dependency resolution, or the configured runtime path failed.",
            action="Review logs/setup.log, confirm the Colab runtime has internet access, then rerun this step.",
        )
        print(f"ERROR SUMMARY: {error}")
        print("POSSIBLE CAUSE: Git access, dependency resolution, or the configured runtime path failed.")
        print("RECOMMENDED ACTION: Review logs/setup.log, confirm the Colab runtime has internet access, then rerun this step.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
