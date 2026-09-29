# Colab setup

## Before starting

The notebook assumes a Google Colab GPU runtime. Select A100 when available. `storage_mode` defaults to `drive`; SDXL is optional and FLUX.1-schnell is enabled in the checked-in configuration. Models are large, so allow time for selected model downloads.

## Launch steps

1. Open `012S_Image_System.ipynb` in Colab and choose **Runtime → Change runtime type → GPU**.
2. Run cells from the top. Step 1 clones/updates the project in `/content/012s-image-system` before setting up storage.
3. The default `drive` mode mounts Drive and uses `/content/drive/MyDrive/012s-image-system`. Set `STORAGE_MODE_OVERRIDE = 'ephemeral'` in Step 1 for `/content/012s-runtime`; this skips Drive mount entirely. To use a fork, set `012S_REPOSITORY_URL` before running Step 1. Never put credentials in the URL.
4. Read the Environment Report. It shows GPU, CUDA, PyTorch, Storage Mode, Storage Root, and Drive. Drive is `NOT REQUIRED` in ephemeral mode. `READY` requires a CUDA-capable GPU and a usable storage root.
5. ComfyUI is cloned on a fresh runtime or fast-forwarded when its checkout exists. Dependencies are installed for that runtime.
6. Review model switches in `config/system_config.json`. The model check prints whether each selected checkpoint is already present. The next cell downloads only missing/invalid selected files.
7. Public model downloads may need no token. If authentication is required, accept the model terms and configure `HF_TOKEN` explicitly; the notebook does not read Colab Secrets automatically.
8. The remaining cells configure model paths from the selected storage root, sync workflows, start ComfyUI, and display its proxy URL.

For a T4 pipeline smoke test, use Step 1 overrides `STORAGE_MODE_OVERRIDE = 'ephemeral'`, `INSTALL_FLUX_OVERRIDE = False`, and `INSTALL_SDXL_OVERRIDE = True`; then run the `text-to-image-sdxl` workflow at 1024×1024. This is not FLUX-on-A100 verification.

## Restarting a runtime

In Drive mode, rerun the notebook to reuse persistent model files and outputs. Ephemeral files are deleted when the runtime ends.

## Stop the runtime

Use **Runtime → Disconnect and delete runtime** after work. This stops the ComfyUI process and frees the GPU. Files already written to Drive remain available.

## Logs

- `logs/setup.log`: environment/setup, model checks, downloads, failures, and launch.
- `logs/comfyui.log`: ComfyUI server output.

For workflow requests, errors are printed as an error summary, possible cause, and recommended action. The complete Python details are also in the logs.
