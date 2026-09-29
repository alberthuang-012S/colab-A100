# Colab Deployment Checklist — Phase 1

This checklist prepares the existing Phase 1 launcher for a clean Google Colab runtime. It does not add or install Phase 2 features.

## Readiness snapshot

- [x] Notebook, scripts, config, prompts, workflows, docs, and the local offline test suite are included in the initial Git commit.
- [x] Large model files, generated outputs, user assets, credentials, logs, and runtime caches are excluded by `.gitignore`.
- [x] The notebook keeps the GitHub checkout at `/content/012s-image-system` and supports shared Drive or ephemeral storage roots.
- [x] Publish the initial commit to GitHub and configure the repository as `origin`.
- [ ] Complete the Phase 1A.1 T4 pipeline smoke run. A T4 checks the pipeline only; it is not FLUX-on-A100 verification.
- [ ] Repeat FLUX generation on a real A100 runtime before claiming FLUX-on-A100 verification.

## GitHub repository

- [x] Repository: [alberthuang-012S/colab-A100](https://github.com/alberthuang-012S/colab-A100), with `master` tracking `origin/master`.
- [x] Initial commit `82e6ff8` pushed successfully.
- [ ] Open `012S_Image_System.ipynb` in Google Colab and run it in a fresh GPU runtime.

## Colab runtime launch

1. Select a GPU runtime in **Runtime → Change runtime type**. A100 is recommended when available.
2. Open the committed `012S_Image_System.ipynb` in Colab and run its cells from top to bottom.
3. **Step 1 — Fetch the launcher and choose storage:** the notebook clones or updates `https://github.com/alberthuang-012S/colab-A100.git` at `/content/012s-image-system` first. `drive` is the default and mounts Drive; `ephemeral` skips Drive entirely and uses `/content/012s-runtime`. Set `012S_REPOSITORY_URL` before this cell if using a fork.
4. **Step 2 — Environment check:** confirm the report says `READY` and shows a CUDA-capable GPU and usable storage root. In ephemeral mode, Drive is `NOT REQUIRED`.
5. **Steps 3–4 — Install/update ComfyUI:** clone ComfyUI into `/content/ComfyUI` on a new runtime, fast-forward an existing checkout, install its current requirements, and check the environment again.
6. **Steps 5–6 — Set up models:** inspect the selected model list, then download only missing/invalid selected models. FLUX is enabled by default and SDXL is disabled. If Hugging Face requests authentication, add `HF_TOKEN` using Colab Secrets and accept any required model terms.
7. **Steps 7–8 — Configure model paths:** write ComfyUI's extra model path config to read models from the selected storage root and prepare the custom-node folder. Included Phase 1 workflows require no third-party custom nodes.
8. **Step 9 — Sync workflows:** copy workflow JSON and prompt templates to the selected storage folders. Existing customizations are preserved.
9. **Steps 10–11 — Launch ComfyUI:** start the server on port 8188, wait for its API health endpoint, then open the Colab proxy link shown by the notebook.
10. Optionally call `run_012s_workflow(...)` from the final notebook cell to submit one of the Phase 1 workflows.

For the Phase 1A.1 T4 smoke test, set Step 1 overrides to ephemeral storage, FLUX off, and SDXL on. Generate one 1024×1024 `text-to-image-sdxl` image. A passing run verifies the pipeline only; FLUX-on-A100 remains unverified until it succeeds on an A100.

## Path and repository hygiene

- Notebook runtime paths: `/content/012s-image-system` and `/content/ComfyUI`.
- Persistent storage (`drive`): `/content/drive/MyDrive/012s-image-system`.
- Runtime-only storage (`ephemeral`): `/content/012s-runtime`; its contents disappear when the runtime ends.
- The notebook was scanned for Windows absolute paths such as `C:\Users\...`; none were found.
- `.gitignore` excludes model weight extensions, `models/`, `outputs/`, all local `assets/`, token/secret files, credentials, logs, notebook checkpoints, and Python caches.
- The notebook does not read Colab Secrets automatically. Configure `HF_TOKEN` explicitly only when the model host requires it.

## Risks before first Colab run

- The first Colab session used a Tesla T4; A100 was unavailable. Drive mount failed with `credential propagation was unsuccessful`. Use ephemeral mode to continue the pipeline smoke test.
- ComfyUI, SDXL generation, and the Colab proxy still need a successful smoke run before `PIPELINE VERIFIED` can be claimed.
- The default FLUX checkpoint is about 17.2 GB (decimal), remains the formal main model, and is enabled by default. The optional SDXL workflow is only for the T4 pipeline smoke test; it does not change the default model.
- ComfyUI is fast-forwarded from its upstream default branch and its requirements are installed at launch time. Upstream changes can affect first-run behavior.
- Private GitHub repositories need working Git authentication in the Colab runtime. Never paste a credential-bearing clone URL; use an approved authentication method.
