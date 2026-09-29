# Workflow guide

The workflow registry is `workflows/registry.json`. The notebook syncs JSON graphs to Drive; use `run_012s_workflow(...)` or `scripts/run_workflow.py` to submit a named graph. The runner reads the Drive copy when available, so approved edits to a workflow graph or brand prompt are used. Template sync updates unmodified managed files and keeps Drive edits. Prompt, seed, dimensions, sampler settings, workflow ID/version, model label, and detected GPU are written beside each generated image.

## Workflow IDs

| ID | Model | Inputs | Notes |
|---|---|---|---|
| `text-to-image` | FLUX.1-schnell FP8 | prompt, negative prompt, dimensions, seed, steps | Schnell is guidance-distilled; the graph uses 4 steps and CFG 1.0. Negative prompt is retained as metadata, but the FLUX graph does not apply it. |
| `product-kv` | FLUX.1-schnell FP8 | transparent product PNG, scene prompt, dimensions, seed | Generates a background, then composites the source product pixels over it. |
| `img2img` | FLUX.1-schnell FP8 | source image, prompt, seed, denoise | Source image dimensions are retained; adjust denoise in the API graph for a stronger/weaker change. |
| `inpaint` | SDXL base | source image, black/white mask, prompt, seed | White mask is regenerated. Enable/install SDXL first. |
| `outpaint` | SDXL base | source image, prompt, seed | Default extends 256 px on left and right. Change `ImagePadForOutpaint` values in the graph for other margins. |
| `batch` | FLUX.1-schnell FP8 | transparent product PNG, prompt, 4/8/16 count, starting seed | Submits one image per seed so filenames and sidecars record each seed separately. |

The official Colab presets in `config/resolution_presets.json` are square 1024×1024, Instagram portrait 1024×1280, vertical advertising 1024×1536, landscape banner 1536×1024, and wide banner 1536×768. Width and height are runner parameters, so these values are defaults rather than hard-coded workflow limits.

## CLI examples

```bash
python scripts/run_workflow.py --workflow text-to-image --prompt "A premium apothecary bottle on pale stone" --seed 12345 --width 1024 --height 1280
python scripts/run_workflow.py --workflow product-kv --input-image /content/drive/MyDrive/012s-image-system/assets/products/product.png --product-name NNE --prompt "Bright studio, pale limestone plinth, soft side light" --seed 12345
python scripts/run_workflow.py --workflow batch --input-image /content/drive/MyDrive/012s-image-system/assets/products/product.png --product-name NNE --prompt "Clean premium studio with open negative space" --count 8 --seed 1000
python scripts/run_workflow.py --workflow inpaint --input-image /content/drive/MyDrive/012s-image-system/assets/reference/source.png --mask-image /content/drive/MyDrive/012s-image-system/assets/reference/mask.png --prompt "Continue the pale stone background" --seed 12345
```

## Output files

Output images are saved to `outputs/draft/` by default. `--category selected` and `--category final` change the destination. A fixed seed produces repeatable input noise while the same model revision, workflow graph, dimensions, and runtime settings are retained. Different ComfyUI/PyTorch versions can still lead to small numerical changes; the metadata records the model/workflow values but not an immutable ComfyUI commit hash yet.
