"""Base class for segmentation pipelines."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SegmentationResult:
    """Result of a segmentation pipeline run."""

    mask: np.ndarray  # (D, H, W) integer label map
    labels: dict[int, str] = field(default_factory=dict)  # label_id -> name
    spacing: tuple[float, float, float] = (1.0, 1.0, 1.0)
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
    direction: tuple[float, ...] = (1, 0, 0, 0, 1, 0, 0, 0, 1)


class BasePipeline(ABC):
    """Abstract base for modality-specific segmentation pipelines."""

    name: str = "base"

    @abstractmethod
    async def run(self, study_id: str) -> list[SegmentationResult]:
        """Run the full pipeline: fetch DICOM → preprocess → infer → postprocess.

        Returns a list of segmentation results (one per model/task).
        """
        ...

    async def fetch_dicom(self, study_id: str) -> None:
        """Fetch DICOM data from Orthanc. Placeholder for M1."""
        logger.info("[%s] Fetching DICOM for study %s", self.name, study_id)

    async def send_results(self, study_id: str, results: list[SegmentationResult]) -> None:
        """Create DICOM SEG + Secondary Capture and C-STORE back to PACS. Placeholder for M1."""
        logger.info(
            "[%s] Sending %d result(s) for study %s",
            self.name,
            len(results),
            study_id,
        )
