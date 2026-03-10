# DICOM AI Segmentation Backend

GPU-agnostic medical image segmentation pipeline with FIPS 140 Level 1 TLS compliance.

## Architecture

```
Scanner/PACS ──DICOM TLS──▶ Orthanc ──HTTP──▶ AI Service ──HTTP──▶ Ollama (LLM)
                               │                   │
                               ▼                   ▼
                          DICOM Store        Segmentation
                                            (nnU-Net / MONAI)
```

- **Orthanc** — DICOM node with TLS, receives studies, routes to AI
- **AI Service** — FastAPI + PyTorch segmentation (ROCm/CUDA/CPU)
- **Ollama** — Local LLM for report generation
- **Caddy** — TLS termination gateway (HTTPS for REST/MCP)

## Quick Start

```bash
cp .env.example .env         # Configure GPU backend, ports, etc.
./scripts/generate_certs.sh  # Generate TLS certificates
docker compose up -d
```

### GPU Configuration

Set `GPU_BACKEND` in `.env`:

| Backend | Value | Notes |
|---------|-------|-------|
| CPU     | `cpu` | Default, works everywhere |
| AMD ROCm | `rocm` | Set `HSA_OVERRIDE_GFX_VERSION` for your GPU |
| NVIDIA CUDA | `cuda` | Copy `docker-compose.cuda.yml` to `docker-compose.override.yml` |

### Ports

| Port | Service | Protocol |
|------|---------|----------|
| 4242 | DICOM TLS | DICOM (configurable via `DICOM_PORT`) |
| 8443 | HTTPS gateway | REST API, MCP (configurable via `HTTPS_PORT`) |
| 3001 | MCP SSE | Claude Code integration (configurable via `MCP_PORT`) |

## FIPS 140 Level 1 Compliance

- OpenSSL 3.x FIPS provider with `fipsinstall` integrity verification
- TLS 1.2+ with ECDHE+AES-GCM cipher suites only
- ECDSA P-384 certificates
- DICOM TLS per BCP 195 Profile B.12
- `cryptography` package built from source against system FIPS OpenSSL
- See `config/openssl-fips.cnf` for full cryptographic policy

## Project Structure

```
├── config/              # Orthanc, Caddy, OpenSSL FIPS configs
├── docker-compose.yml   # Main stack definition
├── scripts/             # Certificate generation, utilities
├── src/
│   ├── dicom/           # DICOM routing and C-STORE handlers
│   ├── inference/       # GPU device detection, model loading
│   ├── mcp/             # MCP server + knowledge base
│   └── main.py          # FastAPI application
└── tests/               # Unit tests
```

## Development

```bash
pip install -e ".[dev]"
pytest tests/
```

## License

Private — gerinsights
