"""Route studies to the appropriate segmentation pipeline."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from src.dicom.receiver import JobStatus, get_all_jobs, get_job
from src.pipeline.cta import CTAPipeline
from src.pipeline.mri import MRIPipeline

logger = logging.getLogger(__name__)

router = APIRouter()

PIPELINES = {
    "cta": CTAPipeline(),
    "mri": MRIPipeline(),
}


async def route_study(study_id: str, pipeline_name: str) -> None:
    """Route a study to the named pipeline and execute it."""
    pipeline = PIPELINES.get(pipeline_name)
    if not pipeline:
        raise ValueError(f"Unknown pipeline: {pipeline_name}")

    logger.info("Routing study %s to %s pipeline", study_id, pipeline_name)
    results = await pipeline.run(study_id)
    await pipeline.send_results(study_id, results)


@router.post("/trigger")
async def trigger_pipeline(study_id: str, pipeline: str) -> dict:
    """Manually trigger a pipeline for a study."""
    if pipeline not in PIPELINES:
        return {"error": f"Unknown pipeline: {pipeline}"}

    # Import here to avoid circular dependency
    from src.dicom.receiver import OrthancWebhook, orthanc_webhook
    from fastapi import BackgroundTasks

    bg = BackgroundTasks()
    payload = OrthancWebhook(study_id=study_id, pipeline=pipeline)
    result = await orthanc_webhook(payload, bg)
    # Execute background tasks synchronously for manual triggers
    for task in bg.tasks:
        await task()
    return result


@router.get("/status/{job_id}")
async def pipeline_status(job_id: str) -> dict:
    job = get_job(job_id)
    if not job:
        return {"error": "Job not found"}
    return job.model_dump()


@router.get("/jobs")
async def list_jobs() -> list[dict]:
    return [j.model_dump() for j in get_all_jobs()]
