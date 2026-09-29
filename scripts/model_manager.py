"""Idempotent model inventory and resumable downloads to Google Drive."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from .common import DEFAULT_CONFIG, load_config, log_exception_summary, setup_logging
    from .drive_manager import ensure_storage_layout, get_storage_root
except ImportError:
    from common import DEFAULT_CONFIG, load_config, log_exception_summary, setup_logging
    from drive_manager import ensure_storage_layout, get_storage_root


class AuthRequiredError(RuntimeError):
    """The model host rejected the request because access or a token is required."""


@dataclass
class ModelSyncReport:
    installed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    auth_required: list[str] = field(default_factory=list)


def sha256_file(path: str | Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_is_valid(path: str | Path, model_info: dict[str, Any], expected_sha256: str | None = None) -> bool:
    candidate = Path(path)
    if not candidate.is_file() or candidate.stat().st_size < int(model_info.get("min_size_bytes", 0)):
        return False
    expected_size = model_info.get("expected_size_bytes")
    if expected_size is not None and candidate.stat().st_size != int(expected_size):
        return False
    if expected_sha256:
        return sha256_file(candidate).lower() == expected_sha256.lower()
    return True


def model_cached_valid(path: str | Path, model_info: dict[str, Any], expected_sha256: str | None = None) -> bool:
    """Verify a model once, then trust its Drive-side checksum marker on later starts."""
    candidate = Path(path)
    if not model_is_valid(candidate, model_info):
        return False
    if not expected_sha256:
        return True
    marker = candidate.with_name(candidate.name + ".sha256")
    try:
        if marker.read_text(encoding="ascii").strip().lower() == expected_sha256.lower():
            return True
    except OSError:
        pass
    actual = sha256_file(candidate)
    if actual.lower() != expected_sha256.lower():
        return False
    try:
        marker.write_text(actual + "\n", encoding="ascii")
    except OSError:
        # The verified model is still usable if Drive refuses the small cache marker.
        pass
    return True


def _auth_header() -> dict[str, str]:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def download_model(model_info: dict[str, Any], destination: str | Path, *, timeout: int = 120,
                   expected_sha256: str | None = None) -> Path:
    """Download with HTTP Range resume, validate size/hash, and atomically install."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    min_size = int(model_info.get("min_size_bytes", 0))
    if model_is_valid(destination, model_info, expected_sha256):
        return destination
    if destination.exists():
        stamp = int(time.time())
        quarantine = destination.with_name(f"{destination.name}.invalid-{stamp}")
        shutil.move(str(destination), str(quarantine))

    partial = destination.with_name(destination.name + ".part")
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "012S-image-system/1.0", **_auth_header()}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = urllib.request.Request(str(model_info["url"]), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            append = offset > 0 and response.status == 206
            if offset and not append:
                offset = 0
            mode = "ab" if append else "wb"
            with partial.open(mode) as output:
                shutil.copyfileobj(response, output, length=8 * 1024 * 1024)
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise AuthRequiredError(str(model_info.get("auth_required_hint", "Model host requires authentication."))) from error
        if error.code == 416 and partial.exists():
            if model_is_valid(partial, model_info, expected_sha256):
                os.replace(partial, destination)
                if expected_sha256:
                    destination.with_name(destination.name + ".sha256").write_text(expected_sha256.lower() + "\n", encoding="ascii")
                return destination
            quarantine_part = partial.with_name(partial.name + f".invalid-{int(time.time())}")
            os.replace(partial, quarantine_part)
            raise RuntimeError(f"Server rejected the resume range; partial download was moved to {quarantine_part}") from error
        raise RuntimeError(f"HTTP {error.code} while downloading {model_info['filename']}") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise RuntimeError(f"Download failed for {model_info['filename']}: {error}") from error

    if partial.stat().st_size < min_size:
        raise RuntimeError(
            f"Downloaded file is smaller than expected ({partial.stat().st_size} < {min_size} bytes); "
            f"partial file retained for resume at {partial}"
        )
    expected_size = model_info.get("expected_size_bytes")
    if expected_size is not None and partial.stat().st_size != int(expected_size):
        raise RuntimeError(
            f"Downloaded file size does not match the pinned model ({partial.stat().st_size} != {expected_size}); "
            f"partial file retained at {partial}"
        )
    if expected_sha256 and sha256_file(partial).lower() != expected_sha256.lower():
        raise RuntimeError(f"SHA-256 validation failed for {model_info['filename']}; partial file retained")
    os.replace(partial, destination)
    if expected_sha256:
        destination.with_name(destination.name + ".sha256").write_text(expected_sha256.lower() + "\n", encoding="ascii")
    return destination


def selected_models(config: dict[str, Any], *, install_flux: bool | None = None,
                    install_sdxl: bool | None = None) -> dict[str, list[dict[str, Any]]]:
    flux = config.get("install_flux", False) if install_flux is None else install_flux
    sdxl = config.get("install_sdxl", False) if install_sdxl is None else install_sdxl
    models = config.get("models", {})
    return {name: models.get(name, []) for name, enabled in (("flux", flux), ("sdxl", sdxl)) if enabled}


def sync_models(config: dict[str, Any], storage_root: str | Path, *, install_flux: bool | None = None,
                install_sdxl: bool | None = None, logger: Any = None) -> ModelSyncReport:
    root = Path(storage_root)
    ensure_storage_layout(root)
    report = ModelSyncReport()
    selections = selected_models(config, install_flux=install_flux, install_sdxl=install_sdxl)
    if not selections:
        if logger:
            logger.info("No model categories selected for installation")
        return report
    downloads_allowed = bool(os.environ.get("COLAB_RELEASE_TAG") or os.environ.get("012S_ALLOW_MODEL_DOWNLOAD"))
    if downloads_allowed:
        try:
            from .environment_check import detect_environment
        except ImportError:
            from environment_check import detect_environment
        environment = detect_environment(config, root)
        if not environment.gpu_exists or not environment.torch_cuda_available:
            report.skipped.append("downloads blocked because a CUDA-capable GPU was not detected")
            if logger:
                logger.warning("Model downloads blocked: environment has no usable CUDA GPU")
            return report
    for category, entries in selections.items():
        for model in entries:
            model_name = model["filename"]
            destination = root / "models" / category / model_name
            expected = config.get("model_sha256", {}).get(model_name)
            if model_cached_valid(destination, model, expected):
                report.skipped.append(f"{category}/{model_name}")
                if logger:
                    logger.info("Model exists; skipping: %s", destination)
                continue
            if not os.environ.get("COLAB_RELEASE_TAG") and not os.environ.get("012S_ALLOW_MODEL_DOWNLOAD"):
                message = f"Download not started outside Colab: {destination}. Set 012S_ALLOW_MODEL_DOWNLOAD=1 to opt in."
                report.skipped.append(f"{category}/{model_name} (download disabled outside Colab)")
                if logger:
                    logger.warning(message)
                continue
            last_error: Exception | None = None
            attempts = max(1, int(config.get("model_retry_count", 3)))
            for attempt in range(1, attempts + 1):
                try:
                    download_model(
                        model, destination,
                        timeout=int(config.get("download_timeout_seconds", 120)),
                        expected_sha256=expected,
                    )
                    report.installed.append(f"{category}/{model_name}")
                    if logger:
                        logger.info("Model installed: %s", destination)
                    last_error = None
                    break
                except AuthRequiredError as error:
                    report.auth_required.append(f"{category}/{model_name}: {error}")
                    if logger:
                        logger.error("AUTH REQUIRED for %s: %s", model_name, error)
                    last_error = None
                    break
                except Exception as error:  # noqa: BLE001 - attempt retry and report once.
                    last_error = error
                    if logger:
                        logger.warning("Download attempt %d/%d failed for %s: %s", attempt, attempts, model_name, error)
                    if attempt < attempts:
                        time.sleep(min(attempt * 2, 10))
            if last_error:
                report.failed.append(f"{category}/{model_name}: {last_error}")
                if logger:
                    logger.error("Model download failed: %s", model_name)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--storage-root", "--drive-root", dest="storage_root")
    parser.add_argument("--install-flux", action="store_true", default=None)
    parser.add_argument("--skip-flux", action="store_true")
    parser.add_argument("--install-sdxl", action="store_true", default=None)
    parser.add_argument("--skip-sdxl", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    root = get_storage_root(config, args.storage_root)
    logger = setup_logging(root / "logs")
    report = sync_models(
        config, root,
        install_flux=False if args.skip_flux else args.install_flux,
        install_sdxl=False if args.skip_sdxl else args.install_sdxl,
        logger=logger,
    )
    print("Models installed:", report.installed or "None")
    print("Models skipped:", report.skipped or "None")
    for message in report.auth_required:
        print("AUTH REQUIRED:", message)
    for message in report.failed:
        print("ERROR SUMMARY:", message)
        print("POSSIBLE CAUSE: Network failure, insufficient Drive space, or an incomplete remote response.")
        print("RECOMMENDED ACTION: Check Drive quota/network and retry; the .part file can resume.")
    return 2 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
