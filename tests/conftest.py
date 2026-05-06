"""
Pytest configuration and shared fixtures.

Fixtures are reusable test components that set up and tear down test environments.
They help avoid code duplication in tests.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient

from api.main import app
from src.database import JobBankDB


@pytest.fixture
def client():
    """
    Create a test client for the FastAPI app.
    
    This allows us to make HTTP requests to our API without running a server.
    It's like having a mini browser that talks to your API.
    
    Usage in tests:
        def test_something(client):
            response = client.get("/health")
            assert response.status_code == 200
    """
    return TestClient(app)


@pytest.fixture
def temp_db():
    """
    Create a temporary test database that gets deleted after the test.
    
    This ensures tests don't interfere with each other or with production data.
    Each test gets a fresh, empty database.
    
    Usage:
        def test_something(temp_db):
            # temp_db is a path to a temporary database
            db = JobBankDB(db_path=str(temp_db))
            # ... test database operations
    """
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_jobs.db"
    
    # Yield the database path to the test
    yield db_path
    
    # Cleanup after test completes
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_jobs():
    """
    Provide sample job data for testing.
    
    This is test data that mimics real job postings.
    Using fixtures for test data makes tests more readable.
    """
    return [
        {
            "job_id": "test-job-1",
            "title": "Software Engineer",
            "company": "Tech Corp",
            "location": "Toronto, ON",
            "salary": "$80,000 - $100,000",
            "job_type": "Full-time",
            "date_posted": "2026-02-20",
            "url": "https://jobbank.gc.ca/job/1",
            "source": "Job Bank"
        },
        {
            "job_id": "test-job-2",
            "title": "Data Scientist",
            "company": "Data Inc",
            "location": "Vancouver, BC",
            "salary": "$90,000 - $120,000",
            "job_type": "Full-time",
            "date_posted": "2026-02-21",
            "url": "https://jobbank.gc.ca/job/2",
            "source": "Job Bank"
        },
        {
            "job_id": "test-job-3",
            "title": "Machine Learning Engineer",
            "company": "AI Solutions",
            "location": "Montreal, QC",
            "salary": "$100,000+",
            "job_type": "Contract",
            "date_posted": "2026-02-22",
            "url": "https://jobbank.gc.ca/job/3",
            "source": "Indeed"
        }
    ]


@pytest.fixture
def populated_db(temp_db, sample_jobs):
    """
    Create a test database pre-populated with sample jobs.
    
    This combines temp_db and sample_jobs fixtures to give you
    a ready-to-use database with test data.
    
    Composition of fixtures is a powerful pytest feature!
    """
    with JobBankDB(db_path=str(temp_db)) as db:
        for job in sample_jobs:
            db.add_job(job)
    
    return temp_db
