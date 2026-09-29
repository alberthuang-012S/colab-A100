"""Google Drive mount detection and project folder management."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

try:
    from .common import DEFAULT_CONFIG, load_config, setup_logging
except ImportError:  # Support direct execution with `python scripts/drive_manager.py`.
    from common import DEFAULT_CONFIG, load_config, setup_logging


LAYOUT = (
    "models/flux", "models/sdxl", "models/lora", "models/controlnet", "models/vae",
    "workflows/text-to-image", "workflows/product-kv", "workflows/img2img",
    "workflows/inpaint", "workflows/outpaint", "workflows/batch",
    "assets/products", "assets/packaging", "assets/reference", "assets/branding",
    "prompts/products", "prompts/advertising", "prompts/website", "prompts/game",
    "prompts/styles", "outputs/draft", "outputs/selected", "outputs/final",
    "metadata", "logs",
)


def get_drive_root(config: dict[str, Any], override: str | Path | None = None) -> Path:
    if override:
        return Path(override).expanduser()
    env_override = os.environ.get("012S_DRIVE_ROOT")
    if env_override:
        return Path(env_override).expanduser()
    return Path(config.get("drive_root", "/content/drive/MyDrive/012s-image-system")).expanduser()


def is_drive_connected(config: dict[str, Any], root: str | Path | None = None) -> bool:
    mount_point = Path(config.get("drive_mount_point", "/content/drive"))
    if os.environ.get("COLAB_RELEASE_TAG"):
        return mount_point.exists() and (mount_point / "MyDrive").exists()
    selected_root = Path(root) if root else get_drive_root(config)
    # Local test/development roots are treated as connected when they already exist.
    return selected_root.exists()


def mount_google_drive() -> bool:
    """Mount Drive in Colab. Returns False outside Colab or when auth is unavailable."""
    try:
        from google.colab import drive  # type: ignore[import-not-found]
    except ImportError:
        return False
    drive.mount("/content/drive", force_remount=False)
    return True


def ensure_drive_layout(root: str | Path) -> list[Path]:
    base = Path(root).expanduser()
    created: list[Path] = []
    for relative in LAYOUT:
        directory = base / relative
        existed = directory.exists()
        directory.mkdir(parents=True, exist_ok=True)
        if not existed:
            created.append(directory)
    return created


def install_extra_model_paths(comfyui_dir: str | Path, drive_root: str | Path) -> Path:
    """Point ComfyUI model categories at persistent Drive folders."""
    comfy = Path(comfyui_dir)
    models = (Path(drive_root) / "models").resolve()
    content = (
        "012S Flux:\n"
        f"  base_path: {models.as_posix()}\n"
        "  checkpoints: flux/\n"
        "012S SDXL:\n"
        f"  base_path: {models.as_posix()}\n"
        "  checkpoints: sdxl/\n"
        "012S Shared:\n"
        f"  base_path: {models.as_posix()}\n"
        "  loras: lora/\n"
        "  controlnet: controlnet/\n"
        "  vae: vae/\n"
    )
    destination = comfy / "extra_model_paths.yaml"
    destination.write_text(content, encoding="utf-8")
    return destination


def sync_workflow_templates(project_root: str | Path, drive_root: str | Path) -> list[Path]:
    """Sync checked-in workflow/prompt templates without overwriting user edits."""
    source_root = Path(project_root)
    target_root = Path(drive_root)
    synced: list[Path] = []
    manifest_path = target_root / "metadata" / "workflow_templates_manifest.json"
    try:
        prior_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        prior_manifest = {}
    current_manifest: dict[str, str] = {}

    def digest(path: Path) -> str:
        sha = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                sha.update(block)
        return sha.hexdigest()

    for directory in ("workflows", "prompts"):
        source = source_root / directory
        if not source.exists():
            continue
        for source_file in source.rglob("*"):
            if not source_file.is_file():
                continue
            target = target_root / source_file.relative_to(source_root)
            target.parent.mkdir(parents=True, exist_ok=True)
            relative = source_file.relative_to(source_root).as_posix()
            source_hash = digest(source_file)
            prior_hash = prior_manifest.get(relative)
            replace = not target.exists()
            if target.exists():
                target_hash = digest(target)
                replace = target_hash == prior_hash and target_hash != source_hash
                if target_hash == source_hash:
                    current_manifest[relative] = source_hash
                    continue
            if replace:
                import shutil

                shutil.copy2(source_file, target)
                synced.append(target)
                current_manifest[relative] = source_hash
            else:
                # It is a local Drive edit or a pre-existing file from an unknown source.
                current_manifest[relative] = prior_hash or source_hash
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(current_manifest, indent=2) + "\n", encoding="utf-8")
    return synced


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--root", help="Override the Drive project root")
    parser.add_argument("--mount", action="store_true", help="Mount Google Drive when running in Colab")
    args = parser.parse_args()
    config = load_config(args.config)
    root = get_drive_root(config, args.root)
    logger = setup_logging(root / "logs")
    try:
        connected = mount_google_drive() if args.mount else is_drive_connected(config, root)
        if args.mount and not connected:
            connected = is_drive_connected(config, root)
        if not connected:
            print("Drive: NOT CONNECTED. In Colab, run the Drive mount cell and retry.")
            logger.warning("Drive is not connected at %s", root)
            return 2
        created = ensure_drive_layout(root)
        logger.info("Drive folders ready at %s (%s new folders)", root, len(created))
        print(f"Drive: Connected\nProject root: {root}\nFolders created: {len(created)}")
        return 0
    except Exception as error:  # noqa: BLE001 - report a concise recovery path to Colab users.
        logger.exception("Drive setup failed")
        print(f"ERROR SUMMARY: Could not prepare Google Drive folders: {error}")
        print("POSSIBLE CAUSE: Drive is not mounted or the account has not granted access.")
        print("RECOMMENDED ACTION: Rerun the notebook Drive mount cell, then run this step again.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
