"""Configuration loader for the DICOM segmentation backend."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class DicomNodeConfig(BaseModel):
    ae_title: str
    host: str = "localhost"
    port: int = 4242


class OrthancConfig(BaseModel):
    url: str = "http://localhost:8042"
    username: str = "orthanc"
    password: str = "orthanc"


class ModelConfig(BaseModel):
    framework: str  # nnunet | monai
    model_path: str
    task_id: str | None = None
    description: str = ""


class PipelineConfig(BaseModel):
    enabled: bool = False
    models: list[str] = []
    output_formats: list[str] = ["dicom_seg", "secondary_capture"]


class RoutingRule(BaseModel):
    modality: str
    body_part: list[str] = []
    description_contains: list[str] = []


class Settings(BaseSettings):
    config_path: str = os.getenv("CONFIG_PATH", "config/settings.yaml")
    orthanc_url: str = "http://localhost:8042"
    pacs_ae: str = "PACS"
    pacs_host: str = "localhost"
    pacs_port: int = 4242

    # Populated from YAML
    dicom: dict[str, DicomNodeConfig] = {}
    orthanc: OrthancConfig = OrthancConfig()
    models: dict[str, ModelConfig] = {}
    models_base_path: str = "/app/models"
    pipelines: dict[str, PipelineConfig] = {}
    routing: dict[str, RoutingRule] = {}

    model_config = {"env_prefix": "", "extra": "ignore"}


def load_settings(config_path: str | None = None) -> Settings:
    """Load settings from YAML config file merged with environment variables."""
    path = Path(config_path or os.getenv("CONFIG_PATH", "config/settings.yaml"))

    yaml_data: dict[str, Any] = {}
    if path.exists():
        with open(path) as f:
            yaml_data = yaml.safe_load(f) or {}

    settings = Settings()

    # Parse DICOM nodes
    dicom_raw = yaml_data.get("dicom", {})
    for name, node_data in dicom_raw.items():
        if isinstance(node_data, dict):
            settings.dicom[name] = DicomNodeConfig(**node_data)

    # Parse Orthanc config
    orthanc_raw = yaml_data.get("orthanc", {})
    if orthanc_raw:
        settings.orthanc = OrthancConfig(**orthanc_raw)

    # Parse models
    models_raw = yaml_data.get("models", {})
    settings.models_base_path = models_raw.pop("base_path", settings.models_base_path)
    for name, model_data in models_raw.items():
        if isinstance(model_data, dict):
            settings.models[name] = ModelConfig(**model_data)

    # Parse pipelines
    pipelines_raw = yaml_data.get("pipelines", {})
    for name, pipe_data in pipelines_raw.items():
        if isinstance(pipe_data, dict):
            settings.pipelines[name] = PipelineConfig(**pipe_data)

    # Parse routing rules
    routing_raw = yaml_data.get("routing", {})
    for name, rule_data in routing_raw.items():
        if isinstance(rule_data, dict):
            settings.routing[name] = RoutingRule(**rule_data)

    return settings
