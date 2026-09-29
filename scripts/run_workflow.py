"""Submit a named workflow to ComfyUI and archive images plus metadata in storage."""

from __future__ import annotations

import argparse
import json
import logging
import secrets
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

try:
    from .common import DEFAULT_CONFIG, PROJECT_ROOT, load_config, setup_logging
    from .drive_manager import ensure_storage_layout, get_storage_root
    from .environment_check import detect_environment
    from .image_utils import png_dimensions, png_has_transparency, prepare_product_canvas
    from .metadata_manager import build_metadata
    from .output_manager import write_output_bundle
    from .workflow_manager import WorkflowError, apply_parameters, get_workflow
except ImportError:
    from common import DEFAULT_CONFIG, PROJECT_ROOT, load_config, setup_logging
    from drive_manager import ensure_storage_layout, get_storage_root
    from environment_check import detect_environment
    from image_utils import png_dimensions, png_has_transparency, prepare_product_canvas
    from metadata_manager import build_metadata
    from output_manager import write_output_bundle
    from workflow_manager import WorkflowError, apply_parameters, get_workflow


class ComfyApiError(RuntimeError):
    pass


class ComfyClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client_id = str(uuid.uuid4())

    def _request(self, path: str, *, payload: dict[str, Any] | None = None,
                 binary: bool = False) -> Any:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if data is not None else {}
        request = urllib.request.Request(self.base_url + path, data=data, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:2000]
            raise ComfyApiError(f"ComfyUI API returned HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise ComfyApiError(f"Cannot reach ComfyUI at {self.base_url}: {error}") from error
        return body if binary else json.loads(body.decode("utf-8")) if body else {}

    def queue(self, graph: dict[str, Any]) -> str:
        response = self._request("/prompt", payload={"prompt": graph, "client_id": self.client_id})
        prompt_id = response.get("prompt_id")
        if not prompt_id:
            raise ComfyApiError(f"ComfyUI did not return a prompt_id: {response}")
        return str(prompt_id)

    def wait_for_images(self, prompt_id: str, *, poll_seconds: float = 3,
                        timeout_seconds: int = 1800) -> list[dict[str, str]]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            history = self._request("/history/" + urllib.parse.quote(prompt_id, safe=""))
            entry = history.get(prompt_id)
            if entry:
                images: list[dict[str, str]] = []
                for node_output in entry.get("outputs", {}).values():
                    for item in node_output.get("images", []):
                        images.append({key: str(item.get(key, "")) for key in ("filename", "subfolder", "type")})
                if images:
                    return images
                status = entry.get("status", {}).get("status_str", "")
                if status == "error":
                    raise ComfyApiError(f"ComfyUI generation failed for prompt {prompt_id}; check its console log.")
            time.sleep(poll_seconds)
        raise TimeoutError(f"Timed out waiting for ComfyUI prompt {prompt_id} after {timeout_seconds}s")

    def download_image(self, image_info: dict[str, str], destination: str | Path) -> Path:
        query = urllib.parse.urlencode({
            "filename": image_info["filename"],
            "subfolder": image_info.get("subfolder", ""),
            "type": image_info.get("type", "output"),
        })
        data = self._request("/view?" + query, binary=True)
        target = Path(destination)
        target.write_bytes(data)
        return target


def copy_input_to_comfy(source: str | Path, comfy_input: str | Path, target_name: str) -> Path:
    src = Path(source).expanduser()
    if not src.is_file():
        raise FileNotFoundError(f"Input image does not exist: {src}")
    target_dir = Path(comfy_input)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / Path(target_name).name
    shutil.copy2(src, target)
    return target


def load_product_style(project_root: str | Path = PROJECT_ROOT,
                       storage_root: str | Path | None = None) -> str:
    candidates = []
    if storage_root:
        candidates.append(Path(storage_root) / "prompts" / "styles" / "012s-premium-product.txt")
    candidates.append(Path(project_root) / "prompts" / "styles" / "012s-premium-product.txt")
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
    return ""


def get_comfyui_revision(comfyui_dir: str | Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(comfyui_dir), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--workflow", required=True, help="Workflow id from workflows/registry.json")
    parser.add_argument("--prompt", default=None)
    parser.add_argument("--negative-prompt", default=None)
    parser.add_argument("--input-image", help="Source image or transparent product PNG")
    parser.add_argument("--mask-image", help="Black/white mask PNG for inpaint")
    parser.add_argument("--product-name", default=None)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--guidance", type=float, default=None)
    parser.add_argument("--denoise", type=float, default=None)
    parser.add_argument("--count", type=int, default=1, choices=(1, 4, 8, 16))
    parser.add_argument("--category", choices=("draft", "selected", "final"), default="draft")
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--storage-root", "--drive-root", dest="storage_root")
    parser.add_argument("--comfyui-dir")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--no-brand-style", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    storage_root = get_storage_root(config, args.storage_root)
    ensure_storage_layout(storage_root)
    logger = setup_logging(storage_root / "logs")
    workflow_version = str(config.get("workflow_version", "1.0.0"))
    try:
        storage_registry = storage_root / "workflows" / "registry.json"
        if storage_registry.is_file():
            descriptor, base_graph = get_workflow(
                args.workflow, registry_path=storage_registry, project_root=storage_root,
            )
        else:
            descriptor, base_graph = get_workflow(args.workflow)
        if args.width < 64 or args.height < 64 or args.width % 8 or args.height % 8:
            raise WorkflowError("Width and height must be at least 64 pixels and divisible by 8")
        if args.steps is not None and args.steps < 1:
            raise WorkflowError("Steps must be a positive integer")
        if args.seed is not None and args.seed < 0:
            raise WorkflowError("Seed must be zero or a positive integer")
        if args.workflow == "batch" and args.count not in (4, 8, 16):
            raise WorkflowError("Batch workflow count must be 4, 8, or 16")
        seed_base = args.seed if args.seed is not None else secrets.randbelow(2**32)
        prompt_text = args.prompt or base_graph[descriptor["nodes"]["prompt"]["id"]]["inputs"]["text"]
        negative_text = args.negative_prompt
        if negative_text is None:
            negative_node = descriptor.get("nodes", {}).get("negative_prompt")
            negative_text = base_graph[negative_node["id"]]["inputs"][negative_node["input"]] if negative_node else ""
        if args.workflow in {"product-kv", "batch"} and not args.no_brand_style:
            style = load_product_style(PROJECT_ROOT, storage_root)
            style = style.replace(
                "Product is the clear hero.",
                "The separately composited source product is the clear hero.",
            )
            if style and style not in prompt_text:
                prompt_text = f"{prompt_text.strip()}\n\n{style}"
            prompt_text = (
                f"{prompt_text.strip()}\n\n"
                "Generate only an empty background scene for a separate product composite. "
                "Do not draw a bottle, product, package, label, logo, or text. Leave a clean hero area for the supplied product image."
            )
        elif args.workflow in {"product-kv", "batch"}:
            prompt_text = (
                f"{prompt_text.strip()}\n\n"
                "Generate only an empty background scene for a separate product composite. "
                "Do not draw a bottle, product, package, label, logo, or text. Leave a clean hero area for the supplied product image."
            )

        comfy_dir = Path(args.comfyui_dir or config.get("comfyui_dir", "/content/ComfyUI"))
        input_paths: dict[str, Path] = {}
        for input_key, kind in descriptor.get("input_files", {}).items():
            if kind == "product":
                source = args.input_image
                if not source:
                    raise WorkflowError(f"Workflow '{args.workflow}' needs --input-image")
                if args.workflow in {"product-kv", "batch"}:
                    transparency = png_has_transparency(source)
                    if transparency is False:
                        raise WorkflowError("Product Key Visual needs a transparent PNG. Put the product on a transparent canvas at the output size.")
                    if transparency is None:
                        logger.warning("Could not inspect PNG alpha; verify that the product source has transparency.")
                    copied = prepare_product_canvas(
                        source, comfy_dir / "input" / config.get("product_input_name", "012s_product.png"),
                        args.width, args.height,
                    )
                else:
                    copied = copy_input_to_comfy(source, comfy_dir / "input", config.get("product_input_name", "012s_product.png"))
                input_paths[input_key] = copied
            elif kind == "mask":
                if not args.mask_image:
                    raise WorkflowError("Inpaint workflow needs --mask-image (white = regenerate, black = keep)")
                copied = copy_input_to_comfy(args.mask_image, comfy_dir / "input", config.get("mask_input_name", "012s_mask.png"))
                input_paths[input_key] = copied
        if "input_mask" in input_paths and "input_image" in input_paths:
            image_size = png_dimensions(input_paths["input_image"])
            mask_size = png_dimensions(input_paths["input_mask"])
            if image_size and mask_size and image_size != mask_size:
                raise WorkflowError(f"Inpaint image and mask dimensions differ: {image_size} vs {mask_size}")

        api_url = args.api_url or f"http://127.0.0.1:{int(config.get('comfyui_port', 8188))}"
        client = ComfyClient(api_url)
        # /system_stats is a quick reachability check before queuing work.
        client._request("/system_stats")
        report = detect_environment(config, storage_root)
        if report.status != "READY":
            raise WorkflowError("Environment is not READY; check GPU/CUDA and the selected storage root before generation.")
        gpu_name = report.gpu_name or "Unknown / not detected"
        product_name = args.product_name or (Path(args.input_image).stem if args.input_image else "image")
        outputs: list[tuple[Path, Path]] = []
        for index in range(args.count):
            seed = (int(seed_base) + index) % (2**32)
            parameters = {
                "prompt": prompt_text,
                "negative_prompt": negative_text,
                "width": args.width,
                "height": args.height,
                "seed": seed,
                "steps": args.steps if args.steps is not None else descriptor.get("default_steps"),
                "guidance": args.guidance if args.guidance is not None else descriptor.get("default_guidance"),
                "denoise": args.denoise,
            }
            for key, image_path in input_paths.items():
                input_name = config.get("mask_input_name") if key == "input_mask" else config.get("product_input_name")
                parameters[key] = Path(input_name).name
            graph = apply_parameters(base_graph, descriptor, parameters)
            prompt_id = client.queue(graph)
            print(f"Queued {args.workflow} {index + 1}/{args.count} seed={seed} prompt_id={prompt_id}")
            images = client.wait_for_images(prompt_id, timeout_seconds=args.timeout)
            for image_info in images:
                with tempfile.TemporaryDirectory(prefix="012s-output-") as temporary:
                    temp_image = Path(temporary) / Path(image_info["filename"]).name
                    client.download_image(image_info, temp_image)
                    dimensions = png_dimensions(temp_image)
                    width, height = dimensions if dimensions else (args.width, args.height)
                    metadata = build_metadata(
                        prompt=prompt_text, negative_prompt=negative_text or "", seed=seed,
                        model=descriptor["model"], model_version=descriptor.get("model_revision", descriptor["model_filename"]),
                        workflow=args.workflow, workflow_version=workflow_version,
                        width=width, height=height,
                        steps=args.steps if args.steps is not None else descriptor.get("default_steps", 4 if "FLUX" in descriptor["model"] else 30),
                        guidance=args.guidance if args.guidance is not None else descriptor.get("default_guidance", 1.0 if "FLUX" in descriptor["model"] else 6.0),
                        sampler=descriptor.get("sampler"), scheduler=descriptor.get("scheduler"),
                        gpu=gpu_name, timezone_name=str(config.get("timezone", "Asia/Taipei")),
                        extra={
                            "comfy_prompt_id": prompt_id,
                            "comfyui_revision": get_comfyui_revision(comfy_dir),
                            "model_filename": descriptor["model_filename"],
                            "model_sha256": config.get("model_sha256", {}).get(descriptor["model_filename"]),
                            "input_files": {k: str(v.name) for k, v in input_paths.items()},
                            "source_images": {
                                key: Path(value).name
                                for key, value in (("input_image", args.input_image), ("input_mask", args.mask_image))
                                if value
                            },
                        },
                    )
                    output, sidecar = write_output_bundle(
                        temp_image, storage_root, product=product_name,
                        workflow=args.workflow, seed=seed, metadata=metadata,
                        category=args.category,
                    )
                    outputs.append((output, sidecar))
                    logger.info("Archived image and metadata: %s | %s", output, sidecar)
                    print(f"Saved: {output}\nMetadata: {sidecar}")
        print(f"Completed {len(outputs)} image(s).")
        return 0
    except Exception as error:  # noqa: BLE001
        logger.exception("Workflow execution failed")
        print(f"ERROR SUMMARY: {error}")
        print("POSSIBLE CAUSE: ComfyUI is not ready, a required model/input is missing, or a workflow node was rejected.")
        print("RECOMMENDED ACTION: Check logs/comfyui.log and logs/setup.log, verify model switches and input paths, then retry.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
