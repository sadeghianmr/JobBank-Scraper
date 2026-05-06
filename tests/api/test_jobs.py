"""
Tests for job-related API endpoints.

These test the /api/v1/jobs/* endpoints that handle job retrieval,
filtering, marking as posted, and statistics.
"""

import pytest

from src.config import MAX_USER_LIMIT_REQUEST


def test_get_user_jobs_empty(client):
    """
    Test getting jobs for a user with no jobs in database.
    
    Expected behavior: Should return empty list, not an error.
    This tests graceful handling of empty data.
    """
    response = client.get("/api/v1/jobs/999999")  # User that doesn't exist
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return pagination info even with no jobs
    assert "total" in data
    assert "jobs" in data
    assert data["total"] == 0
    assert data["jobs"] == []


def test_get_user_jobs_with_filters(client):
    """
    Test filtering jobs by keyword, location, etc.
    
    This tests query parameters work correctly.
    Query parameters are the ?key=value parts of URLs.
    """
    response = client.get(
        "/api/v1/jobs/999999",
        params={
            "keyword": "engineer",
            "location": "Toronto",
            "limit": 10,
            "offset": 0
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "total" in data
    assert "jobs" in data
    assert "limit" in data
    assert data["limit"] == 10


def test_get_user_jobs_pagination(client):
    """
    Test pagination parameters.
    
    Pagination is how we split large result sets into pages.
    Like Google search showing 10 results per page.
    """
    # Test different page sizes
    for limit in [5, 10, 20]:
        response = client.get(
            f"/api/v1/jobs/999999?limit={limit}"
        )
        assert response.status_code == 200
        assert response.json()["limit"] == limit


def test_get_user_jobs_invalid_limit(client):
    """
    Test that invalid pagination values are rejected.
    
    The API should validate input and reject bad values.
    This is called "input validation" - critical for security!
    """
    # Limit too large
    response = client.get(f"/api/v1/jobs/999999?limit={MAX_USER_LIMIT_REQUEST + 1}")
    # FastAPI's validation will return 422 (Unprocessable Entity)
    assert response.status_code == 422
    
    # Negative limit
    response = client.get("/api/v1/jobs/999999?limit=-5")
    assert response.status_code == 422


def test_filter_jobs_endpoint(client):
    """
    Test the POST /api/v1/jobs/filter endpoint.
    
    This endpoint accepts complex filter criteria in the request body.
    POST is used when you need to send more complex data than a URL can hold.
    """
    filter_request = {
        "user_id": 999999,
        "filters": {
            "keyword": "machine learning",
            "location": "Canada",
            "min_salary": 80000,
            "limit": 20,
            "offset": 0,
            "unposted_only": True
        }
    }
    
    response = client.post("/api/v1/jobs/filter", json=filter_request)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "total" in data
    assert "jobs" in data
    assert isinstance(data["jobs"], list)


def test_mark_jobs_as_posted(client):
    """
    Test marking jobs as posted to Telegram.
    
    This is how the bot tracks which jobs it has already posted.
    """
    mark_request = {
        "user_id": 999999,
        "job_ids": ["test-job-1", "test-job-2"],
        "message_ids": [12345, 12346]
    }
    
    response = client.post("/api/v1/jobs/mark-posted", json=mark_request)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert "count" in data


def test_mark_jobs_posted_without_message_ids(client):
    """
    Test marking jobs as posted without message IDs.
    
    Sometimes you just want to mark jobs as posted without
    tracking the specific Telegram message ID.
    """
    mark_request = {
        "user_id": 999999,
        "job_ids": ["test-job-1", "test-job-2"]
        # No message_ids provided
    }
    
    response = client.post("/api/v1/jobs/mark-posted", json=mark_request)
    
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_get_user_stats(client):
    """
    Test the statistics endpoint.
    
    Stats are useful for showing users how many jobs they have,
    how many are posted, etc.
    """
    response = client.get("/api/v1/jobs/999999/stats")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check all expected stat fields exist
    assert "total_jobs" in data
    assert "unposted_jobs" in data
    assert "posted_jobs" in data
    assert "sources" in data
    
    # Stats should be numbers
    assert isinstance(data["total_jobs"], int)
    assert isinstance(data["unposted_jobs"], int)
    assert isinstance(data["posted_jobs"], int)


def test_get_specific_job(client):
    """
    Test getting a single job by ID.
    
    This tests the GET /api/v1/jobs/{user_id}/{job_id} endpoint.
    """
    # This will return 404 since job doesn't exist in test DB
    response = client.get("/api/v1/jobs/999999/nonexistent-job")
    
    # Should return 404 Not Found for missing jobs
    assert response.status_code == 404


def test_delete_job(client):
    """
    Test deleting a job.
    
    DELETE operations are important for data management.
    """
    response = client.delete("/api/v1/jobs/999999/test-job-1")
    
    # Should return 404 since job doesn't exist in test DB
    assert response.status_code == 404


def test_invalid_user_id(client):
    """
    Test that invalid user IDs are handled properly.
    
    URLs with non-numeric user_id should be rejected.
    """
    response = client.get("/api/v1/jobs/not-a-number")
    
    # FastAPI will return 422 for invalid path parameters
    assert response.status_code == 422
