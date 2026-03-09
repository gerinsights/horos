"""Preprocessing utilities for CTA/MRI volumes (M1 implementation)."""

from __future__ import annotations


def resample_isotropic(volume, current_spacing, target_spacing=(0.7, 0.7, 0.7)):
    """Resample volume to isotropic spacing using SimpleITK."""
    raise NotImplementedError("Resampling not yet implemented")


def clip_hu(volume, window=(-100, 700)):
    """Clip Hounsfield Units to a vascular window for CTA."""
    raise NotImplementedError("HU clipping not yet implemented")


def normalize_intensity(volume, method="zscore"):
    """Normalize volume intensity (z-score or min-max)."""
    raise NotImplementedError("Intensity normalization not yet implemented")
