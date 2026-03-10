"""DICOM output generation: SEG + Secondary Capture (M1 implementation)."""

from __future__ import annotations


async def create_dicom_seg(study_id: str, segmentation_result) -> bytes:
    """Create a DICOM SEG object from a segmentation result using highdicom.

    To be implemented in M1.
    """
    raise NotImplementedError("DICOM SEG creation not yet implemented")


async def create_secondary_capture(study_id: str, segmentation_result) -> list[bytes]:
    """Create Secondary Capture DICOM series with color overlay.

    To be implemented in M1.
    """
    raise NotImplementedError("Secondary Capture creation not yet implemented")
