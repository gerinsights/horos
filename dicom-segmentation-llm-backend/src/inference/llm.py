"""LLM integration via Ollama for report generation and study triage.

GPU-agnostic: Ollama manages its own ROCm/CUDA/CPU backend.
Communication is over internal Docker network (HTTP, no TLS needed).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")


@dataclass
class LLMResponse:
    text: str
    model: str
    total_duration_ms: int | None = None


async def generate(
    prompt: str,
    system: str = "",
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> LLMResponse:
    """Generate text using Ollama.

    Args:
        prompt: User prompt
        system: System prompt for context
        model: Ollama model name (e.g., "llama3.2:3b", "mistral:7b")
        temperature: Sampling temperature (lower = more deterministic)
        max_tokens: Maximum response tokens
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if system:
        payload["system"] = system

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
        resp.raise_for_status()
        data = resp.json()

    return LLMResponse(
        text=data.get("response", ""),
        model=data.get("model", model),
        total_duration_ms=data.get("total_duration"),
    )


async def generate_report(
    segmentation_summary: dict,
    patient_context: str = "",
    model: str = DEFAULT_MODEL,
) -> str:
    """Generate a structured radiology report from segmentation results.

    Args:
        segmentation_summary: Dict with keys like 'labels', 'volumes_ml', 'findings'
        patient_context: Clinical context (age, indication, etc.)
        model: Ollama model to use
    """
    system = (
        "You are a neuroradiology AI assistant. Generate concise, structured findings "
        "based on AI segmentation results. Use standard radiology reporting format. "
        "Always include a disclaimer that findings are AI-generated and require radiologist review."
    )

    prompt = f"""Segmentation Results:
{_format_summary(segmentation_summary)}

{f"Clinical Context: {patient_context}" if patient_context else ""}

Generate a structured findings report."""

    response = await generate(prompt=prompt, system=system, model=model)
    return response.text


async def triage_study(
    study_description: str,
    modality: str,
    body_part: str,
    model: str = DEFAULT_MODEL,
) -> dict:
    """Use LLM to assist with study triage / pipeline routing.

    Returns suggested pipeline and confidence.
    """
    system = (
        "You are a DICOM study classifier. Given study metadata, determine "
        "the appropriate AI pipeline. Respond with JSON only: "
        '{"pipeline": "cta"|"mri"|"none", "confidence": 0.0-1.0, "reason": "..."}'
    )

    prompt = f"""Study: {study_description}
Modality: {modality}
Body Part: {body_part}

Classify this study."""

    response = await generate(
        prompt=prompt, system=system, model=model, temperature=0.1
    )
    import json

    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        return {"pipeline": "none", "confidence": 0.0, "reason": response.text}


async def list_models() -> list[dict]:
    """List models available in Ollama."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{OLLAMA_URL}/api/tags")
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("models", [])


async def ensure_model(model: str = DEFAULT_MODEL) -> bool:
    """Pull a model if not already available."""
    models = await list_models()
    model_names = [m.get("name", "") for m in models]

    if model in model_names:
        logger.info("Model %s already available", model)
        return True

    logger.info("Pulling model %s...", model)
    async with httpx.AsyncClient(timeout=600) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/pull",
            json={"name": model, "stream": False},
            timeout=600,
        )
        return resp.status_code == 200


def _format_summary(summary: dict) -> str:
    """Format segmentation summary for LLM prompt."""
    lines = []
    for key, value in summary.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            for k, v in value.items():
                lines.append(f"  {k}: {v}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)
