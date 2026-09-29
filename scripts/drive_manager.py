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


STORAGE_MODES = {"drive", "ephemeral"}


def get_storage_mode(config: dict[str, Any], override: str | None = None) -> str:
    """Return the configured storage mode, with a per-runtime environment override."""
    mode = override or os.environ.get("012S_STORAGE_MODE") or config.get("storage_mode", "drive")
    normalized = str(mode).strip().lower()
    if normalized not in STORAGE_MODES:
        raise ValueError(f"Unsupported storage_mode {mode!r}; choose 'drive' or 'ephemeral'.")
    return normalized


def get_storage_root(config: dict[str, Any], override: str | Path | None = None,
                     *, storage_mode: str | None = None) -> Path:
    """Resolve the one shared root used for models, outputs, metadata, logs, and assets."""
    if override:
        return Path(override).expanduser()
    mode = get_storage_mode(config, storage_mode)
    env_override = os.environ.get("012S_STORAGE_ROOT")
    if env_override:
        return Path(env_override).expanduser()
    if mode == "ephemeral":
        return Path(os.environ.get("012S_EPHEMERAL_ROOT", config.get("ephemeral_root", "/content/012s-runtime"))).expanduser()
    legacy_override = os.environ.get("012S_DRIVE_ROOT")
    if legacy_override:
        return Path(legacy_override).expanduser()
    return Path(config.get("drive_root", "/content/drive/MyDrive/012s-image-system")).expanduser()


def get_drive_root(config: dict[str, Any], override: str | Path | None = None) -> Path:
    """Backward-compatible resolver for callers that explicitly need the Drive root."""
    return get_storage_root(config, override, storage_mode="drive")


def is_drive_connected(config: dict[str, Any], root: str | Path | None = None) -> bool:
    """Check the Drive mount itself (ephemeral storage must not call this)."""
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


def ensure_storage_layout(root: str | Path) -> list[Path]:
    """Create the shared data layout under either persistent or ephemeral storage."""
    base = Path(root).expanduser()
    created: list[Path] = []
    for relative in LAYOUT:
        directory = base / relative
        existed = directory.exists()
        directory.mkdir(parents=True, exist_ok=True)
        if not existed:
            created.append(directory)
    return created


def ensure_drive_layout(root: str | Path) -> list[Path]:
    """Backward-compatible name for the shared storage layout initializer."""
    return ensure_storage_layout(root)


def is_storage_available(config: dict[str, Any], root: str | Path,
                         storage_mode: str | None = None) -> bool:
    mode = get_storage_mode(config, storage_mode)
    selected_root = Path(root).expanduser()
    if not selected_root.is_dir() or not os.access(selected_root, os.W_OK):
        return False
    if mode == "ephemeral":
        return True
    return is_drive_connected(config, selected_root)


def install_extra_model_paths(comfyui_dir: str | Path, storage_root: str | Path) -> Path:
    """Point ComfyUI model categories at the selected storage folders."""
    comfy = Path(comfyui_dir)
    models = (Path(storage_root) / "models").resolve()
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


def sync_workflow_templates(project_root: str | Path, storage_root: str | Path) -> list[Path]:
    """Sync checked-in workflow/prompt templates without overwriting user edits."""
    source_root = Path(project_root)
    target_root = Path(storage_root)
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
    root = get_storage_root(config, args.root)
    logger = setup_logging(root / "logs")
    try:
        mode = get_storage_mode(config)
        if args.mount and mode == "drive":
            mount_google_drive()
        connected = is_storage_available(config, root, mode)
        if not connected:
            print(f"Storage: NOT AVAILABLE ({mode}) at {root}")
            logger.warning("Storage is not available at %s", root)
            return 2
        created = ensure_storage_layout(root)
        logger.info("Storage folders ready at %s (%s new folders)", root, len(created))
        drive_state = "NOT REQUIRED" if mode == "ephemeral" else "Connected"
        print(f"Storage Mode: {mode}\nStorage Root: {root}\nDrive: {drive_state}\nFolders created: {len(created)}")
        return 0
    except Exception as error:  # noqa: BLE001 - report a concise recovery path to Colab users.
        logger.exception("Drive setup failed")
        print(f"ERROR SUMMARY: Could not prepare storage folders: {error}")
        print("POSSIBLE CAUSE: The selected storage root is unavailable or not writable.")
        print("RECOMMENDED ACTION: Check Storage Mode and Storage Root, then rerun this step.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
