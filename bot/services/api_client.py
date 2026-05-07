"""
API Client for JobBank Bot.

This module provides an HTTP client for the Telegram bot to communicate
with the FastAPI backend. Instead of directly accessing the database,
the bot makes HTTP requests to the API.

Why use an API client?
- Separation of concerns: Bot handles UI, API handles data
- Scalability: Multiple bots can share one API
- Maintainability: Changes to database logic don't affect bot
- Testing: Easy to mock API responses
"""

import httpx
import logging
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class JobBankAPI:
    """
    Client for communicating with JobBank FastAPI backend.
    
    This class wraps HTTP requests to the API and provides clean methods
    for the bot to use. It handles:
    - Request formatting
    - Error handling
    - Response parsing
    """
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout_seconds: Optional[float] = None):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL of the FastAPI server (default: http://localhost:8000)
            timeout_seconds: HTTP timeout for API calls
        """
        self.base_url = base_url.rstrip("/")
        if timeout_seconds is None:
            timeout_seconds = self._get_timeout_from_env()

        self.client = httpx.Client(timeout=timeout_seconds)
        logger.info(
            f"API client initialized with base URL: {self.base_url}, "
            f"timeout={timeout_seconds}s"
        )

    def _get_timeout_from_env(self) -> float:
        """Read API timeout from environment, falling back to a scraper-friendly default."""
        try:
            return float(os.getenv("API_REQUEST_TIMEOUT_SECONDS", "300"))
        except ValueError:
            return 300.0
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """
        Handle API response and check for errors.
        
        This centralizes error handling so we don't repeat it everywhere.
        
        Args:
            response: HTTP response from API
            
        Returns:
            Parsed JSON response
            
        Raises:
            Exception: If API returns an error
        """
        try:
            response.raise_for_status()  # Raises exception for 4xx/5xx status codes
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
    
    # ===========================================
    # Scraper Endpoints
    # ===========================================
    
    def scrape_jobs(
        self,
        user_id: int,
        keyword: str,
        location: str = "Canada",
        pages: int = 1,
        job_bank_only: bool = True,
        headless: bool = True
    ) -> Dict[str, Any]:
        """
        Scrape jobs and store in user's database.
        
        This triggers the scraper to fetch new jobs from Job Bank website.
        
        Args:
            user_id: User ID
            keyword: Job search keyword
            location: Search location
            pages: Number of pages to scrape
            job_bank_only: Only Job Bank postings (exclude Indeed, etc.)
            headless: Run browser in headless mode
            
        Returns:
            Dict with scraping results: {success, message, jobs_found, jobs_new, stats}
        """
        logger.info(f"Scraping jobs for user {user_id}: {keyword} in {location}")
        
        url = f"{self.base_url}/api/v1/scraper/scrape"
        payload = {
            "user_id": user_id,
            "keyword": keyword,
            "location": location,
            "pages": pages,
            "job_bank_only": job_bank_only,
            "headless": headless
        }
        
        response = self.client.post(url, json=payload)
        return self._handle_response(response)
    
    # ===========================================
    # Jobs Endpoints
    # ===========================================
    
    def get_unposted_jobs(
        self,
        user_id: int,
        job_bank_only: bool = True,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """
        Get jobs that haven't been posted to Telegram yet.
        
        This is used by the scheduler to find new jobs to post.
        
        Args:
            user_id: User ID
            job_bank_only: Filter to only Job Bank postings
            limit: Maximum jobs to return (None = use user config default)
            
        Returns:
            List of job dictionaries
        """
        url = f"{self.base_url}/api/v1/jobs/{user_id}"
        params = {
            "unposted_only": True
        }
        if limit is not None:
            params["limit"] = limit
        if job_bank_only:
            params["source"] = "Job Bank"
        
        response = self.client.get(url, params=params)
        data = self._handle_response(response)
        return data.get("jobs", [])
    
    def search_jobs(
        self,
        user_id: int,
        keyword: Optional[str] = None,
        location: Optional[str] = None,
        min_salary: Optional[int] = None,
        limit: int = None,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search jobs in user's database.
        
        Used for the "Search Database" feature where users can
        query their stored jobs.
        
        Args:
            user_id: User ID
            keyword: Search keyword (searches title and company)
            location: Filter by location
            min_salary: Minimum salary filter
            limit: Max results
            offset: Offset for pagination
            
        Returns:
            Dict with: {total, jobs, limit, offset}
        """
        url = f"{self.base_url}/api/v1/jobs/{user_id}"
        params = {
            "offset": offset
        }
        if limit is not None:
            params["limit"] = limit
        if keyword:
            params["keyword"] = keyword
        if location:
            params["location"] = location
        if min_salary:
            params["min_salary"] = min_salary
        
        response = self.client.get(url, params=params)
        return self._handle_response(response)
    
    def mark_jobs_as_posted(
        self,
        user_id: int,
        job_ids: List[str],
        message_ids: Optional[List[int]] = None
    ) -> bool:
        """
        Mark jobs as posted to Telegram.
        
        This prevents the bot from posting the same job twice.
        
        Args:
            user_id: User ID
            job_ids: List of job IDs to mark
            message_ids: Telegram message IDs (optional)
            
        Returns:
            True if successful
        """
        url = f"{self.base_url}/api/v1/jobs/mark-posted"
        payload = {
            "user_id": user_id,
            "job_ids": job_ids
        }
        if message_ids:
            payload["message_ids"] = message_ids
        
        response = self.client.post(url, json=payload)
        data = self._handle_response(response)
        return data.get("success", False)
    
    def get_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get statistics for user's job database.
        
        Shows total jobs, posted/unposted counts, job sources, etc.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with: {total_jobs, unposted_jobs, posted_jobs, sources}
        """
        url = f"{self.base_url}/api/v1/jobs/{user_id}/stats"
        response = self.client.get(url)
        return self._handle_response(response)
    
    # ===========================================
    # Health Check
    # ===========================================
    
    def health_check(self) -> bool:
        """
        Check if API server is running.
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            url = f"{self.base_url}/health"
            response = self.client.get(url, timeout=5.0)
            data = response.json()
            return data.get("status") == "healthy"
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def close(self):
        """Close the HTTP client connection."""
        self.client.close()
    
    def __enter__(self):
        """Context manager support."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.close()


# ===========================================
# Usage Example
# ===========================================
if __name__ == "__main__":
    # Example usage of the API client
    with JobBankAPI() as api:
        # Check if API is running
        if api.health_check():
            print("✓ API is healthy")
            
            # Get stats for user
            stats = api.get_stats(user_id=123)
            print(f"Total jobs: {stats['total_jobs']}")
            
            # Get unposted jobs
            jobs = api.get_unposted_jobs(user_id=123, limit=5)
            print(f"Found {len(jobs)} unposted jobs")
        else:
            print("✗ API is not responding")
