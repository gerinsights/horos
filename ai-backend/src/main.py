"""FastAPI application for the Neuro DICOM AI segmentation backend."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI

from src.config import Settings, load_settings
from src.dicom.receiver import router as webhook_router
from src.inference.device import DeviceInfo, detect_device
from src.pipeline.router import router as pipeline_router

logger = logging.getLogger(__name__)

settings: Settings | None = None
device_info: DeviceInfo | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global settings, device_info
    settings = load_settings()
    device_info = detect_device()
    logger.info("Neuro DICOM AI backend starting")
    logger.info("Device: %s", device_info)
    logger.info("Orthanc URL: %s", settings.orthanc.url)
    yield
    logger.info("Neuro DICOM AI backend shutting down")


app = FastAPI(
    title="Neuro DICOM AI",
    description="AI segmentation backend for neuro CTA/MRI",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(webhook_router, prefix="/webhook", tags=["webhook"])
app.include_router(pipeline_router, prefix="/pipeline", tags=["pipeline"])


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "device": device_info.summary() if device_info else "unknown",
        "fips_mode": _check_fips(),
    }


def _check_fips() -> bool:
    """Check if OpenSSL FIPS mode is active."""
    try:
        import ssl
        ctx = ssl.create_default_context()
        # OpenSSL 3.x with FIPS provider restricts available ciphers
        ciphers = ctx.get_ciphers()
        # If FIPS is active, no legacy ciphers (RC4, DES, etc.) will be present
        return not any("RC4" in c["name"] or "DES" in c["name"] for c in ciphers)
    except Exception:
        return False


@app.get("/llm/models")
async def llm_models() -> dict:
    """List LLM models available in Ollama."""
    from src.inference.llm import list_models as ollama_list
    models = await ollama_list()
    return {"models": models}


@app.get("/models")
async def list_models() -> dict:
    if not settings:
        return {"models": {}}
    return {
        "models": {
            name: {
                "framework": m.framework,
                "description": m.description,
            }
            for name, m in settings.models.items()
        }
    }


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
