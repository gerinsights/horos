"""MONAI model inference wrapper."""

from __future__ import annotations


class MONAIRunner:
    """Wrapper for MONAI model inference.

    Loads and runs MONAI-based 3D segmentation models.
    GPU-agnostic: works with ROCm, CUDA, or CPU via PyTorch.
    """

    def __init__(self, model_path: str):
        self.model_path = model_path

    async def predict(self, volume, spacing):
        raise NotImplementedError("MONAI inference not yet implemented")
