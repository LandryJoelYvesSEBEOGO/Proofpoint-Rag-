"""Smoke tests for the project layout: every top-level package must be importable."""

import importlib

import pytest

TOP_LEVEL_PACKAGES = ["api", "workers", "retrieval", "generation", "connectors", "eval"]


@pytest.mark.parametrize("package_name", TOP_LEVEL_PACKAGES)
def test_top_level_package_imports_and_is_documented(package_name: str) -> None:
    module = importlib.import_module(package_name)

    assert module.__doc__, f"{package_name} must have a module docstring"
