# Colab Deployment Checklist — Phase 1

This checklist prepares the existing Phase 1 launcher for a clean Google Colab runtime. It does not add or install Phase 2 features.

## Readiness snapshot

- [x] Notebook, scripts, config, prompts, workflows, docs, and the local offline test suite are included in the initial Git commit.
- [x] Large model files, generated outputs, user assets, credentials, logs, and runtime caches are excluded by `.gitignore`.
- [x] The notebook uses Colab runtime paths under `/content` and persistent files under `/content/drive/MyDrive/012s-image-system`.
- [ ] Publish this commit to a GitHub repository and configure its URL in Colab on the first launch.
- [ ] Run the notebook in a real fresh Colab GPU runtime. This has not been done from this local environment.

## GitHub setup required

1. Create an empty GitHub repository under the appropriate personal or organization owner. Recommended name: `012s-image-system`.
2. Choose public or private visibility according to the owner's policy. Do not initialize it with a README, license, or `.gitignore`; this local repository already contains those files.
3. Copy the repository's HTTPS or SSH clone URL. Add it as `origin` locally and push the `master` branch containing the initial commit. Do not put access tokens or passwords in the URL.
4. Open `012S_Image_System.ipynb` from that repository in Google Colab. The notebook asks for the repository URL once on a new Drive, saves the non-secret URL under Drive metadata, and clones the project into `/content/012s-image-system`.

No GitHub remote is configured in this checkout, so the owner and repository URL must be supplied by the project owner after the repository is created or selected.

## Fresh Colab runtime launch

1. Select a GPU runtime in **Runtime → Change runtime type**. A100 is recommended when available.
2. Open the committed `012S_Image_System.ipynb` in Colab and run its cells from top to bottom.
3. **Step 1 — Mount Drive and fetch the launcher:** approve Google Drive access. On the first launch, paste the GitHub clone URL when prompted. The notebook mounts Drive at `/content/drive`, then clones the repository to `/content/012s-image-system`. This order lets it save and reuse the repository URL in Drive on later launches.
4. **Step 2 — Environment check:** confirm the report says `READY` and shows a CUDA-capable GPU and mounted Drive. Stop if it reports `WARNING`.
5. **Steps 3–4 — Install/update ComfyUI:** clone ComfyUI into `/content/ComfyUI` on a new runtime, fast-forward an existing checkout, install its current requirements, and check the environment again.
6. **Steps 5–6 — Set up models:** inspect the selected model list, then download only missing/invalid selected models. FLUX is enabled by default and SDXL is disabled. If Hugging Face requests authentication, add `HF_TOKEN` using Colab Secrets and accept any required model terms.
7. **Steps 7–8 — Configure model paths:** write ComfyUI's extra model path config to read models from Drive and prepare the custom-node folder. Included Phase 1 workflows require no third-party custom nodes.
8. **Step 9 — Sync workflows:** copy workflow JSON and prompt templates to the corresponding Drive folders. Existing Drive customizations are preserved.
9. **Steps 10–11 — Launch ComfyUI:** start the server on port 8188, wait for its API health endpoint, then open the Colab proxy link shown by the notebook.
10. Optionally call `run_012s_workflow(...)` from the final notebook cell to submit one of the Phase 1 workflows.

## Path and repository hygiene

- Notebook runtime paths: `/content/012s-image-system` and `/content/ComfyUI`.
- Persistent storage: `/content/drive/MyDrive/012s-image-system`.
- The notebook was scanned for Windows absolute paths such as `C:\Users\...`; none were found.
- `.gitignore` excludes model weight extensions, `models/`, `outputs/`, all local `assets/`, token/secret files, credentials, logs, notebook checkpoints, and Python caches.
- The `HF_TOKEN` is read from Colab Secrets at runtime. It is not included in the notebook or config.

## Risks before first Colab run

- The GitHub repository must exist and contain this commit before Colab can clone it. Its URL and access policy are not known in this checkout.
- The notebook has not been executed in Colab. GPU availability, Drive authorization, current ComfyUI dependency compatibility, and the Colab proxy link remain unverified.
- The default FLUX checkpoint is about 17.2 GB (decimal) and is stored in Drive. Confirm available Drive quota before downloading; the first download may take significant time. SDXL is off by default.
- ComfyUI is fast-forwarded from its upstream default branch and its requirements are installed at launch time. Upstream changes can affect first-run behavior.
- Private GitHub repositories need working Git authentication in the Colab runtime. Never paste a credential-bearing clone URL; use an approved authentication method.
