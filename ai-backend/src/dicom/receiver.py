"""Webhook endpoint called by Orthanc when a study becomes stable."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from src.pipeline.router import route_study

logger = logging.getLogger(__name__)

router = APIRouter()


class OrthancWebhook(BaseModel):
    study_id: str
    pipeline: str
    modality: str = ""
    body_part: str = ""
    description: str = ""


class JobStatus(BaseModel):
    job_id: str
    study_id: str
    pipeline: str
    status: str  # queued, running, completed, failed
    created_at: str
    error: str | None = None


# In-memory job store (replace with persistent store in production)
_jobs: dict[str, JobStatus] = {}


@router.post("/orthanc")
async def orthanc_webhook(
    payload: OrthancWebhook,
    background_tasks: BackgroundTasks,
) -> dict:
    """Handle incoming study notification from Orthanc."""
    job_id = str(uuid.uuid4())[:8]

    job = JobStatus(
        job_id=job_id,
        study_id=payload.study_id,
        pipeline=payload.pipeline,
        status="queued",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _jobs[job_id] = job

    logger.info(
        "Received study %s for %s pipeline (job %s)",
        payload.study_id,
        payload.pipeline,
        job_id,
    )

    background_tasks.add_task(_run_pipeline, job_id, payload)
    return {"job_id": job_id, "status": "queued"}


async def _run_pipeline(job_id: str, payload: OrthancWebhook) -> None:
    """Execute the segmentation pipeline in the background."""
    job = _jobs[job_id]
    job.status = "running"

    try:
        await route_study(payload.study_id, payload.pipeline)
        job.status = "completed"
        logger.info("Job %s completed", job_id)
    except Exception as e:
        job.status = "failed"
        job.error = str(e)
        logger.error("Job %s failed: %s", job_id, e)


def get_job(job_id: str) -> JobStatus | None:
    return _jobs.get(job_id)


def get_all_jobs() -> list[JobStatus]:
    return list(_jobs.values())
