"""MRI brain/tissue segmentation pipeline (Phase 2)."""

from __future__ import annotations

import logging

from src.pipeline.base import BasePipeline, SegmentationResult

logger = logging.getLogger(__name__)


class MRIPipeline(BasePipeline):
    """Neuro MRI segmentation pipeline.

    Steps (to be implemented in M3):
    1. Fetch DICOM from Orthanc
    2. Convert to NIfTI per sequence
    3. Resample to 1mm isotropic
    4. Bias correction and intensity normalization
    5. Co-register sequences (T1/T2/FLAIR) if multi-sequence model
    6. Brain extraction → brain mask
    7. Tissue segmentation → GM/WM/CSF
    8. Optional: lesion/tumor model
    9. Post-process and create DICOM outputs
    """

    name = "mri"

    async def run(self, study_id: str) -> list[SegmentationResult]:
        logger.info("[MRI] Pipeline triggered for study %s", study_id)
        await self.fetch_dicom(study_id)

        logger.info("[MRI] Segmentation not yet implemented — returning empty result")
        return []
