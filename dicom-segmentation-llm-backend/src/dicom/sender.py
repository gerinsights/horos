"""C-STORE sender for returning results to PACS via Orthanc REST API."""

from __future__ import annotations

import io
import logging

import httpx
import pydicom
from pydicom.dataset import Dataset

logger = logging.getLogger(__name__)


async def upload_to_orthanc(
    dataset: Dataset,
    orthanc_url: str = "http://orthanc:8042",
) -> str:
    """Upload a single DICOM dataset to Orthanc via REST API.

    Args:
        dataset: pydicom Dataset to upload.
        orthanc_url: Orthanc REST API base URL.

    Returns:
        Orthanc instance ID of the uploaded object.
    """
    buffer = io.BytesIO()
    pydicom.dcmwrite(buffer, dataset, write_like_original=False)
    dicom_bytes = buffer.getvalue()

    async with httpx.AsyncClient(base_url=orthanc_url, timeout=30) as client:
        resp = await client.post(
            "/instances",
            content=dicom_bytes,
            headers={"Content-Type": "application/dicom"},
        )
        resp.raise_for_status()
        result = resp.json()

    instance_id = result.get("ID", "unknown")
    status = result.get("Status", "unknown")
    logger.info("Uploaded to Orthanc: %s (status: %s)", instance_id, status)
    return instance_id


async def store_to_pacs(
    datasets: Dataset | list[Dataset],
    destination_ae: str = "PACS",
    orthanc_url: str = "http://orthanc:8042",
) -> None:
    """Upload DICOM objects to Orthanc and C-STORE to a remote PACS.

    Two-step process:
    1. Upload DICOM to Orthanc's local store via POST /instances
    2. Forward to remote modality via POST /modalities/{ae}/store

    Args:
        datasets: Single Dataset or list of Datasets to send.
        destination_ae: AE title of the destination (must be configured in Orthanc).
        orthanc_url: Orthanc REST API base URL.
    """
    if isinstance(datasets, Dataset):
        datasets = [datasets]

    if not datasets:
        logger.warning("No datasets to send")
        return

    # Step 1: Upload all to Orthanc
    instance_ids = []
    for ds in datasets:
        instance_id = await upload_to_orthanc(ds, orthanc_url)
        instance_ids.append(instance_id)

    logger.info("Uploaded %d instances to Orthanc", len(instance_ids))

    # Step 2: C-STORE to remote PACS via Orthanc modality
    async with httpx.AsyncClient(base_url=orthanc_url, timeout=120) as client:
        resp = await client.get("/modalities")
        resp.raise_for_status()
        modalities = resp.json()

        if destination_ae not in modalities:
            logger.warning(
                "Modality %s not configured in Orthanc (available: %s). "
                "Results stored locally only.",
                destination_ae,
                modalities,
            )
            return

        for instance_id in instance_ids:
            resp = await client.post(
                f"/modalities/{destination_ae}/store",
                json={"Resources": [instance_id]},
            )
            if resp.status_code == 200:
                logger.info("C-STORE %s → %s: OK", instance_id, destination_ae)
            else:
                logger.error(
                    "C-STORE %s → %s failed: %s %s",
                    instance_id,
                    destination_ae,
                    resp.status_code,
                    resp.text,
                )

    logger.info(
        "C-STORE complete: %d instances → %s", len(instance_ids), destination_ae
    )
