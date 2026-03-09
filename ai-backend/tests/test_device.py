"""Tests for GPU-agnostic device detection."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.inference.device import DeviceInfo, detect_device


def test_detect_device_no_torch():
    """Falls back to CPU when PyTorch is not installed."""
    with patch.dict("sys.modules", {"torch": None}):
        # Force reimport
        with patch("builtins.__import__", side_effect=ImportError("No module named 'torch'")):
            info = detect_device()
            assert info.backend == "cpu"
            assert info.device_name == "CPU"


def test_detect_device_cpu_only():
    """Falls back to CPU when no GPU is available."""
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = False
    mock_torch.version.hip = None

    with patch.dict("sys.modules", {"torch": mock_torch}):
        with patch("src.inference.device.torch", mock_torch, create=True):
            info = detect_device()
    assert info.backend == "cpu"


def test_device_info_summary():
    info = DeviceInfo(backend="rocm", device_name="AMD Radeon GPU", device_index=0, vram_mb=8192)
    assert "rocm:0" in info.summary()
    assert "AMD Radeon GPU" in info.summary()
    assert "8192MB" in info.summary()


def test_device_info_summary_no_vram():
    info = DeviceInfo(backend="cpu", device_name="CPU", device_index=0, vram_mb=None)
    assert "cpu:0" in info.summary()
    assert "VRAM" not in info.summary()
