"""Post-processing utilities for segmentation masks."""

from __future__ import annotations

import numpy as np
from scipy import ndimage
from skimage import measure


def threshold_mask(probability_map: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    """Convert probability map to binary mask.

    Args:
        probability_map: 3D array of probabilities in [0, 1].
        threshold: Classification threshold.

    Returns:
        Binary mask (uint8, values 0 or 1).
    """
    return (probability_map >= threshold).astype(np.uint8)


def connected_components(mask: np.ndarray, min_size: int = 100) -> np.ndarray:
    """Remove small connected components from a binary mask.

    Args:
        mask: 3D binary mask (0/1).
        min_size: Minimum voxel count to keep a component.

    Returns:
        Cleaned binary mask.
    """
    labeled, num_features = ndimage.label(mask)
    if num_features == 0:
        return mask

    sizes = ndimage.sum(mask, labeled, range(1, num_features + 1))
    keep = np.array([s >= min_size for s in sizes])

    cleaned = np.zeros_like(mask)
    for i, should_keep in enumerate(keep):
        if should_keep:
            cleaned[labeled == (i + 1)] = 1

    return cleaned


def largest_component(mask: np.ndarray) -> np.ndarray:
    """Keep only the largest connected component.

    Args:
        mask: 3D binary mask.

    Returns:
        Mask with only the largest connected component.
    """
    labeled, num_features = ndimage.label(mask)
    if num_features == 0:
        return mask

    sizes = ndimage.sum(mask, labeled, range(1, num_features + 1))
    largest_label = np.argmax(sizes) + 1

    return (labeled == largest_label).astype(np.uint8)


def label_anatomical_regions(
    vessel_mask: np.ndarray,
    spacing: tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> tuple[np.ndarray, dict[int, str]]:
    """Label vessel segments by anatomical region using spatial heuristics.

    Splits the vessel mask into regions based on Z-axis position:
    - Lower third: extracranial (carotid/vertebral)
    - Upper two-thirds: intracranial

    Further splits left/right using the X-axis midline.

    Args:
        vessel_mask: 3D binary vessel mask (D, H, W).
        spacing: Voxel spacing in mm (D, H, W).

    Returns:
        Tuple of (label_map, labels_dict).
        label_map: integer array where each voxel has a region label.
        labels_dict: mapping from label ID to region name.
    """
    labels = {
        1: "Right carotid",
        2: "Left carotid",
        3: "Right vertebral",
        4: "Left vertebral",
        5: "Intracranial arteries",
    }

    label_map = np.zeros_like(vessel_mask, dtype=np.uint8)

    if vessel_mask.sum() == 0:
        return label_map, labels

    coords = np.argwhere(vessel_mask > 0)
    z_min, y_min, x_min = coords.min(axis=0)
    z_max, y_max, x_max = coords.max(axis=0)

    z_range = z_max - z_min + 1
    z_split = z_min + int(z_range * 0.35)

    x_mid = (x_min + x_max) // 2
    y_mid = (y_min + y_max) // 2

    # Intracranial: upper portion
    intra_mask = (vessel_mask > 0) & (np.arange(vessel_mask.shape[0])[:, None, None] >= z_split)
    label_map[intra_mask] = 5

    # Extracranial: lower portion
    extra_mask = (vessel_mask > 0) & (np.arange(vessel_mask.shape[0])[:, None, None] < z_split)

    x_coords = np.arange(vessel_mask.shape[2])[None, None, :]
    y_coords = np.arange(vessel_mask.shape[1])[None, :, None]

    right_mask = x_coords < x_mid
    anterior = y_coords < y_mid

    label_map[extra_mask & right_mask & anterior] = 1   # Right carotid
    label_map[extra_mask & ~right_mask & anterior] = 2   # Left carotid
    label_map[extra_mask & right_mask & ~anterior] = 3   # Right vertebral
    label_map[extra_mask & ~right_mask & ~anterior] = 4  # Left vertebral

    return label_map, labels


def smooth_mask(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    """Morphological smoothing (close then open) to reduce jagged edges.

    Args:
        mask: 3D binary mask.
        iterations: Number of morphological iterations.

    Returns:
        Smoothed binary mask.
    """
    struct = ndimage.generate_binary_structure(3, 1)
    closed = ndimage.binary_closing(mask, structure=struct, iterations=iterations)
    opened = ndimage.binary_opening(closed, structure=struct, iterations=iterations)
    return opened.astype(np.uint8)
