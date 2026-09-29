# Troubleshooting

## Environment status is WARNING

- **GPU not detected:** select a Colab GPU runtime and rerun the environment cell. The launcher stops before downloading models.
- **GPU detected but PyTorch CUDA is unavailable:** restart the runtime after selecting GPU. Check the PyTorch version and CUDA entry in the Environment Report.
- **Drive not connected:** rerun the Drive mount cell and approve access. Confirm that `MyDrive/012s-image-system/` is reachable.

## Model reports AUTH REQUIRED

Accept any model terms on its Hugging Face page and add a Colab Secret named `HF_TOKEN`. Rerun the model installation cell. The token is not written to Drive or Git.

## Checkpoint is missing in ComfyUI

Confirm the selected model switch is enabled, the download completed, and the file is in `models/flux/` or `models/sdxl/`. Rerun the Drive model path cell, then restart ComfyUI so it rescans `extra_model_paths.yaml`.

## Product workflow rejects an image

Use PNG with transparency. The runner centers smaller artwork without resizing; oversized artwork must be uniformly resized by the user or placed on a matching transparent canvas. A full-size canvas gives precise product placement. Product and output dimensions must match.

## Inpaint output is unchanged or changes the wrong place

The SDXL base checkpoint must be installed. Verify that the mask is the same size as the input and that white is the region to regenerate. The starter graph does not install a specialized SDXL inpainting checkpoint.

## ComfyUI does not start or the link fails

Read `logs/comfyui.log` and `logs/setup.log`. The notebook waits for ComfyUI's `/system_stats` endpoint before displaying a link. If the server exited, rerun the start cell after resolving the first reported Python or dependency error.

## Out of Drive space or interrupted download

Check Google Drive quota. Partial downloads remain as `.part` files and can resume on a later model sync. A file that fails size/hash validation is quarantined with an `.invalid-<timestamp>` suffix rather than silently treated as valid.

## Memory errors

Reduce output dimensions or batch count. The batch runner submits one image at a time; it does not place 16 images in GPU memory simultaneously. A100 Colab availability and memory size vary by account/session and have not been verified by this repository's tests.
