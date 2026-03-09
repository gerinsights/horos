"""nnUNet v2 inference wrapper (M1 implementation)."""

from __future__ import annotations


class NNUNetRunner:
    """Wrapper for nnUNet v2 inference.

    Uses nnUNetv2's predictor API to run 3D segmentation.
    GPU-agnostic: works with ROCm, CUDA, or CPU via PyTorch.
    To be implemented in M1.
    """

    def __init__(self, model_path: str, task_id: str):
        self.model_path = model_path
        self.task_id = task_id

    async def predict(self, volume, spacing):
        raise NotImplementedError("nnUNet inference not yet implemented")
