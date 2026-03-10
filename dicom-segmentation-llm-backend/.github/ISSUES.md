# GitHub Issues — Sprint Backlog

Create these issues in `gerinsights/dicom-segmentation-llm-backend` to track progress.

---

## Issue 1: M1 — Implement nnU-Net inference runner
**Labels:** `enhancement`, `M1`

### Description
Implement the `NNUNetRunner` class in `src/inference/nnunet_runner.py`.

### Tasks
- [ ] Load nnUNet v2 model from `plans.json` + checkpoint files
- [ ] Implement `predict()` method accepting numpy volume + spacing
- [ ] Handle multi-fold ensemble (fold_0, fold_1, etc.)
- [ ] GPU-agnostic execution via PyTorch (ROCm/CUDA/CPU)
- [ ] Return probability maps per label class
- [ ] Add sliding window inference for large volumes
- [ ] Add unit tests with mock model

---

## Issue 2: M1 — Implement MONAI inference runner
**Labels:** `enhancement`, `M1`

### Description
Implement the `MONAIRunner` class in `src/inference/monai_runner.py`.

### Tasks
- [ ] Load MONAI model from config + weights file
- [ ] Implement `predict()` with sliding window inferer
- [ ] Support DynUNet, SegResNet, SwinUNETR architectures
- [ ] GPU-agnostic execution
- [ ] Add unit tests

---

## Issue 3: M1 — Wire CTA pipeline end-to-end
**Labels:** `enhancement`, `M1`

### Description
Connect the CTA pipeline stages: converter → preprocess → inference → postprocess → output → sender.

### Tasks
- [ ] Update `CTAPipeline.run()` to call `dicom_to_volume()`
- [ ] Apply `resample_isotropic()`, `clip_hu()`, `normalize_intensity()`
- [ ] Call inference runner (nnUNet or MONAI)
- [ ] Apply `threshold_mask()`, `connected_components()`, `label_anatomical_regions()`
- [ ] Generate RTSTRUCT + Secondary Capture + DICOM SEG
- [ ] C-STORE results back to PACS
- [ ] Integration test with synthetic DICOM data

---

## Issue 4: M1 — Wire MRI pipeline end-to-end
**Labels:** `enhancement`, `M1`

### Description
Connect the MRI pipeline: converter → bias correction → normalize → inference → postprocess → output.

### Tasks
- [ ] Update `MRIPipeline.run()` with full pipeline
- [ ] Add multi-sequence handling (T1, T2, FLAIR)
- [ ] Apply `bias_field_correction()` for MRI
- [ ] Brain extraction → tissue segmentation chain
- [ ] Integration test

---

## Issue 5: M2 — Model weight management
**Labels:** `enhancement`, `M2`

### Description
Implement model download, validation, and versioning.

### Tasks
- [ ] Add actual model URLs to `scripts/download_models.sh`
- [ ] SHA-256 checksum verification for downloaded weights
- [ ] Model version tracking in `ModelRegistry`
- [ ] API endpoint for model status/download progress
- [ ] HuggingFace Hub integration option

---

## Issue 6: M2 — LLM report generation from segmentation
**Labels:** `enhancement`, `M2`

### Description
Connect LLM report generation to pipeline output.

### Tasks
- [ ] Compute volumetric measurements from segmentation masks
- [ ] Build structured summary dict for LLM prompt
- [ ] Generate report via `generate_report()`
- [ ] Store report as DICOM SR (Structured Report)
- [ ] Add confidence scoring / uncertainty metrics

---

## Issue 7: M2 — Persistent job store
**Labels:** `enhancement`, `M2`

### Description
Replace in-memory job dict with persistent storage.

### Tasks
- [ ] SQLite or PostgreSQL job store
- [ ] Job history with timestamps and duration
- [ ] Study-to-job relationship tracking
- [ ] Retry failed jobs
- [ ] Job cleanup / TTL policy

---

## Issue 8: Infrastructure — CI/CD pipeline
**Labels:** `infrastructure`

### Description
Set up GitHub Actions for testing and Docker builds.

### Tasks
- [ ] Pytest CI on push/PR
- [ ] Docker image build + push to GHCR
- [ ] FIPS compliance test in CI
- [ ] Lint (ruff) and type check (mypy)

---

## Issue 9: Documentation — Wiki setup
**Labels:** `documentation`

### Description
Create and maintain GitHub wiki as authoritative project documentation.

### Wiki Pages
- [ ] Home (architecture overview)
- [ ] Getting Started (setup, GPU configuration)
- [ ] DICOM Pipeline Reference
- [ ] Model Integration Guide (nnU-Net, MONAI)
- [ ] LLM Integration (Ollama setup, report generation)
- [ ] Security (FIPS 140, TLS, network segmentation)
- [ ] MCP Server Reference
- [ ] Sprint Planning & Progress

---

## Issue 10: Testing — End-to-end integration tests
**Labels:** `testing`, `M2`

### Description
Add integration tests that exercise the full pipeline with synthetic DICOM data.

### Tasks
- [ ] Generate synthetic CTA DICOM series (pydicom)
- [ ] Test full CTA pipeline with mock inference
- [ ] Verify RTSTRUCT contour coordinates
- [ ] Verify Secondary Capture pixel overlay
- [ ] Verify DICOM SEG segment encoding
- [ ] Test C-STORE via mock Orthanc server
