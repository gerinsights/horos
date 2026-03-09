"""MCP tool implementations for the Horos AI backend."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.mcp.knowledge import RESOURCES

logger = logging.getLogger(__name__)

# Base URLs — configured at startup
ORTHANC_URL = "http://localhost:8042"
AI_SERVICE_URL = "http://localhost:8000"


def configure(orthanc_url: str, ai_service_url: str) -> None:
    global ORTHANC_URL, AI_SERVICE_URL
    ORTHANC_URL = orthanc_url
    AI_SERVICE_URL = ai_service_url


async def horos_query_study(
    patient_name: str = "",
    patient_id: str = "",
    study_date: str = "",
    modality: str = "",
) -> dict[str, Any]:
    """Query PACS_CORE (via Orthanc) for studies matching criteria."""
    query: dict[str, str] = {}
    if patient_name:
        query["PatientName"] = patient_name
    if patient_id:
        query["PatientID"] = patient_id
    if study_date:
        query["StudyDate"] = study_date
    if modality:
        query["ModalitiesInStudy"] = modality

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{ORTHANC_URL}/tools/find",
            json={"Level": "Study", "Query": query, "Expand": True},
            timeout=30,
        )
        resp.raise_for_status()
        return {"studies": resp.json()}


async def horos_get_series(study_id: str) -> dict[str, Any]:
    """List all series in a study, including AI-generated ones."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{ORTHANC_URL}/studies/{study_id}", timeout=30)
        resp.raise_for_status()
        study = resp.json()

        series_list = []
        for series_id in study.get("Series", []):
            s_resp = await client.get(f"{ORTHANC_URL}/series/{series_id}", timeout=30)
            if s_resp.status_code == 200:
                series_list.append(s_resp.json().get("MainDicomTags", {}))

        return {"study_id": study_id, "series": series_list}


async def horos_trigger_segmentation(study_id: str, pipeline: str = "cta") -> dict[str, Any]:
    """Manually trigger an AI segmentation pipeline for a study."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{AI_SERVICE_URL}/pipeline/trigger",
            params={"study_id": study_id, "pipeline": pipeline},
            timeout=300,
        )
        resp.raise_for_status()
        return resp.json()


async def horos_pipeline_status(job_id: str) -> dict[str, Any]:
    """Check the status of a segmentation job."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{AI_SERVICE_URL}/pipeline/status/{job_id}", timeout=10)
        resp.raise_for_status()
        return resp.json()


async def horos_list_models() -> dict[str, Any]:
    """List available AI models."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{AI_SERVICE_URL}/models", timeout=10)
        resp.raise_for_status()
        return resp.json()


async def horos_get_config() -> dict[str, Any]:
    """Read current AE titles, routing rules, and model settings."""
    from src.config import load_settings

    settings = load_settings()
    return {
        "dicom": {k: v.model_dump() for k, v in settings.dicom.items()},
        "orthanc": settings.orthanc.model_dump(),
        "models": {k: v.model_dump() for k, v in settings.models.items()},
        "pipelines": {k: v.model_dump() for k, v in settings.pipelines.items()},
        "routing": {k: v.model_dump() for k, v in settings.routing.items()},
    }


async def horos_architecture_guide(subsystem: str = "overview") -> dict[str, str]:
    """Return architecture documentation for a specific subsystem."""
    uri = f"horos://{subsystem}" if not subsystem.startswith("horos://") else subsystem

    # Check direct match
    if uri in RESOURCES:
        title, content = RESOURCES[uri]
        return {"title": title, "content": content}

    # Check partial match
    for key, (title, content) in RESOURCES.items():
        if subsystem.lower() in key.lower():
            return {"title": title, "content": content}

    available = list(RESOURCES.keys())
    return {"error": f"Unknown subsystem: {subsystem}", "available": available}


async def horos_logs(service: str = "ai", lines: int = 50) -> dict[str, Any]:
    """Tail recent logs from AI service or Orthanc."""
    if service == "orthanc":
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{ORTHANC_URL}/tools/log-level", timeout=10)
            return {"service": "orthanc", "log_level": resp.text if resp.status_code == 200 else "unknown"}

    # For AI service, return recent log from in-memory buffer
    return {"service": "ai", "note": "Log streaming not yet implemented — check container logs"}


async def horos_llm_generate(
    prompt: str,
    system: str = "",
    model: str = "",
) -> dict[str, Any]:
    """Generate text using the on-device LLM (Ollama)."""
    from src.inference.llm import generate, DEFAULT_MODEL

    response = await generate(
        prompt=prompt,
        system=system,
        model=model or DEFAULT_MODEL,
    )
    return {"text": response.text, "model": response.model}


async def horos_llm_models() -> dict[str, Any]:
    """List LLM models available in Ollama."""
    from src.inference.llm import list_models

    models = await list_models()
    return {"models": models}
