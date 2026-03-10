"""DICOM to volume conversion via Orthanc REST API + SimpleITK."""

from __future__ import annotations

import io
import logging
import os
import tempfile
import zipfile
from dataclasses import dataclass

import httpx
import numpy as np
import pydicom
import SimpleITK as sitk

logger = logging.getLogger(__name__)


@dataclass
class VolumeData:
    """3D volume with spatial metadata."""

    array: np.ndarray  # (D, H, W) float32
    spacing: tuple[float, float, float]
    origin: tuple[float, float, float]
    direction: tuple[float, ...]
    series_id: str
    study_id: str
    source_datasets: list  # pydicom Datasets for DICOM output


async def fetch_series_ids(study_id: str, orthanc_url: str) -> list[str]:
    """Get all series IDs for a study from Orthanc."""
    async with httpx.AsyncClient(base_url=orthanc_url, timeout=30) as client:
        resp = await client.get(f"/studies/{study_id}")
        resp.raise_for_status()
        return resp.json()["Series"]


async def dicom_to_volume(
    study_id: str,
    series_id: str | None = None,
    orthanc_url: str = "http://orthanc:8042",
) -> VolumeData:
    """Fetch DICOM series from Orthanc and convert to a 3D SimpleITK volume.

    Args:
        study_id: Orthanc study ID.
        series_id: Orthanc series ID. If None, uses first series.
        orthanc_url: Orthanc REST API base URL.

    Returns:
        VolumeData with numpy array and spatial metadata.
    """
    async with httpx.AsyncClient(base_url=orthanc_url, timeout=60) as client:
        # Resolve series ID
        if series_id is None:
            series_ids = await fetch_series_ids(study_id, orthanc_url)
            if not series_ids:
                raise ValueError(f"No series found for study {study_id}")
            series_id = series_ids[0]
            logger.info("Auto-selected series %s from study %s", series_id, study_id)

        # Download series as a ZIP of DICOM files
        logger.info("Downloading series %s from Orthanc", series_id)
        resp = await client.get(
            f"/series/{series_id}/archive",
            headers={"Accept": "application/zip"},
        )
        resp.raise_for_status()

    # Extract DICOM files from ZIP
    dicom_files = []
    source_datasets = []

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            dicom_bytes = zf.read(name)
            dicom_files.append(dicom_bytes)

    if not dicom_files:
        raise ValueError(f"No DICOM files in series {series_id}")

    logger.info("Downloaded %d DICOM files for series %s", len(dicom_files), series_id)

    # Read DICOM files with SimpleITK
    reader = sitk.ImageSeriesReader()
    reader.MetaDataDictionaryArrayUpdateOn()
    reader.LoadPrivateTagsOn()

    # Write to temp files for SimpleITK (it needs file paths)
    with tempfile.TemporaryDirectory(prefix="dicom_") as tmpdir:
        file_paths = []
        for i, dcm_bytes in enumerate(dicom_files):
            path = os.path.join(tmpdir, f"{i:06d}.dcm")
            with open(path, "wb") as f:
                f.write(dcm_bytes)
            file_paths.append(path)

        # Let SimpleITK sort by slice position
        sorted_names = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(tmpdir)
        if not sorted_names:
            sorted_names = file_paths

        reader.SetFileNames(sorted_names)
        image = reader.Execute()

        # Load source datasets for DICOM output metadata
        for path in sorted_names:
            source_datasets.append(pydicom.dcmread(path, stop_before_pixels=True))

    array = sitk.GetArrayFromImage(image)  # (D, H, W)
    spacing = image.GetSpacing()  # (x, y, z) in mm
    origin = image.GetOrigin()
    direction = image.GetDirection()

    logger.info(
        "Volume: shape=%s, spacing=%.2f x %.2f x %.2f mm, dtype=%s",
        array.shape,
        spacing[0],
        spacing[1],
        spacing[2],
        array.dtype,
    )

    return VolumeData(
        array=array.astype(np.float32),
        spacing=(spacing[2], spacing[1], spacing[0]),  # (D, H, W) order
        origin=(origin[2], origin[1], origin[0]),
        direction=direction,
        series_id=series_id,
        study_id=study_id,
        source_datasets=source_datasets,
    )


def volume_to_sitk(volume: VolumeData) -> sitk.Image:
    """Convert VolumeData back to a SimpleITK Image."""
    image = sitk.GetImageFromArray(volume.array)
    image.SetSpacing((volume.spacing[2], volume.spacing[1], volume.spacing[0]))
    image.SetOrigin((volume.origin[2], volume.origin[1], volume.origin[0]))
    image.SetDirection(volume.direction)
    return image
