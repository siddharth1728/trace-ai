"""Pytest configuration and fixtures for TRACE test suite."""

import os
from pathlib import Path
import pytest

from trace.tools.registry import create_default_registry


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Fixture providing a clean temporary workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


@pytest.fixture
def default_registry(temp_workspace: Path):
    """Fixture providing a default tool registry configured for temp workspace."""
    return create_default_registry(workspace_root=str(temp_workspace))
