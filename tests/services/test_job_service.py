"""
Tests for the job service layer.

Service layer tests verify business logic without HTTP requests.
These are "pure" unit tests - testing one component in isolation.
"""

import pytest
from pathlib import Path
from api.services.job_service import JobService
from src.database import JobBankDB
from src.config import DEFAULT_USER_LIMIT_REQUEST


def test_get_user_db_path(tmp_path, monkeypatch):
    """
    Test that user database paths are created correctly.
    
    Each user should get their own isolated database.
    The path should follow the pattern: data/user_{id}/jobs.db
    """
    monkeypatch.setattr("api.services.job_service.BASE_DIR", tmp_path)
    service = JobService()
    
    user_id = 12345
    db_path = service.get_user_db_path(user_id)
    
    # Check the path contains the user ID
    assert f"user_{user_id}" in str(db_path)
    assert db_path.name == "jobs.db"
    
    # Check the parent directory would be created
    # (actual creation happens when database is opened)
    assert db_path.parent.name == f"user_{user_id}"


def test_get_jobs_from_empty_db(temp_db):
    """
    Test getting jobs from an empty database.
    
    This uses the temp_db fixture from conftest.py.
    The fixture gives us a clean, temporary database for this test.
    """
    service = JobService()
    
    # Override the db path to use our test database
    with JobBankDB(db_path=str(temp_db)) as db:
        pass  # Just create the DB schema
    
    # Now get jobs using the service
    # We need to mock get_user_db_path to return our temp_db
    original_method = service.get_user_db_path
    service.get_user_db_path = lambda user_id: temp_db
    
    result = service.get_jobs(user_id=123)
    
    assert result["total"] == 0
    assert result["jobs"] == []
    assert result["limit"] == DEFAULT_USER_LIMIT_REQUEST
    assert result["offset"] == 0
    
    # Restore original method
    service.get_user_db_path = original_method


def test_get_jobs_with_data(populated_db, sample_jobs):
    """
    Test getting jobs from a populated database.
    
    This uses the populated_db fixture which contains sample_jobs.
    This is fixture composition - reusing fixtures to build complex test scenarios!
    """
    service = JobService()
    
    # Mock the db path method
    service.get_user_db_path = lambda user_id: populated_db
    
    result = service.get_jobs(user_id=123, limit=10)
    
    assert result["total"] == len(sample_jobs)
    assert len(result["jobs"]) == len(sample_jobs)
    
    # Verify job data structure
    first_job = result["jobs"][0]
    assert "job_id" in first_job
    assert "title" in first_job
    assert "company" in first_job


def test_get_jobs_uses_configured_default_limit(populated_db, monkeypatch):
    """
    Test that get_jobs uses the user's configured request limit when omitted.
    """
    service = JobService()
    service.get_user_db_path = lambda user_id: populated_db
    monkeypatch.setattr("api.services.job_service.get_user_limit_request", lambda user_id: 2)

    result = service.get_jobs(user_id=123)

    assert result["limit"] == 2
    assert len(result["jobs"]) == 2


def test_get_unposted_jobs_filters_recent_posted_dates(temp_db):
    """Older unposted jobs should not be returned when recent_days is set."""
    service = JobService()
    service.get_user_db_path = lambda user_id: temp_db

    with JobBankDB(db_path=str(temp_db)) as db:
        db.add_job({
            "job_id": "recent-job",
            "title": "Recent Data Analyst",
            "company": "Data Inc",
            "location": "Vancouver, BC",
            "salary": "$80,000",
            "job_type": "Full-time",
            "date_posted": "May 01, 2026",
            "url": "https://jobbank.gc.ca/job/recent",
            "source": "Job Bank",
        })
        db.add_job({
            "job_id": "old-job",
            "title": "Old Data Analyst",
            "company": "Old Inc",
            "location": "Vancouver, BC",
            "salary": "$80,000",
            "job_type": "Full-time",
            "date_posted": "February 20, 2026",
            "url": "https://jobbank.gc.ca/job/old",
            "source": "Job Bank",
        })

    result = service.get_jobs(user_id=123, unposted_only=True, recent_days=30)
    job_ids = {job["job_id"] for job in result["jobs"]}

    assert job_ids == {"recent-job"}


def test_database_normalizes_job_id_before_duplicate_check(temp_db):
    """The same Job Bank posting should not be duplicated by URL query params."""
    base_job = {
        "job_id": "49405461",
        "title": "Software Developer",
        "company": "Jarvis Consulting Group",
        "location": "Toronto, ON",
        "salary": "$50.00 hourly",
        "job_type": "Full-time",
        "date_posted": "April 27, 2026",
        "url": "https://www.jobbank.gc.ca/jobsearch/jobposting/49405461",
        "source": "Job Bank",
    }

    with JobBankDB(db_path=str(temp_db)) as db:
        assert db.add_job(base_job.copy()) is True

        duplicate = base_job.copy()
        duplicate["job_id"] = "49405461?source=searchresults"
        duplicate["url"] = "https://www.jobbank.gc.ca/jobsearch/jobposting/49405461?source=searchresults"

        assert db.add_job(duplicate) is False
        jobs = db.get_all_jobs()

    assert len(jobs) == 1
    assert jobs[0]["job_id"] == "49405461"


