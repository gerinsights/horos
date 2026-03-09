"""Horos domain knowledge base for the MCP server.

Embedded expertise from codebase exploration of Horos v4.0.0 RC5.
"""

ARCHITECTURE = """
# System Architecture

## Nodes
- **Scanners**: CT (CTA head/neck), MRI (brain)
- **PACS_CORE**: Central DICOM server (Orthanc or dcm4chee), AE title `PACS_CORE`
- **AI_SEGMENT**: AI segmentation node (Ryzen 9/Bazzite + RX 7600 XT eGPU), AE title `AI_SEGMENT`
- **HOROS_M1**: Horos workstation (M1 Mac mini), AE title `HOROS_M1`

## Data Flow
1. Scanner → PACS_CORE (C-STORE)
2. PACS_CORE routes neuro CTA/MRI → AI_SEGMENT (Orthanc Lua routing)
3. AI_SEGMENT: receives DICOM → runs AI segmentation → sends DICOM SEG + Secondary Capture → PACS_CORE
4. Horos queries PACS_CORE → sees original series + AI overlays

## AI Server Stack (Docker Compose)
- **Orthanc** — DICOM node, REST API, Lua routing, DICOM TLS
- **AI Service** (FastAPI) — pipeline orchestration, webhook handler, MCP server
- **Ollama** — on-device LLM for report generation and study triage
- **Caddy** — TLS-terminating reverse proxy (FIPS-compliant ciphers)
- PyTorch + ROCm (GPU inference, GPU-agnostic: ROCm/CUDA/CPU)
- nnUNet v2 / MONAI (3D segmentation models)
- highdicom / pydicom (DICOM output generation)

## Security
- FIPS 140 Level 1 compliant by default
- OpenSSL 3.x FIPS provider in all containers
- TLS 1.2+ with ECDHE+AESGCM ciphers only
- ECDSA P-384 certificates
- Network segmentation: internal (service-to-service), dicom (PACS), external (HTTPS gateway)
- Non-root containers, read-only filesystems, no-new-privileges
"""

HOROS_CAPABILITIES = """
# Horos Display Capabilities

## What Horos CAN display:
- **DICOM overlays** (0x6000 group): 16 binary overlay channels, togglable
  - File: Horos/Sources/DCMPix.h — `overlaysChannelON[16]` array
- **DICOM Secondary Capture**: Color-overlaid slices appear as new series
  - This is how AI results are made visible in Horos
- **DICOM SR (Structured Reports)**: Full read/create support
  - Files: Horos/Sources/StructuredReport.h/mm, SRAnnotation.h/mm
- **ROIs**: Line, rectangle, oval, polygon, angle, brush, layer overlay
  - File: Horos/Sources/ROI.h/m (uses OpenGL rendering)
- **Presentation State**: Graphic objects (POINT, POLYLINE, CIRCLE, ELLIPSE)
  - File: DCM Framework/DCMPresentationState.h

## What Horos CANNOT display:
- **DICOM SEG** (Segmentation objects) — NOT supported
- **DICOM RTSTRUCT** (RT Structure Sets) — NOT supported
- **Metal rendering** — all rendering is OpenGL (1,065+ references across 70+ files)

## DICOM Networking:
- C-STORE SCP/SCU: Horos/Sources/DCMTKStoreSCU.mm
- C-FIND: Horos/Sources/DCMTKQueryNode.mm (patient/study/series/image level)
- C-MOVE/C-GET: Horos/Sources/QueryController.mm
- Auto-routing: Horos/Sources/DicomDatabase+Routing.mm (695 lines, full rule system)
- WADO: Horos/Sources/WADODownload.h/m
- TLS support with certificate selection from keychain

## Key Horos Architecture:
- Pure Objective-C/C++ (339 source files, zero Swift, zero Metal)
- macOS 11.0+ deployment target, arm64 (Apple Silicon)
- Version: v4.0.0 RC5
- Plugin system: Horos/Sources/PluginFilter.h (filterImage, processFiles, report actions)
- Dependencies: ITK, VTK, DCMTK, GDCM, OpenJPEG, OpenSSL, CharLS, Grok
"""

