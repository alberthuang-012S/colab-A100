# Model guide

## Phase 1 model set

| Model | Switch | Drive folder | Use |
|---|---|---|---|
| FLUX.1-schnell FP8 checkpoint | `install_flux` (default `true`) | `models/flux/` | Text-to-image, product backgrounds, image-to-image, batch variations |
| Stable Diffusion XL 1.0 base | `install_sdxl` (default `false`) | `models/sdxl/` | Inpaint and outpaint starter graphs |

Only selected categories download. On Colab, a valid existing file is skipped. An interrupted `.part` file resumes with HTTP Range when the host supports it. A configured SHA-256 can be added under `model_sha256`; no checksum is invented when one is not published in this repository.

FLUX uses the Comfy-Org single-file Schnell FP8 checkpoint referenced by the official ComfyUI template. It is pinned at 17.2 GB with a SHA-256 check, keeping the first install to one checkpoint and giving ComfyUI a normal checkpoint loader graph. SDXL base is pinned at 6.94 GB. These published sizes and hashes are recorded from the [Comfy-Org FLUX file](https://huggingface.co/Comfy-Org/flux1-schnell/blob/0cb207e7e753453ef479ae266caf7c1ab364e363/flux1-schnell-fp8.safetensors) and [Stability AI SDXL file](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/ce8cd4d6569112b0c0ad48cdd18560fe0bcc7a48/sd_xl_base_1.0.safetensors). The FLUX checkpoint is quantized; its quality and throughput have not been measured on this A100 runtime.

The SDXL URL points to the Stability AI SDXL base repository. Access may require accepting its license terms and a Hugging Face token. Phase 1 does not download an SDXL inpainting-specific checkpoint, so the inpaint graph uses SDXL base with ComfyUI's mask-aware conditioning; it is a starter workflow, not a claim of parity with a specialized inpainting model.

## Authentication

Set a Colab Secret called `HF_TOKEN`, or set `HF_TOKEN` / `HUGGING_FACE_HUB_TOKEN` in the process environment. Do not paste tokens into config, notebook source, or Git. A 401/403 is reported as **AUTH REQUIRED** with the next step. The rest of the notebook can finish starting ComfyUI.

## Model paths

Drive model folders are exposed using `ComfyUI/extra_model_paths.yaml`. Flux and SDXL checkpoints are searched under their respective Drive folders; LoRA, ControlNet, and VAE folders are registered for future use. No LoRA or ControlNet weights are installed in Phase 1.

## Space and restart behavior

The first FLUX download can take many gigabytes. It is kept in Drive across Colab runtime restarts. The runtime checkout and Python packages are recreated when a runtime is deleted. Check Drive free space before enabling another model category.
