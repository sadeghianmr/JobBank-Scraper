"""Fixtures for integration tests."""

import pytest
import shutil
from pathlib import Path
from fastapi.testclient import TestClient

from api.main import app
from src.config import BASE_DIR


@pytest.fixture(scope="module")
def client():
    """
    Create a test client for the API.
    
    Uses the REAL API with all real components.
    """
    return TestClient(app)


@pytest.fixture(scope="function")
def test_user_id():
    """
    Provide a test user ID.
    
    Uses a unique ID for each test to avoid conflicts.
    """
    return 99999  # High number to avoid conflicts with real users


@pytest.fixture(scope="function")
def cleanup_test_db(test_user_id):
    """
    Clean up test user's database after each test.
    
    Yields before test, cleans up after.
    """
    yield
    
    # Cleanup: Remove test user's database after test
    test_db_dir = BASE_DIR / "data" / f"user_{test_user_id}"
    if test_db_dir.exists():
        shutil.rmtree(test_db_dir)
        print(f"\n✓ Cleaned up test database: {test_db_dir}")
