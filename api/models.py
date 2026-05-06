"""Pydantic models for API."""

from typing import List, Optional
from pydantic import BaseModel, Field

from src.config import MAX_USER_LIMIT_REQUEST, MIN_USER_LIMIT_REQUEST


class ScrapeRequest(BaseModel):
    """Request model for scraping jobs."""
    user_id: int
    keyword: str = Field(..., min_length=1, description="Job keyword (required)")
    location: str = Field(default="Canada", min_length=1)
    pages: int = Field(default=1, ge=1, le=1000)
    job_bank_only: bool = True
    headless: bool = True


class JobFilter(BaseModel):
    """Filter model for querying jobs."""
    user_id: int
    keyword: Optional[str] = None
    location: Optional[str] = None
    min_salary: Optional[int] = None
    source: Optional[str] = None
    limit: Optional[int] = Field(default=None, ge=MIN_USER_LIMIT_REQUEST, le=MAX_USER_LIMIT_REQUEST)
    offset: int = Field(default=0, ge=0)
    posted_only: bool = False
    unposted_only: bool = False


class Job(BaseModel):
    """Job model."""
    id: Optional[int] = None
    job_id: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    salary: Optional[str] = None
    job_type: Optional[str] = None
    date_posted: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    scraped_at: Optional[str] = None
    is_active: bool = True
    posted_to_telegram: bool = False
    telegram_message_id: Optional[int] = None


class JobsResponse(BaseModel):
    """Response model for jobs list."""
    total: int
    jobs: List[Job]
    limit: int
    offset: int


class ScrapeResponse(BaseModel):
    """Response model for scrape operation."""
    success: bool
    message: str
    jobs_found: int
    jobs_new: int
    jobs_updated: int


class MarkPostedRequest(BaseModel):
    """Request to mark jobs as posted."""
    user_id: int
    job_ids: List[str]
    message_ids: Optional[List[int]] = None


class StatsResponse(BaseModel):
    """Statistics response."""
    total_jobs: int
    unposted_jobs: int
    posted_jobs: int
    sources: dict
