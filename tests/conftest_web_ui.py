"""
Pytest configuration for Web UI tests.

This file provides shared fixtures and configuration for web UI testing.
Copy or import into conftest.py if needed.
"""

import os
import pytest

# Test environment configuration
UBUNTU1_HOST = os.getenv("UBUNTU1_HOST", "10.0.4.130")
UBUNTU2_HOST = os.getenv("UBUNTU2_HOST", "10.0.4.140")


def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addoption(
        "--offline",
        action="store_true",
        default=False,
        help="Run tests in offline mode (skip integration tests)",
    )
    parser.addoption(
        "--ubuntu1-host",
        action="store",
        default=UBUNTU1_HOST,
        help="Ubuntu 1 host IP (Media Mover)",
    )
    parser.addoption(
        "--ubuntu2-host",
        action="store",
        default=UBUNTU2_HOST,
        help="Ubuntu 2 host IP (Gateway)",
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests when running offline."""
    if config.getoption("--offline"):
        skip_integration = pytest.mark.skip(reason="Skipped in offline mode")
        for item in items:
            if "integration" in item.keywords or "e2e" in item.keywords:
                item.add_marker(skip_integration)


@pytest.fixture(scope="session")
def ubuntu1_host(request):
    """Get Ubuntu 1 host from command line or environment."""
    return request.config.getoption("--ubuntu1-host")


@pytest.fixture(scope="session")
def ubuntu2_host(request):
    """Get Ubuntu 2 host from command line or environment."""
    return request.config.getoption("--ubuntu2-host")


@pytest.fixture(scope="session")
def gateway_url(ubuntu2_host):
    """Build Gateway URL from host."""
    return f"http://{ubuntu2_host}:8000"


@pytest.fixture(scope="session")
def media_mover_url(ubuntu1_host):
    """Build Media Mover URL from host."""
    return f"http://{ubuntu1_host}:8083/api"


@pytest.fixture(scope="session")
def thumbs_url(ubuntu1_host):
    """Build thumbnails URL from host."""
    return f"http://{ubuntu1_host}/thumbs"
