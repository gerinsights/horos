"""Tests for preprocessing utilities."""

from __future__ import annotations

import numpy as np
import SimpleITK as sitk

from src.processing.preprocess import clip_hu, normalize_intensity, resample_isotropic


def _make_test_image(spacing=(1.0, 1.0, 2.0), size=(64, 64, 32)):
    """Create a test SimpleITK image with known properties."""
    arr = np.random.randn(*size[::-1]).astype(np.float32) * 100 + 40  # ~HU range
    img = sitk.GetImageFromArray(arr)
    img.SetSpacing(spacing)
    img.SetOrigin((0.0, 0.0, 0.0))
    return img


def test_resample_isotropic_changes_spacing():
    img = _make_test_image(spacing=(1.0, 1.0, 2.0))
    resampled = resample_isotropic(img, target_spacing=(1.0, 1.0, 1.0))

    assert resampled.GetSpacing() == (1.0, 1.0, 1.0)
    # Z dimension should roughly double since spacing halved
    assert resampled.GetSize()[2] >= img.GetSize()[2] * 1.8


def test_resample_isotropic_preserves_origin():
    img = _make_test_image(spacing=(0.5, 0.5, 1.0))
    img.SetOrigin((10.0, 20.0, 30.0))
    resampled = resample_isotropic(img, target_spacing=(0.7, 0.7, 0.7))

    assert resampled.GetOrigin() == (10.0, 20.0, 30.0)


def test_clip_hu_vascular_window():
    volume = np.array([-500, -100, 0, 400, 700, 1500], dtype=np.float32)
    clipped = clip_hu(volume, window=(-100, 700))

    assert clipped.min() == -100
    assert clipped.max() == 700
    assert clipped[2] == 0  # Unchanged within window


def test_clip_hu_custom_window():
    volume = np.arange(-200, 200, dtype=np.float32)
    clipped = clip_hu(volume, window=(0, 80))
    assert clipped.min() == 0
    assert clipped.max() == 80


def test_normalize_zscore():
    volume = np.random.randn(32, 64, 64).astype(np.float32) * 200 + 400
    normalized = normalize_intensity(volume, method="zscore")

    # Z-score should give roughly zero mean, unit variance
    assert abs(normalized.mean()) < 1.0
    assert abs(normalized.std() - 1.0) < 0.5


def test_normalize_minmax():
    volume = np.random.randn(32, 64, 64).astype(np.float32) * 200 + 400
    normalized = normalize_intensity(volume, method="minmax")

    assert normalized.min() >= 0.0
    assert normalized.max() <= 1.0


def test_normalize_invalid_method():
    volume = np.ones((10, 10, 10), dtype=np.float32)
    try:
        normalize_intensity(volume, method="invalid")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
