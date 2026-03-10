"""Tests for pipeline routing and execution."""

from __future__ import annotations

import pytest

from src.pipeline.cta import CTAPipeline
from src.pipeline.mri import MRIPipeline
from src.pipeline.router import PIPELINES


def test_pipelines_registered():
    assert "cta" in PIPELINES
    assert "mri" in PIPELINES


def test_cta_pipeline_name():
    p = CTAPipeline()
    assert p.name == "cta"


def test_mri_pipeline_name():
    p = MRIPipeline()
    assert p.name == "mri"


@pytest.mark.asyncio
async def test_cta_pipeline_returns_empty():
    """CTA pipeline returns empty results in M0 scaffold."""
    p = CTAPipeline()
    results = await p.run("test-study-id")
    assert results == []


@pytest.mark.asyncio
async def test_mri_pipeline_returns_empty():
    """MRI pipeline returns empty results in M0 scaffold."""
    p = MRIPipeline()
    results = await p.run("test-study-id")
    assert results == []
