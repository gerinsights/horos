"""DICOM to volume conversion utilities (M1 implementation)."""

from __future__ import annotations


async def dicom_to_volume(study_id: str, series_id: str | None = None):
    """Convert DICOM series to a 3D numpy volume via SimpleITK.

    To be implemented in M1.
    """
    raise NotImplementedError("DICOM-to-volume conversion not yet implemented")
