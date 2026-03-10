"""Post-processing utilities for segmentation masks (M1 implementation)."""

from __future__ import annotations


def threshold_mask(probability_map, threshold=0.5):
    """Apply threshold to probability map to get binary mask."""
    raise NotImplementedError("Thresholding not yet implemented")


def connected_components(mask, min_size=100):
    """Keep only connected components above minimum size."""
    raise NotImplementedError("Connected components not yet implemented")


def label_anatomical_regions(vessel_mask):
    """Label vessel segments by anatomical region (carotid, vertebral, intracranial)."""
    raise NotImplementedError("Anatomical labeling not yet implemented")
