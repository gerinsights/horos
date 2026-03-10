"""Domain knowledge base for the MCP server.

Architecture documentation and DICOM pipeline reference.
"""

ARCHITECTURE = """
# System Architecture

## Components
- **Orthanc**: DICOM node with REST API, Lua routing, DICOM TLS
- **AI Service** (FastAPI): Pipeline orchestration, webhook handler, MCP server
- **Ollama**: On-device LLM for report generation and study triage
- **Caddy**: TLS-terminating reverse proxy (FIPS-compliant ciphers)
- **PyTorch + ROCm/CUDA**: GPU-agnostic inference backend
- **nnU-Net v2 / MONAI**: 3D segmentation models
- **highdicom / pydicom**: DICOM output generation

## Data Flow
1. Scanner → PACS (C-STORE)
2. PACS routes studies → Orthanc (Lua routing by modality/body part)
3. Orthanc webhook → FastAPI → pipeline selection
4. Pipeline: fetch DICOM → preprocess → GPU inference → postprocess
5. Generate triple output: RTSTRUCT + Secondary Capture + DICOM SEG
6. C-STORE results back to PACS
7. Viewer queries PACS → sees original series + AI overlays

## Security
- FIPS 140 Level 1 compliant by default
- OpenSSL 3.x FIPS provider in all containers
- TLS 1.2+ with ECDHE+AESGCM ciphers only
- ECDSA P-384 certificates
- Network segmentation: internal (service-to-service), dicom (PACS), external (HTTPS gateway)
- Non-root containers, read-only filesystems, no-new-privileges
"""

DICOM_FLOW = """
# DICOM Data Flow

```
┌──────────┐     C-STORE      ┌────────────┐    Lua webhook    ┌──────────────┐
│  Scanner  │ ──────────────→  │    PACS     │ ──────────────→  │  AI_SEGMENT  │
│  (CT/MR)  │                  │  (Orthanc)  │                  │  (GPU node)  │
└──────────┘                  └────────────┘                  └──────────────┘
                                     │                                │
                                     │ C-FIND/C-MOVE                  │ C-STORE
                                     ▼                                │ (RTSTRUCT + SC + SEG)
                              ┌────────────┐                          │
                              │   Viewer    │ ◄────────────────────────┘
                              │             │   (via PACS)
                              └────────────┘

AI Pipeline (inside AI_SEGMENT):
  Orthanc receives study
    → Lua OnStableStudy fires
    → HTTP POST to FastAPI /webhook/orthanc
    → FastAPI routes to CTA or MRI pipeline
    → Fetch DICOM from Orthanc REST API
    → Preprocess (resample, normalize, clip)
    → GPU inference (nnUNet/MONAI via ROCm/CUDA/CPU)
    → Post-process (threshold, connected components)
    → Create triple output:
      - DICOM RTSTRUCT — interactive contours (most PACS viewers)
      - DICOM Secondary Capture — burned-in overlay (universal)
      - DICOM SEG — voxel-level archive (OHIF/3D Slicer interop)
    → C-STORE results back to PACS
```
"""

PIPELINE_CTA = """
# CTA Vessel Segmentation Pipeline

## Input
- CT Angiography (head/neck)
- Detected by: Modality=CT, BodyPartExamined in {HEAD, NECK}, or StudyDescription contains CTA

## Processing Steps
1. Fetch DICOM from Orthanc REST API
2. Convert to 3D volume (SimpleITK)
3. Resample to isotropic spacing (0.6-0.8mm)
4. HU clipping: vascular window [-100, 700]
5. Intensity normalization (z-score)
6. 3D segmentation: nnUNet v2 (3D full-resolution) or MONAI DynUNet
7. Post-processing:
   - Probability threshold
   - Connected component analysis
   - Anatomical labeling: intracranial arteries, carotids, vertebrals
   - Optional: aneurysm candidate detection

## Output Segments
| Label | Structure |
|-------|-----------|
| 1 | Intracranial arteries |
| 2 | Carotid arteries |
| 3 | Vertebral arteries |
| 4 | Aneurysm candidates (optional) |

## DICOM Output
- DICOM RTSTRUCT: Interactive contours for PACS viewer overlay
- DICOM Secondary Capture: Color-overlaid slices (universal viewing)
- DICOM SEG: Standards-compliant segmentation object (for interop)
"""

