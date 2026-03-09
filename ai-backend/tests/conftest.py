"""Shared test fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """FastAPI test client."""
    from src.main import app

    with TestClient(app) as c:
        yield c
