# conftest.py — pytest configuration and shared fixtures
#
# WHY conftest.py?
#   pytest automatically discovers and loads this file before running tests.
#   Fixtures defined here are available to ALL test files without importing them.
#   This is where you set up shared state: test clients, DB connections, mock objects.
#
# WHAT is a fixture?
#   A fixture is a function decorated with @pytest.fixture.
#   pytest injects it into test functions as a parameter.
#   Think of it as "setup code that runs before a test".

import pytest
from fastapi.testclient import TestClient  # wraps FastAPI app for synchronous testing
from app.main import app                   # our FastAPI application
from app import database                   # our in-memory database module


@pytest.fixture
def client():
    """
    Provides a TestClient for each test.
    TestClient lets you make HTTP requests directly to the FastAPI app
    WITHOUT starting an actual server — it calls the app in-process.
    This makes tests FAST (no network overhead).
    """
    yield TestClient(app)   # 'yield' = give the client to the test, then run cleanup

    # Cleanup AFTER each test (everything after yield):
    database.clear_all()    # wipe the database so tests don't affect each other
    # This is critical — tests must be INDEPENDENT. If test A creates a deployment
    # and test B checks "is the list empty?", test B would fail without this cleanup.


@pytest.fixture
def sample_deployment_payload():
    """
    A valid deployment payload reused across tests.
    Why a fixture instead of a dict in each test?
    If the model changes (e.g. we add a required field), we only update this one place.
    """
    return {
        "app_name":    "payment-service",
        "version":     "v2.1.0",
        "environment": "staging",
        "deployed_by": "tejas",
        "notes":       "Sprint 14 release"
    }
