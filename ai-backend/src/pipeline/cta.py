"""CTA vessel segmentation pipeline (Phase 1)."""

from __future__ import annotations

import logging

from src.pipeline.base import BasePipeline, SegmentationResult

logger = logging.getLogger(__name__)


class CTAPipeline(BasePipeline):
    """Neuro CTA vessel segmentation pipeline.

    Steps (to be implemented in M1):
    1. Fetch DICOM from Orthanc
    2. Convert to 3D volume
    3. Resample to isotropic spacing (0.6-0.8mm)
    4. HU clipping to vascular window [-100, 700]
    5. Intensity normalization
    6. Run nnUNet/MONAI vessel segmentation
    7. Post-process: threshold, connected components, anatomical labeling
    8. Create DICOM SEG + Secondary Capture
    9. C-STORE back to PACS
    """

    name = "cta"

    async def run(self, study_id: str) -> list[SegmentationResult]:
        logger.info("[CTA] Pipeline triggered for study %s", study_id)
        await self.fetch_dicom(study_id)

        # M1: actual inference
        logger.info("[CTA] Segmentation not yet implemented — returning empty result")
        return []