def test_get_jobs_with_keyword_filter(populated_db):
    """
    Test filtering jobs by keyword.
    
    This tests that search functionality works correctly.
    """
    service = JobService()
    service.get_user_db_path = lambda user_id: populated_db
    
    # Search for "engineer" - should match "Software Engineer" and "ML Engineer"
    result = service.get_jobs(user_id=123, keyword="engineer")
    
    assert result["total"] >= 2  # At least 2 jobs should match
    
    # Verify results contain the keyword
    for job in result["jobs"]:
        title_lower = job["title"].lower()
        assert "engineer" in title_lower


def test_get_jobs_with_location_filter(populated_db):
    """
    Test filtering jobs by location.
    """
    service = JobService()
    service.get_user_db_path = lambda user_id: populated_db
    
    result = service.get_jobs(user_id=123, location="Toronto")
    
    # Should only return Toronto jobs
    for job in result["jobs"]:
        assert "Toronto" in job["location"]


def test_get_jobs_with_pagination(populated_db, sample_jobs):
    """
    Test pagination works correctly.
    
    Pagination is splitting results into pages.
    This tests offset and limit parameters.
    """
    service = JobService()
    service.get_user_db_path = lambda user_id: populated_db
    
    # Get first page (limit=2)
    page1 = service.get_jobs(user_id=123, limit=2, offset=0)
    assert len(page1["jobs"]) == 2
    assert page1["offset"] == 0
    
    # Get second page (limit=2, offset=2)
    page2 = service.get_jobs(user_id=123, limit=2, offset=2)
    assert len(page2["jobs"]) <= 2  # Might be 0 or 1 depending on total
    assert page2["offset"] == 2
    
    # Jobs on different pages should be different
    if len(page2["jobs"]) > 0:
        page1_ids = [j["job_id"] for j in page1["jobs"]]
        page2_ids = [j["job_id"] for j in page2["jobs"]]
        assert page1_ids[0] != page2_ids[0]


def test_get_job_by_id(populated_db):
    """
    Test retrieving a specific job by its ID.
    """
    service = JobService()
    service.get_user_db_path = lambda user_id: populated_db
    
    # Get a job that exists
    job = service.get_job_by_id(user_id=123, job_id="test-job-1")
    
    assert job is not None
    assert job["job_id"] == "test-job-1"
    assert "title" in job
    
    # Try to get a job that doesn't exist
    missing_job = service.get_job_by_id(user_id=123, job_id="nonexistent")
    assert missing_job is None


def test_mark_as_posted(populated_db):
    """
    Test marking jobs as posted.
    
    This is critical for tracking which jobs have been sent to Telegram.
    """
    service = JobService()
    service.get_user_db_path = lambda user_id: populated_db
    
    job_ids = ["test-job-1", "test-job-2"]
    message_ids = [100, 101]
    
    # Mark jobs as posted
    count = service.mark_as_posted(
        user_id=123,
        job_ids=job_ids,
        message_ids=message_ids
    )
    
    assert count == 2
    
    # Verify they're marked in database
    with JobBankDB(db_path=str(populated_db)) as db:
        job1 = db.get_job("test-job-1")
        assert job1["posted_to_telegram"] == 1
        assert job1["telegram_message_id"] == 100


def test_get_stats(populated_db, sample_jobs):
    """
    Test getting database statistics.
    
    Stats help users understand their job database.
    """
    service = JobService()
    service.get_user_db_path = lambda user_id: populated_db
    
    stats = service.get_stats(user_id=123)
    
    # Check all expected stats exist
    assert "total_jobs" in stats
    assert "unposted_jobs" in stats
    assert "posted_jobs" in stats
    assert "sources" in stats
    
    # Check stats make sense
    assert stats["total_jobs"] == len(sample_jobs)
    assert stats["unposted_jobs"] >= 0
    assert stats["posted_jobs"] >= 0
    
    # Sources should be a dictionary
    assert isinstance(stats["sources"], dict)


def test_delete_job(populated_db):
    """
    Test deleting a job from database.
    """
    service = JobService()
    service.get_user_db_path = lambda user_id: populated_db
    
    # Delete an existing job
    success = service.delete_job(user_id=123, job_id="test-job-1")
    assert success is True
    
    # Verify it's gone
    job = service.get_job_by_id(user_id=123, job_id="test-job-1")
    assert job is None
    
    # Try to delete a non-existent job
    success = service.delete_job(user_id=123, job_id="nonexistent")
    assert success is False
