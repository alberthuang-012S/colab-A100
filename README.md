# 012S AI Image Generation System v1

A modular Google Colab launcher for ComfyUI, designed around an NVIDIA A100 runtime. The default `drive` storage mode keeps model weights, workflows, prompts, generated images, and metadata in Google Drive. The optional `ephemeral` mode uses `/content/012s-runtime` for Drive-free runtime smoke tests; its files are deleted when the Colab runtime ends.

## What is included

- FLUX.1-schnell text-to-image, product key visual compositing, image-to-image, and seeded product batches.
- SDXL inpaint and outpaint workflow graphs, with SDXL installation disabled by default, plus a text-to-image runtime smoke workflow.
- One shared storage root for Drive and ephemeral runtime data; `storage_mode` defaults to `drive`.
- Model discovery through ComfyUI's `extra_model_paths.yaml` in either storage mode.
- PNG output plus a JSON sidecar with prompt, seed, model, workflow, settings, date, and detected GPU.
- An environment report and persistent setup/ComfyUI logs.
- No video generation in Phase 1. The workflow registry leaves room for a later video workflow family.

## Start in Colab

1. Publish or clone this repository, then open [012S_Image_System.ipynb](012S_Image_System.ipynb) in Google Colab.
2. In **Runtime → Change runtime type**, select a GPU runtime. Choose A100 when Colab offers it.
3. Run the notebook from the top. Step 1 clones or updates the project at `/content/012s-image-system` before preparing storage. To use a fork, set `012S_REPOSITORY_URL` before running that cell. Do not put credentials in the URL.
4. `storage_mode` defaults to `drive`, which mounts `/content/drive` and uses `/content/drive/MyDrive/012s-image-system`. If Drive authorization is unavailable, set `STORAGE_MODE_OVERRIDE = 'ephemeral'` in Step 1. Drive is not mounted in ephemeral mode.
5. The environment check stops before model downloads if CUDA GPU support or the selected storage root is unavailable. Drive is shown as `NOT REQUIRED` in ephemeral mode.
6. The notebook installs only selected model categories: FLUX is on by default; SDXL is off. Existing valid files are skipped.
7. Open the ComfyUI link shown by the final setup cell. To generate with a managed workflow, call `run_012s_workflow(...)` in the notebook.

The notebook uses the standard ComfyUI web UI. The checked-in workflow JSON files are ComfyUI API graphs run by the small `scripts/run_workflow.py` helper; they are not custom front-end screens.

For a T4 pipeline smoke test, set `STORAGE_MODE_OVERRIDE = 'ephemeral'`, `INSTALL_FLUX_OVERRIDE = False`, and `INSTALL_SDXL_OVERRIDE = True` in Step 1. Then run `text-to-image-sdxl` at 1024×1024. This checks the pipeline only; it does not verify FLUX on A100. Keep checked-in defaults unchanged after the test.

## Run a workflow

The notebook defines a helper, or use the CLI in a Colab cell:

```python
run_012s_workflow(
    "text-to-image",
    "Premium apothecary bottle on pale limestone, soft studio light",
    seed=12345,
    width=1024,
    height=1024,
)
```

For product key visuals, upload a transparent PNG into `MyDrive/012s-image-system/assets/products/` using Google Drive, then pass its path:

```python
run_012s_workflow(
    "product-kv",
    "Bright clean studio with a pale stone plinth and soft side lighting",
    input_image="/content/drive/MyDrive/012s-image-system/assets/products/product.png",
    product_name="NNE",
    seed=12345,
)
```

Batch variation accepts `count=4`, `8`, or `16`. A fixed starting seed produces consecutive, repeatable seeds. Inpaint uses an image and mask; white mask pixels are regenerated. See [Workflow Guide](docs/WORKFLOW_GUIDE.md) for all IDs and inputs.

## Where files go

```text
MyDrive/012s-image-system/  # storage_mode=drive (default)
├── models/       # persistent model weights; excluded from Git
├── workflows/    # synced workflow API graphs
├── assets/       # product, packaging, reference, and brand images
├── prompts/      # prompt templates
├── outputs/
│   ├── draft/
│   ├── selected/
│   └── final/
├── metadata/     # runtime state and future indexes
└── logs/
    ├── setup.log
    └── comfyui.log
```

Each generated PNG has a same-name `.json` sidecar in its output folder. Names follow `product_workflow_YYYYMMDD_seedNNNNN.png`.

In ephemeral mode the same folder layout is rooted at `/content/012s-runtime/`. The notebook shows the output path and PNG preview after a successful run and includes `download_latest_output()` for an optional browser download.

## Models and access

FLUX.1-schnell FP8 is the default single-file checkpoint. SDXL base is optional. Model downloads are not part of unit tests. If a model host returns 401/403, the notebook prints **AUTH REQUIRED**; accept any required model terms and configure `HF_TOKEN` explicitly before retrying. The notebook does not read Colab Secrets automatically, and tokens are never stored in this repository.

## Shut down

When finished, stop the Colab runtime with **Runtime → Disconnect and delete runtime** (or **Disconnect runtime**). Drive files persist. Ephemeral files, the ComfyUI process, and runtime dependencies are temporary.

## Guides

- [Architecture](docs/ARCHITECTURE.md)
- [Colab setup](docs/COLAB_SETUP.md)
- [Colab deployment checklist](COLAB_DEPLOYMENT_CHECKLIST.md)
- [Model guide](docs/MODEL_GUIDE.md)
- [Workflow guide](docs/WORKFLOW_GUIDE.md)
- [Product image guide](docs/PRODUCT_IMAGE_GUIDE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## Developer checks

Run the lightweight offline suite from the repository root:

```bash
python -m unittest discover -v
```

The tests do not download models or contact Google Drive, Hugging Face, or ComfyUI.
