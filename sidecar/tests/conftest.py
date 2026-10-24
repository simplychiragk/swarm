"""
Global pytest configuration for Swarm unit tests.
Ensures test suite executes in deterministic mock mode without consuming live API tokens.
"""

import os
import pytest


@pytest.fixture(autouse=True)
def default_test_environment(monkeypatch):
    """Enforces mock isolation for all unit test runs."""
    monkeypatch.setenv("SWARM_MODE", "mock")
    monkeypatch.setenv("SWARM_LLM_MODE", "mock")
