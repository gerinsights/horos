"""Model discovery and loading registry."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Discovers and manages available AI models."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    def list_models(self) -> dict[str, dict]:
        """List all models found in the models directory."""
        models = {}

        # Check nnUNet models
        nnunet_dir = self.base_path / "nnunet"
        if nnunet_dir.exists():
            for model_dir in nnunet_dir.iterdir():
                if model_dir.is_dir():
                    has_checkpoint = any(model_dir.rglob("*.pth"))
                    models[model_dir.name] = {
                        "framework": "nnunet",
                        "path": str(model_dir),
                        "ready": has_checkpoint,
                    }

        # Check MONAI models
        monai_dir = self.base_path / "monai"
        if monai_dir.exists():
            for model_dir in monai_dir.iterdir():
                if model_dir.is_dir():
                    has_weights = any(model_dir.rglob("*.pt"))
                    models[model_dir.name] = {
                        "framework": "monai",
                        "path": str(model_dir),
                        "ready": has_weights,
                    }

        return models

    def is_model_ready(self, model_name: str) -> bool:
        """Check if a model has downloaded weights."""
        models = self.list_models()
        return models.get(model_name, {}).get("ready", False)
