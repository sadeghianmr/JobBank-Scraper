"""Scraper API routes."""

from fastapi import APIRouter, HTTPException
from ..models import ScrapeRequest, ScrapeResponse
from ..services.scraper_service import ScraperService

router = APIRouter()
scraper_service = ScraperService()


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_jobs(request: ScrapeRequest):
    """
    Scrape jobs for a user.
    
    Args:
        request: Scrape request with user_id, keyword, location, etc.
        
    Returns:
        Scrape results with statistics
    """
    result = await scraper_service.scrape_jobs(
        user_id=request.user_id,
        keyword=request.keyword,
        location=request.location,
        pages=request.pages,
        job_bank_only=request.job_bank_only,
        headless=request.headless
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    
    return ScrapeResponse(**result)
