"""Tests for DICOM output generation (placeholder for M1)."""

from __future__ import annotations

from src.pipeline.base import SegmentationResult


def test_segmentation_result_defaults():
    import numpy as np

    mask = np.zeros((10, 10, 10), dtype=np.int32)
    result = SegmentationResult(mask=mask)
    assert result.spacing == (1.0, 1.0, 1.0)
    assert result.labels == {}
    assert result.mask.shape == (10, 10, 10)


def test_segmentation_result_with_labels():
    import numpy as np

    mask = np.zeros((5, 5, 5), dtype=np.int32)
    mask[2, 2, 2] = 1
    mask[3, 3, 3] = 2

    result = SegmentationResult(
        mask=mask,
        labels={1: "Intracranial arteries", 2: "Carotid arteries"},
        spacing=(0.7, 0.7, 0.7),
    )
    assert result.labels[1] == "Intracranial arteries"
    assert result.spacing == (0.7, 0.7, 0.7)
