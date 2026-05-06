"""Scraper service for API."""

import logging
import asyncio
from typing import Dict, Any
from pathlib import Path
from functools import partial

from src.scraper import quick_search
from .job_service import JobService

logger = logging.getLogger(__name__)


class ScraperService:
    """Service for scraping jobs."""
    
    def __init__(self):
        self.job_service = JobService()
    
    async def scrape_jobs(
        self,
        user_id: int,
        keyword: str = None,
        location: str = "Canada",
        pages: int = 1,
        job_bank_only: bool = True,
        headless: bool = True
    ) -> Dict[str, Any]:
        """
        Scrape jobs and store in user's database.
        
        Args:
            user_id: User ID
            keyword: Job keyword
            location: Job location
            pages: Number of pages to scrape
            job_bank_only: Only Job Bank postings
            headless: Run browser in headless mode
            
        Returns:
            Dict with scraping results
        """
        try:
            logger.info(f"Scraping jobs for user {user_id}: {keyword} in {location}")
            
            # Get user's database path
            db_path = self.job_service.get_user_db_path(user_id)
            
            # Run scraper in thread pool to avoid blocking async event loop
            # quick_search uses sync_playwright which can't run in async context
            # NOTE: quick_search doesn't accept db_path parameter, so we need to
            # use a wrapper function that creates scraper with correct db_path
            loop = asyncio.get_event_loop()
            
            def run_scraper_with_db():
                from src.scraper import JobBankScraper
                with JobBankScraper(headless=headless, use_database=False) as scraper:
                    # Set user-specific database
                    from src.database import JobBankDB
                    scraper.db = JobBankDB(db_path=str(db_path))
                    # Enable saving to DB now that the user-specific DB is attached
                    scraper.use_database = True
                    return scraper.search_jobs(keyword, location, pages, job_bank_only)
            
            results = await loop.run_in_executor(None, run_scraper_with_db)
            
            # Get statistics
            stats = self.job_service.get_stats(user_id)
            
            return {
                "success": True,
                "message": f"Scraped {len(results)} jobs",
                "jobs_found": len(results),
                "jobs_new": stats.get('unposted_jobs', 0),
                "jobs_updated": 0,
                "stats": stats
            }
            
        except Exception as e:
            logger.error(f"Error scraping jobs: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "jobs_found": 0,
                "jobs_new": 0,
                "jobs_updated": 0
            }
