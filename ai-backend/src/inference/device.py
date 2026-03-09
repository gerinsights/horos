"""GPU-agnostic device detection and selection.

Supports ROCm (AMD), CUDA (NVIDIA), and CPU fallback.
PyTorch uses the same `cuda` device API for both CUDA and ROCm builds.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    backend: str  # "rocm", "cuda", "cpu"
    device_name: str
    device_index: int
    vram_mb: int | None

    def summary(self) -> str:
        vram = f", {self.vram_mb}MB VRAM" if self.vram_mb else ""
        return f"{self.backend}:{self.device_index} ({self.device_name}{vram})"


def detect_device() -> DeviceInfo:
    """Detect the best available compute device.

    Detection order: ROCm/CUDA GPU → CPU.
    PyTorch ROCm builds report `torch.cuda.is_available() == True`
    and expose ROCm GPUs via the cuda device API.
    """
    try:
        import torch

        if torch.cuda.is_available():
            idx = 0
            name = torch.cuda.get_device_name(idx)
            vram = torch.cuda.get_device_properties(idx).total_mem // (1024 * 1024)

            # Distinguish ROCm from CUDA by checking the torch build
            backend = "rocm" if hasattr(torch.version, "hip") and torch.version.hip else "cuda"

            info = DeviceInfo(
                backend=backend,
                device_name=name,
                device_index=idx,
                vram_mb=vram,
            )
            logger.info("GPU detected: %s", info.summary())
            return info

    except ImportError:
        logger.warning("PyTorch not installed — falling back to CPU")
    except Exception as e:
        logger.warning("GPU detection failed: %s — falling back to CPU", e)

    return DeviceInfo(backend="cpu", device_name="CPU", device_index=0, vram_mb=None)


def get_torch_device() -> "torch.device":
    """Return a torch.device for the best available backend."""
    import torch

    if torch.cuda.is_available():
        return torch.device("cuda", 0)
    return torch.device("cpu")
