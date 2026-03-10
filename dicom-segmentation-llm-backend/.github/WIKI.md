# GitHub Wiki Content

Copy these sections to the GitHub wiki at:
https://github.com/gerinsights/dicom-segmentation-llm-backend/wiki

---

## Page: Home

# DICOM Segmentation Backend

Standalone AI-powered medical image segmentation backend with LLM integration.

## Architecture

```
┌─────────────┐     C-STORE     ┌─────────────┐    webhook     ┌──────────────┐
│   Scanner    │ ─────────────→ │   Orthanc    │ ────────────→ │  AI Service  │
│   (CT/MR)    │                │  (DICOM node)│               │  (FastAPI)   │
└─────────────┘                └─────────────┘               └──────────────┘
                                      │                              │
                                      │ C-FIND                       │ GPU inference
                                      ▼                              ▼
                               ┌─────────────┐               ┌──────────────┐
                               │    Viewer    │               │   Ollama     │
                               │  (any PACS)  │               │   (LLM)     │
                               └─────────────┘               └──────────────┘
```

## Quick Start

```bash
# 1. Configure GPU backend
cp .env.example .env
# Edit .env: set GPU_BACKEND=rocm|cuda|cpu

# 2. Generate TLS certificates
./scripts/generate_certs.sh

# 3. Start services
docker compose up -d

# 4. Verify
curl -k https://localhost:8443/health
```

## Key Features
- **GPU-agnostic**: ROCm (AMD), CUDA (NVIDIA), CPU fallback
- **FIPS 140 Level 1**: OpenSSL 3.x FIPS provider, ECDSA P-384 certs
- **Triple DICOM output**: RTSTRUCT + Secondary Capture + SEG
- **LLM integration**: Ollama for report generation and study triage
- **MCP server**: Claude Code integration via stdio/SSE

## Sprint Status
See [Sprint Planning](Sprint-Planning) for current progress.

---

## Page: Getting-Started

# Getting Started

## Prerequisites
- Docker + Docker Compose v2
- GPU (optional): AMD ROCm 6.2+ or NVIDIA CUDA 12.4+
- 8GB+ RAM (16GB+ recommended with LLM)

## GPU Configuration

### AMD ROCm
```bash
GPU_BACKEND=rocm
cp docker-compose.rocm.yml docker-compose.override.yml
# Set HSA_OVERRIDE_GFX_VERSION for your GPU in .env
```

### NVIDIA CUDA
```bash
GPU_BACKEND=cuda
cp docker-compose.cuda.yml docker-compose.override.yml
```

### CPU Only
```bash
GPU_BACKEND=cpu
# No override file needed
```

## Service Ports
| Service | Port | Protocol |
|---------|------|----------|
| DICOM TLS | 4242 | DICOM |
| HTTPS Gateway | 8443 | HTTPS |
| MCP SSE | 3001 | HTTP/SSE |

## Configuration
Edit `config/settings.yaml` for:
- DICOM AE titles and routing rules
- Model paths and framework selection
- Pipeline enable/disable
- LLM model selection

---

## Page: DICOM-Pipeline

# DICOM Pipeline Reference

## Pipeline Stages

### 1. DICOM Fetch (`src/dicom/converter.py`)
- Downloads series from Orthanc REST API as ZIP
- Sorts slices via SimpleITK GDCM reader
- Returns `VolumeData`: numpy array + spacing + origin + direction + source datasets

### 2. Preprocessing (`src/processing/preprocess.py`)
| Function | Description | Default |
|----------|-------------|---------|
| `resample_isotropic()` | Resample to target spacing | 0.7mm |
| `clip_hu()` | HU windowing | [-100, 700] CTA |
| `normalize_intensity()` | Z-score or min-max | z-score |
| `bias_field_correction()` | N4 correction (MRI) | shrink=4 |

### 3. Inference (`src/inference/`)
- `NNUNetRunner`: nnUNet v2 predictor API (stub)
- `MONAIRunner`: MONAI model loading (stub)
- `DeviceInfo`: GPU auto-detection (ROCm/CUDA/CPU)

### 4. Postprocessing (`src/processing/postprocess.py`)
| Function | Description |
|----------|-------------|
| `threshold_mask()` | Probability → binary at threshold |
| `connected_components()` | Remove small components |
| `largest_component()` | Keep only largest |
| `label_anatomical_regions()` | Spatial heuristic labeling |
| `smooth_mask()` | Morphological close+open |

### 5. DICOM Output (`src/dicom/output.py`)
Triple format strategy:
- **RTSTRUCT**: Contour extraction via `skimage.find_contours`, pixel→patient coordinate transform
- **Secondary Capture**: RGB overlay with configurable opacity, window/level from source
- **DICOM SEG**: highdicom binary segmentation with SCT coded concepts

### 6. C-STORE (`src/dicom/sender.py`)
Two-step: upload to Orthanc → forward to PACS modality

---

## Page: Security

# Security — FIPS 140 Level 1

## Cryptographic Module Boundary
- **OpenSSL 3.x FIPS provider** in all containers
- Built from source via `--no-binary cryptography`
- `openssl fipsinstall` run at Docker build time

## TLS Configuration
- Minimum: TLS 1.2
- Ciphers: ECDHE+AESGCM only
- Certificates: ECDSA P-384 + SHA-384
- Generated via `scripts/generate_certs.sh`

## Network Segmentation
| Network | Purpose | External? |
|---------|---------|-----------|
| internal | Service-to-service | No |
| dicom | DICOM TLS port | Scanner/PACS only |
| external | HTTPS gateway | Yes |

## Container Hardening
- Non-root user (`aiuser`)
- `read_only: true` filesystems
- `no-new-privileges` security option
- Health checks with dependency ordering

---

## Page: Sprint-Planning

# Sprint Planning

## M0 — Scaffold (DONE)
- [x] Project structure and packaging
- [x] Docker Compose (Orthanc + AI Service + Ollama + Caddy)
- [x] FastAPI with health check, webhook, pipeline routing
- [x] FIPS 140 Level 1 compliance
- [x] MCP server with 10 tools
- [x] Orthanc Lua routing script
- [x] Test suite (pipeline, FIPS, device detection)

## M1 — Core Pipeline (CURRENT)
- [x] DICOM converter (Orthanc → SimpleITK volume)
- [x] Preprocessing (resample, clip HU, normalize, bias correction)
- [x] Postprocessing (threshold, connected components, labeling, smoothing)
- [x] DICOM output (RTSTRUCT + Secondary Capture + SEG)
- [x] C-STORE sender
- [ ] nnU-Net inference runner
- [ ] MONAI inference runner
- [ ] Wire CTA pipeline end-to-end
- [ ] Wire MRI pipeline end-to-end

## M2 — Integration
- [ ] Model weight download + validation
- [ ] LLM report generation from segmentation
- [ ] Persistent job store
- [ ] CI/CD pipeline
- [ ] End-to-end integration tests

## M3 — Production
- [ ] Multi-sequence MRI co-registration
- [ ] Aneurysm candidate detection
- [ ] Performance optimization (batch inference)
- [ ] Monitoring + alerting
- [ ] Production deployment guide