PIPELINE_MRI = """
# MRI Brain/Tissue Segmentation Pipeline

## Input
- MRI Brain (T1, T2, FLAIR, DWI)
- Detected by: Modality=MR, BodyPartExamined in {HEAD, BRAIN}

## Processing Steps
1. Fetch DICOM from Orthanc
2. Convert to NIfTI per sequence
3. Resample to 1mm isotropic
4. Bias field correction (N4)
5. Intensity normalization (z-score)
6. Co-register sequences if multi-sequence model
7. Brain extraction → brain mask
8. Tissue segmentation → GM/WM/CSF
9. Optional: lesion/tumor/stroke models

## Output Segments
| Label | Structure |
|-------|-----------|
| 1 | Brain parenchyma |
| 2 | Gray matter |
| 3 | White matter |
| 4 | CSF |
| 5 | Lesion (if present) |
"""

SECURITY = """
# Security Architecture — FIPS 140 Level 1

## FIPS 140 Level 1 Requirements (software-only)
- Use a CMVP-validated cryptographic module (OpenSSL 3.x FIPS provider)
- FIPS-approved algorithms only: AES, SHA-2/SHA-3, ECDSA, RSA 2048+, ECDH P-256+
- Disallowed: MD5, SHA-1 for signatures, 3DES, ChaCha20-Poly1305, RC4
- Self-tests: power-up integrity check + known-answer tests (handled by `openssl fipsinstall`)

## TLS Configuration
- **Minimum protocol**: TLS 1.2
- **TLS 1.3 suites**: TLS_AES_256_GCM_SHA384, TLS_AES_128_GCM_SHA256
- **TLS 1.2 suites**: ECDHE_RSA/ECDSA_WITH_AES_{128,256}_GCM_SHA{256,384}
- **Key exchange**: ECDHE with P-256, P-384 only
- **Certificates**: ECDSA P-384 + SHA-384 (generated via `scripts/generate_certs.sh`)

## DICOM TLS
- Orthanc: `DicomTlsEnabled: true` with FIPS certs
- Compatible with DICOM Supplement 230 / BCP 195 Profile B.12

## Network Segmentation (Docker)
- **internal**: service-to-service only (no external access)
- **dicom**: DICOM TLS port exposed to scanner/PACS network
- **external**: HTTPS gateway only

## Container Hardening
- Non-root user in AI service
- `read_only: true` where possible
- `no-new-privileges` security option
- Health checks with dependency ordering
"""

LLM_INTEGRATION = """
# LLM Integration (Ollama)

## Architecture
- Ollama runs as a Docker sidecar service
- GPU-agnostic: uses same ROCm/CUDA devices as AI segmentation
- Internal network only — not exposed externally
- REST API: http://ollama:11434

## Use Cases
1. **Report generation**: Structured radiology findings from segmentation results
2. **Study triage**: Natural language classification of study metadata to pipeline routing
3. **DICOM explanation**: Explain DICOM tags and concepts in clinical context
4. **Interactive queries**: Answer questions about studies via MCP tools

## Models
- Default: `llama3.2:3b` (fits in 8GB VRAM alongside segmentation models)
- Can upgrade to larger models when GPU memory allows
- Models managed via `ollama pull` / Ollama REST API

## GPU Sharing
- Segmentation and LLM share the GPU (ROCm/CUDA)
- Not simultaneous — segmentation runs first, then LLM for report generation
- Ollama automatically manages VRAM allocation
"""

# Map of resource URIs to their content
RESOURCES = {
    "segmentation://architecture": ("System Architecture", ARCHITECTURE),
    "segmentation://dicom-flow": ("DICOM Data Flow", DICOM_FLOW),
    "segmentation://pipeline/cta": ("CTA Pipeline", PIPELINE_CTA),
    "segmentation://pipeline/mri": ("MRI Pipeline", PIPELINE_MRI),
    "segmentation://security": ("Security & FIPS 140", SECURITY),
    "segmentation://llm": ("LLM Integration", LLM_INTEGRATION),
}
