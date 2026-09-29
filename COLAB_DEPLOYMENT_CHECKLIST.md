# Colab Deployment Checklist — Phase 1

This checklist prepares the existing Phase 1 launcher for a clean Google Colab runtime. It does not add or install Phase 2 features.

## Readiness snapshot

- [x] Notebook, scripts, config, prompts, workflows, docs, and the local offline test suite are included in the initial Git commit.
- [x] Large model files, generated outputs, user assets, credentials, logs, and runtime caches are excluded by `.gitignore`.
- [x] The notebook keeps the GitHub checkout at `/content/012s-image-system` and supports shared Drive or ephemeral storage roots.
- [x] Publish the initial commit to GitHub and configure the repository as `origin`.
- [x] Complete the Phase 1A.1 T4 pipeline smoke run with SDXL, PNG, and metadata. A T4 checks the pipeline only; it is not FLUX-on-A100 verification.
- [ ] Verify that the Colab browser proxy opens from an authorized browser session. The local ComfyUI API worked; Chrome blocked/denied the external proxy URL in this run.
- [ ] Repeat FLUX generation on a real A100 runtime before claiming FLUX-on-A100 verification.

## GitHub repository

- [x] Repository: [alberthuang-012S/colab-A100](https://github.com/alberthuang-012S/colab-A100), with `master` tracking `origin/master`.
- [x] Initial commit `82e6ff8` pushed successfully.
- [x] Open `012S_Image_System.ipynb` in Google Colab and run the T4 ephemeral/SDXL smoke test.

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
- T4 pipeline smoke passed through the local ComfyUI API and generated PNG plus JSON metadata. The external proxy link was issued, but Chrome reported `ERR_BLOCKED_BY_CLIENT` on the notebook link and HTTP 403 in a separately opened tab. The browser proxy is not verified in this browser session.
- The default FLUX checkpoint is about 17.2 GB (decimal), remains the formal main model, and is enabled by default. The optional SDXL workflow is only for the T4 pipeline smoke test; it does not change the default model.
- ComfyUI is fast-forwarded from its upstream default branch and its requirements are installed at launch time. Upstream changes can affect first-run behavior.
- Private GitHub repositories need working Git authentication in the Colab runtime. Never paste a credential-bearing clone URL; use an approved authentication method.

## Phase 1A.1 — T4 runtime verification (2026-09-29)

- **Runtime:** Colab Python 3.13.15; PyTorch 2.11.0+cu128; torch CUDA 12.8; Tesla T4, 14.56 GiB VRAM. The environment report was `READY`.
- **Storage:** ephemeral mode at `/content/012s-runtime`; Drive displayed `NOT REQUIRED` and was not mounted. The earlier Drive mount issue was `credential propagation was unsuccessful`; no OAuth bypass or credential storage was used.
- **ComfyUI:** cloned from upstream at revision `a7169322485d0049380fb207fa17e9fb3ec40486`; requirements installed; local `/system_stats` API responded on port 8188. The Colab proxy URL was returned, but opening it from Chrome was blocked/denied (`ERR_BLOCKED_BY_CLIENT` / HTTP 403).
- **SDXL:** `sd_xl_base_1.0.safetensors` downloaded to the ephemeral model folder; 6,938,078,334 bytes; the downloader validated the configured SHA-256 `31e35c80fc4829d14f90153f4c74cd59c90b779f6afe05a74cd6120b893f7e5b`.
- **Generation:** `text-to-image-sdxl`, 1024×1024, batch 1, seed `20260929`, 12 steps, guidance 6.0. The call took 50.8 seconds including checkpoint load and generation; observed peak GPU memory was 10.38 GiB. ComfyUI did not emit a separately parseable checkpoint-load duration in its log.
- **Output:** `/content/012s-runtime/outputs/draft/image_text-to-image-sdxl_20260929_seed20260929.png` (880,105 bytes) and same-name `.json` sidecar. Metadata records the exact prompt, seed, SDXL model/revision and SHA, workflow/version, dimensions, steps, guidance, GPU, and timestamp.
- **FLUX/A100:** FLUX was disabled for the T4 smoke run because 14.56 GiB is below the 20 GiB gate. No FLUX-on-A100 generation was attempted; it remains unverified.
- **Storage lifetime:** the output and model are in ephemeral runtime storage and disappear when that runtime ends.