DICOM_FLOW = """
# DICOM Data Flow

```
┌──────────┐     C-STORE      ┌────────────┐    Lua webhook    ┌──────────────┐
│  Scanner  │ ──────────────→  │  PACS_CORE │ ──────────────→  │  AI_SEGMENT  │
│  (CT/MR)  │                  │  (Orthanc)  │                  │  (Ryzen/GPU) │
└──────────┘                  └────────────┘                  └──────────────┘
                                     │                                │
                                     │ C-FIND/C-MOVE                  │ C-STORE
                                     ▼                                │ (SEG + SC)
                              ┌────────────┐                          │
                              │  HOROS_M1   │ ◄────────────────────────┘
                              │  (Mac mini) │   (via PACS_CORE)
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
    → Create DICOM SEG (highdicom) + Secondary Capture (pydicom)
    → C-STORE results back to PACS_CORE
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
   - Optional: aneurysm candidate detection (saccular outpouchings)

## Output Segments
| Label | Structure |
|-------|-----------|
| 1 | Intracranial arteries |
| 2 | Carotid arteries |
| 3 | Vertebral arteries |
| 4 | Aneurysm candidates (optional) |

## DICOM Output
- DICOM SEG: Standards-compliant segmentation object (for PACS interop)
- Secondary Capture: Color-overlaid slices (for Horos viewing)
"""

PIPELINE_MRI = """
# MRI Brain/Tissue Segmentation Pipeline (Phase 2)

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

## Cryptographic Policy
- **OpenSSL 3.x FIPS provider** activated in all Python/Orthanc containers
- Config: `config/openssl-fips.cnf` sets `fips=yes` as default property
- All TLS uses FIPS-approved algorithms only

## TLS Configuration
- **Minimum protocol**: TLS 1.2
- **Cipher suites**: ECDHE+AESGCM only (AES-128-GCM, AES-256-GCM)
- **Key exchange**: ECDHE with P-256, P-384, or X25519
- **Certificates**: ECDSA P-384 + SHA-384 (generated via `scripts/generate_certs.sh`)
- **No**: MD5, SHA-1, RC4, DES, 3DES, RSA key exchange

## Network Segmentation (Docker)
- **internal** network: service-to-service only (no external access)
- **dicom** network: DICOM TLS port exposed to scanner/PACS network
- **external** network: HTTPS gateway only
- Orthanc REST API: internal only (not exposed to host)
- Ollama API: internal only

## Container Hardening
- Non-root user (`aiuser`) in AI service
- `read_only: true` where possible
- `no-new-privileges` security option
- Health checks on all services
- Secrets via environment variables (not baked into images)

## DICOM TLS
- Orthanc configured with `DicomTlsEnabled: true`
- Certificates: ECDSA P-384 (same CA as REST TLS)
- Horos supports TLS via DCMTK (configurable in Preference Panes)

## What FIPS 140 Level 1 Does NOT Require
- Physical security of the module (that's Level 2+)
- Tamper-evident seals (Level 2+)
- Identity-based authentication (Level 3+)
- Environmental protection (Level 4)
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
- Segmentation and LLM share the RX 7600 XT GPU
- Not simultaneous — segmentation runs first, then LLM for report generation
- Ollama automatically manages VRAM allocation
"""

# Map of resource URIs to their content
RESOURCES = {
    "horos://architecture": ("System Architecture", ARCHITECTURE),
    "horos://horos-capabilities": ("Horos Capabilities", HOROS_CAPABILITIES),
    "horos://dicom-flow": ("DICOM Data Flow", DICOM_FLOW),
    "horos://pipeline/cta": ("CTA Pipeline", PIPELINE_CTA),
    "horos://pipeline/mri": ("MRI Pipeline", PIPELINE_MRI),
    "horos://security": ("Security & FIPS 140", SECURITY),
    "horos://llm": ("LLM Integration", LLM_INTEGRATION),
}
