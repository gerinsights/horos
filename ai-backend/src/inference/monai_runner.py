"""MONAI model inference wrapper (M1/M3 implementation)."""

from __future__ import annotations


class MONAIRunner:
    """Wrapper for MONAI model inference.

    Loads and runs MONAI-based 3D segmentation models.
    GPU-agnostic: works with ROCm, CUDA, or CPU via PyTorch.
    To be implemented in M1/M3.
    """

    def __init__(self, model_path: str):
        self.model_path = model_path

    async def predict(self, volume, spacing):
        raise NotImplementedError("MONAI inference not yet implemented")
