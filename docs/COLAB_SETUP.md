# Colab setup

## Before starting

The notebook assumes a Google Colab GPU runtime and a Google account with Drive access. Select A100 when available. FLUX.1-schnell is enabled in the checked-in configuration; SDXL is optional. Models are large, so allow time for the initial selected model download and keep enough Drive quota free.

## Launch steps

1. Open `012S_Image_System.ipynb` in Colab and choose **Runtime → Change runtime type → GPU**.
2. Run cells from the top. The first cell mounts Drive, creates the 012S Drive layout, and checks whether project scripts are already present.
3. If scripts are absent, provide the repository URL once. It is saved without credentials in the Drive metadata folder, so a fresh runtime can clone again without another prompt. This repository was not given a Git remote in the initial checkout. For private source repositories, use your existing Git credentials or a repository access method approved by your organization.
4. Read the Environment Report. If status is not `READY`, stop and select a GPU runtime or reconnect Drive before continuing.
5. ComfyUI is cloned on a fresh runtime or fast-forwarded when its checkout exists. Dependencies are installed for that runtime.
6. Review model switches in `config/system_config.json`. The model check prints whether each selected checkpoint is already present. The next cell downloads only missing/invalid selected files.
7. For Hugging Face authentication, add a Colab Secret named `HF_TOKEN`. The notebook exposes it to the downloader without printing or saving the token. A public model usually needs no token; gated access may also require accepting the model terms in Hugging Face first.
8. The remaining cells configure Drive model paths, sync workflows, start ComfyUI, and display its proxy URL.

## Restarting a runtime

Mount Drive and rerun the notebook. The Drive folders and valid model files are kept. ComfyUI and its dependencies are prepared on the new runtime; model downloads are skipped when files pass validation.

## Stop the runtime

Use **Runtime → Disconnect and delete runtime** after work. This stops the ComfyUI process and frees the GPU. Files already written to Drive remain available.

## Logs

- `logs/setup.log`: environment/setup, model checks, downloads, failures, and launch.
- `logs/comfyui.log`: ComfyUI server output.

For workflow requests, errors are printed as an error summary, possible cause, and recommended action. The complete Python details are also in the logs.
