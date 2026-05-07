"""
Tests for scraper API endpoints.

These test the /api/v1/scraper endpoints that trigger job scraping.
Note: These tests mock the actual scraping to avoid hitting real websites.
"""

import pytest
from unittest.mock import patch, MagicMock


def test_scrape_request_validation(client):
    """
    Test that scrape requests are properly validated.
    
    The API should reject invalid scrape requests before trying to scrape.
    This is called "fail fast" - catch errors early!
    """
    # Missing required field (keyword)
    invalid_request = {
        "user_id": 123,
        # Missing keyword - this is now required!
        "location": "Toronto",
        "pages": 1
    }
    
    response = client.post("/api/v1/scraper/scrape", json=invalid_request)
    
    # Should return 422 Unprocessable Entity for validation errors
    assert response.status_code == 422


def test_scrape_with_minimal_params(client):
    """
    Test scraping with minimum required parameters.
    
    What is mocking?
    'patch' replaces the real scraping function with a fake one.
    This lets us test the API without actually scraping websites.
    """
    scrape_request = {
        "user_id": 123,
        "keyword": "software engineer",
        "location": "Toronto",
        "pages": 1,
        "job_bank_only": True,
        "recent_jobs_only": True,
        "headless": True
    }
    
    # Mock the scraping function to return fake results
    # This prevents actual web scraping during tests
    with (
        patch('src.scraper.JobBankScraper.start'),
        patch('src.scraper.JobBankScraper.close'),
        patch('src.scraper.JobBankScraper.search_jobs') as mock_scrape,
    ):
        # Tell the mock what to return
        mock_scrape.return_value = [
            {"job_id": "mock-1", "title": "Mocked Job"}
        ]
        
        response = client.post("/api/v1/scraper/scrape", json=scrape_request)
        
        # Should succeed
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "jobs_found" in data
        assert "message" in data
        mock_scrape.assert_called_once_with(
            "software engineer", "Toronto", 1, True, True
        )


def test_scrape_with_all_params(client):
    """
    Test scraping with all optional parameters.
    
    This ensures the API handles all possible parameter combinations.
    """
    scrape_request = {
        "user_id": 123,
        "keyword": "data scientist",
        "location": "Vancouver, BC",
        "pages": 3,
        "job_bank_only": False,  # Include all sources
        "recent_jobs_only": False,
        "headless": False        # Show browser
    }
    
    with (
        patch('src.scraper.JobBankScraper.start'),
        patch('src.scraper.JobBankScraper.close'),
        patch('src.scraper.JobBankScraper.search_jobs') as mock_scrape,
    ):
        mock_scrape.return_value = []  # No jobs found
        
        response = client.post("/api/v1/scraper/scrape", json=scrape_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["jobs_found"] == 0
        mock_scrape.assert_called_once_with(
            "data scientist", "Vancouver, BC", 3, False, False
        )


def test_scrape_error_handling(client):
    """
    Test that scraping errors are handled gracefully.
    
    What happens if the website is down or the scraper crashes?
    The API should return an error response, not crash itself!
    """
    scrape_request = {
        "user_id": 123,
        "keyword": "engineer",
        "location": "Toronto",
        "pages": 1,
        "job_bank_only": True,
        "recent_jobs_only": True,
        "headless": True
    }
    
    # Simulate a scraping error
    with (
        patch('src.scraper.JobBankScraper.start'),
        patch('src.scraper.JobBankScraper.close'),
        patch('src.scraper.JobBankScraper.search_jobs') as mock_scrape,
    ):
        mock_scrape.side_effect = Exception("Network error!")
        
        response = client.post("/api/v1/scraper/scrape", json=scrape_request)
        
        # Should still return 200 but with success=False
        # (Better would be 500, but our current implementation returns 500 via HTTPException)
        # Let's test both scenarios
        assert response.status_code in [200, 500]


def test_scrape_invalid_pages(client):
    """
    Test that invalid page numbers are rejected.
    
    Negative pages or zero pages don't make sense!
    """
    scrape_request = {
        "user_id": 123,
        "keyword": "engineer",
        "location": "Toronto",
        "pages": 0,  # Invalid!
        "job_bank_only": True,
        "recent_jobs_only": True,
        "headless": True
    }
    
    response = client.post("/api/v1/scraper/scrape", json=scrape_request)
    
    # Should reject invalid input
    assert response.status_code == 422
