# Architecture

## Components

- `012S_Image_System.ipynb` is the Colab launcher. It mounts Drive, checks hardware, calls the setup modules in order, starts ComfyUI, and exposes the Colab proxy URL.
- `scripts/environment_check.py` reports Python, PyTorch, CUDA, GPU model, VRAM, and Drive state. Its status is `READY` only when CUDA is usable and Drive is mounted.
- `scripts/drive_manager.py` creates the project folder layout and writes ComfyUI's additional model search paths.
- `scripts/model_manager.py` checks selected files, skips valid files, resumes interrupted downloads, validates minimum size and optional SHA-256, and reports authentication failures.
- `scripts/comfy_manager.py` clones or fast-forwards ComfyUI, installs its requirements, and starts the server.
- `scripts/workflow_manager.py` validates the workflow registry, prepares API graphs, and syncs graph/prompt files to Drive.
- `scripts/run_workflow.py` submits a graph to ComfyUI's HTTP API, downloads generated PNGs, and archives each PNG with metadata.
- `scripts/output_manager.py` creates collision-safe output names and JSON sidecars.

## Persistent data and runtime data

Drive stores model files, assets, prompts, workflows, outputs, logs, and sidecars. The Colab runtime stores the ComfyUI checkout, Python dependencies, and temporary input/output files. On a fresh runtime, setup updates ComfyUI and points it at the existing Drive model folders instead of downloading valid models again.

ComfyUI discovers Drive models through `ComfyUI/extra_model_paths.yaml`; model files do not need to be copied to the runtime. Category switches live in `config/system_config.json` (`install_flux`, `install_sdxl`). FLUX is selected by default and SDXL is opt-in.

## Workflow execution

Workflow definitions are ComfyUI API-format JSON graphs. The registry in `workflows/registry.json` maps friendly IDs and parameter names to graph nodes. The runner submits them to the same ComfyUI server used by the web UI. This keeps the front end stock while making the 012S flows repeatable and scriptable.

The graphs use ComfyUI core nodes. The initial FLUX graph follows Comfy-Org's Schnell single-checkpoint workflow pattern; ComfyUI's official workflow templates and built-in node documentation are useful references: [FLUX.1-schnell template](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/flux_schnell.json), [ComfyUI workflow templates](https://github.com/Comfy-Org/workflow_templates), [DualCLIPLoader docs](https://docs.comfy.org/built-in-nodes/DualCLIPLoader).

## Versioning and future video support

Project and workflow versions are in `config/system_config.json`. Each image sidecar records the workflow version used. Video support is intentionally absent from Phase 1; future Wan or LTX-Video flows can be added as a separate registry category and runtime dependency set without changing the image workflow runner's metadata contract.

## Next phase candidates

ControlNet, reference consistency, automatic background generation, LoRA support, upscaling, and image-to-video workflows are candidates for Phase 2. They are not included in this release.
