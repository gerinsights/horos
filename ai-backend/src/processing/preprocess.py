"""Preprocessing utilities for CTA/MRI volumes."""

from __future__ import annotations

import numpy as np
import SimpleITK as sitk


def resample_isotropic(
    image: sitk.Image,
    target_spacing: tuple[float, float, float] = (0.7, 0.7, 0.7),
    interpolator=sitk.sitkLinear,
) -> sitk.Image:
    """Resample a SimpleITK image to isotropic spacing.

    Args:
        image: Input SimpleITK image.
        target_spacing: Target voxel spacing in mm (x, y, z).
        interpolator: SimpleITK interpolator (Linear for images, NearestNeighbor for masks).

    Returns:
        Resampled SimpleITK image.
    """
    original_spacing = image.GetSpacing()
    original_size = image.GetSize()

    new_size = [
        int(round(osz * ospc / tspc))
        for osz, ospc, tspc in zip(original_size, original_spacing, target_spacing)
    ]

    resampler = sitk.ResampleImageFilter()
    resampler.SetOutputSpacing(target_spacing)
    resampler.SetSize(new_size)
    resampler.SetOutputDirection(image.GetDirection())
    resampler.SetOutputOrigin(image.GetOrigin())
    resampler.SetTransform(sitk.Transform())
    resampler.SetInterpolator(interpolator)
    resampler.SetDefaultPixelValue(float(sitk.GetArrayViewFromImage(image).min()))

    return resampler.Execute(image)


def clip_hu(volume: np.ndarray, window: tuple[float, float] = (-100, 700)) -> np.ndarray:
    """Clip Hounsfield Units to a window range.

    Args:
        volume: 3D numpy array of HU values.
        window: (min_hu, max_hu) clipping range.
            CTA vascular: (-100, 700)
            Brain soft tissue: (0, 80)
            Bone: (-100, 2000)

    Returns:
        Clipped volume.
    """
    return np.clip(volume, window[0], window[1])


def normalize_intensity(
    volume: np.ndarray,
    method: str = "zscore",
    percentiles: tuple[float, float] = (0.5, 99.5),
) -> np.ndarray:
    """Normalize volume intensity.

    Args:
        volume: 3D numpy array.
        method: "zscore" (zero mean, unit variance) or "minmax" (scale to [0, 1]).
        percentiles: For "minmax", clip to these percentiles first to handle outliers.

    Returns:
        Normalized volume as float32.
    """
    volume = volume.astype(np.float32)

    if method == "zscore":
        # Compute stats on non-background voxels (> -900 HU for CT)
        foreground = volume[volume > -900] if volume.min() < -500 else volume.ravel()
        if foreground.size == 0:
            foreground = volume.ravel()
        mean = foreground.mean()
        std = foreground.std()
        if std < 1e-8:
            return volume - mean
        return (volume - mean) / std

    elif method == "minmax":
        p_low, p_high = np.percentile(volume, percentiles)
        volume = np.clip(volume, p_low, p_high)
        denom = p_high - p_low
        if denom < 1e-8:
            return np.zeros_like(volume)
        return (volume - p_low) / denom

    else:
        raise ValueError(f"Unknown normalization method: {method}")


def bias_field_correction(image: sitk.Image, shrink_factor: int = 4) -> sitk.Image:
    """N4 bias field correction for MRI volumes.

    Args:
        image: Input SimpleITK image (MRI).
        shrink_factor: Downsample factor for speed (4 is typical).

    Returns:
        Bias-corrected image.
    """
    input_image = sitk.Cast(image, sitk.sitkFloat32)

    # Shrink for speed
    shrunk = sitk.Shrink(input_image, [shrink_factor] * input_image.GetDimension())

    # Create mask (non-zero voxels)
    mask = sitk.OtsuThreshold(shrunk, 0, 1, 200)

    corrector = sitk.N4BiasFieldCorrectionImageFilter()
    corrector.SetMaximumNumberOfIterations([50, 50, 30, 20])

    corrector.Execute(shrunk, mask)

    # Apply correction at full resolution
    log_bias_field = corrector.GetLogBiasFieldAsImage(input_image)
    corrected = input_image / sitk.Exp(log_bias_field)

    return corrected
