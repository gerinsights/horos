"""Tests for postprocessing utilities."""

from __future__ import annotations

import numpy as np

from src.processing.postprocess import (
    connected_components,
    label_anatomical_regions,
    largest_component,
    smooth_mask,
    threshold_mask,
)


def test_threshold_mask_basic():
    probs = np.array([0.1, 0.5, 0.9, 0.3, 0.7], dtype=np.float32)
    mask = threshold_mask(probs, threshold=0.5)

    assert mask.dtype == np.uint8
    np.testing.assert_array_equal(mask, [0, 1, 1, 0, 1])


def test_threshold_mask_3d():
    probs = np.random.rand(10, 32, 32).astype(np.float32)
    mask = threshold_mask(probs, threshold=0.5)

    assert mask.shape == probs.shape
    assert set(np.unique(mask)).issubset({0, 1})


def test_connected_components_removes_small():
    mask = np.zeros((20, 20, 20), dtype=np.uint8)
    mask[5:15, 5:15, 5:15] = 1
    mask[0, 0, 0:3] = 1

    cleaned = connected_components(mask, min_size=100)

    assert cleaned.sum() < mask.sum()
    assert cleaned[10, 10, 10] == 1
    assert cleaned[0, 0, 0] == 0


def test_connected_components_empty_mask():
    mask = np.zeros((10, 10, 10), dtype=np.uint8)
    cleaned = connected_components(mask, min_size=100)
    assert cleaned.sum() == 0


def test_largest_component():
    mask = np.zeros((20, 20, 20), dtype=np.uint8)
    mask[2:5, 2:5, 2:5] = 1
    mask[10:18, 10:18, 10:18] = 1

    result = largest_component(mask)

    assert result[12, 12, 12] == 1
    assert result[3, 3, 3] == 0


def test_label_anatomical_regions_basic():
    mask = np.zeros((100, 64, 64), dtype=np.uint8)

    mask[10:30, 20:30, 20:30] = 1
    mask[10:30, 40:50, 40:50] = 1
    mask[60:90, 25:40, 25:40] = 1

    label_map, labels = label_anatomical_regions(mask)

    assert label_map.shape == mask.shape
    assert len(labels) == 5
    assert label_map[70, 30, 30] == 5
    assert label_map.max() <= 5


def test_label_anatomical_regions_empty():
    mask = np.zeros((50, 50, 50), dtype=np.uint8)
    label_map, labels = label_anatomical_regions(mask)
    assert label_map.sum() == 0


def test_smooth_mask_preserves_shape():
    mask = np.zeros((20, 20, 20), dtype=np.uint8)
    mask[5:15, 5:15, 5:15] = 1

    smoothed = smooth_mask(mask, iterations=1)

    assert smoothed.shape == mask.shape
    assert smoothed.dtype == np.uint8
    assert smoothed[10, 10, 10] == 1
