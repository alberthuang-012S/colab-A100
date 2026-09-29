# 012S AI Image Generation System v1

A modular Google Colab launcher for ComfyUI, designed around an NVIDIA A100 runtime. The system keeps model weights, workflows, prompts, generated images, and metadata on Google Drive so a restarted Colab runtime can reuse them.

## What is included

- FLUX.1-schnell text-to-image, product key visual compositing, image-to-image, and seeded product batches.
- SDXL inpaint and outpaint workflow graphs, with SDXL installation disabled by default.
- Drive-backed model storage and model discovery through ComfyUI's `extra_model_paths.yaml`.
- PNG output plus a JSON sidecar with prompt, seed, model, workflow, settings, date, and detected GPU.
- An environment report and persistent setup/ComfyUI logs.
- No video generation in Phase 1. The workflow registry leaves room for a later video workflow family.

## Start in Colab

1. Publish or clone this repository, then open [012S_Image_System.ipynb](012S_Image_System.ipynb) in Google Colab.
2. In **Runtime → Change runtime type**, select a GPU runtime. Choose A100 when Colab offers it.
3. Run the notebook from the top. The first cell mounts Drive and fetches the project scripts. Because this checkout has no Git remote configured yet, paste the repository URL once when prompted; it is saved as a non-secret URL in Drive for later runtime restarts. Do not include credentials in that URL.
4. The environment check stops before model downloads if CUDA GPU support or Drive is unavailable.
5. The notebook installs only the model categories selected in `config/system_config.json`: FLUX is on by default; SDXL is off. Existing valid files are skipped. Missing model files are stored under `MyDrive/012s-image-system/models/`.
6. Open the ComfyUI link shown by the final setup cell. To generate with one of the managed workflows, call `run_012s_workflow(...)` in the notebook. Examples are included beside the helper function.

The notebook uses the standard ComfyUI web UI. The checked-in workflow JSON files are ComfyUI API graphs run by the small `scripts/run_workflow.py` helper; they are not custom front-end screens.

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
MyDrive/012s-image-system/
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

## Models and access

FLUX.1-schnell FP8 is the default single-file checkpoint. SDXL base is optional and supports the Phase 1 inpaint/outpaint examples. Model downloads are not part of tests. If a model host returns 401/403, the notebook prints **AUTH REQUIRED** and continues setup; add a `HF_TOKEN` Colab Secret, accept any required model terms, then rerun the model cell. Tokens are read from `HF_TOKEN` or `HUGGING_FACE_HUB_TOKEN` and are never stored in this repository.

## Shut down

When finished, stop the Colab runtime with **Runtime → Disconnect and delete runtime** (or **Disconnect runtime**). Generated files and downloaded models remain on Drive. The Colab runtime disk and ComfyUI process are temporary.

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
