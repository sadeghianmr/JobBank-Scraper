"""Jobs API routes."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ..models import (
    JobFilter,
    JobsResponse,
    MarkPostedRequest,
    StatsResponse,
    Job
)
from ..services.job_service import JobService
from src.config import MAX_USER_LIMIT_REQUEST, MIN_USER_LIMIT_REQUEST

router = APIRouter()
job_service = JobService()


# Stats route MUST come before /{user_id}/{job_id} to avoid path conflicts
@router.get("/{user_id}/stats", response_model=StatsResponse)
async def get_stats(user_id: int):
    """
    Get statistics for user's jobs.
    
    Args:
        user_id: User ID
        
    Returns:
        Job statistics
    """
    stats = job_service.get_stats(user_id)
    return StatsResponse(**stats)


@router.post("/filter", response_model=JobsResponse)
async def filter_jobs(request: JobFilter):
    """
    Get jobs with filters.
    
    Args:
        request: Job filter request
        
    Returns:
        Filtered jobs with metadata
    """
    result = job_service.get_jobs(
        user_id=request.user_id,
        keyword=request.keyword,
        location=request.location,
        min_salary=request.min_salary,
        source=request.source,
        limit=request.limit,
        offset=request.offset,
        posted_only=request.posted_only,
        unposted_only=request.unposted_only
    )
    
    return JobsResponse(**result)


@router.get("/{user_id}", response_model=JobsResponse)
async def get_user_jobs(
    user_id: int,
    keyword: Optional[str] = None,
    location: Optional[str] = None,
    min_salary: Optional[int] = None,
    source: Optional[str] = None,
    limit: Optional[int] = Query(None, ge=MIN_USER_LIMIT_REQUEST, le=MAX_USER_LIMIT_REQUEST),
    offset: int = Query(0, ge=0),
    posted_only: bool = False,
    unposted_only: bool = False
):
    """
    Get jobs for a user.
    
    Args:
        user_id: User ID
        keyword: Filter by keyword
        location: Filter by location
        min_salary: Minimum salary
        source: Filter by source
        limit: Max results. Defaults to user's user_limit_request config.
        offset: Offset for pagination
        posted_only: Only posted jobs
        unposted_only: Only unposted jobs
        
    Returns:
        Jobs with metadata
    """
    result = job_service.get_jobs(
        user_id=user_id,
        keyword=keyword,
        location=location,
        min_salary=min_salary,
        source=source,
        limit=limit,
        offset=offset,
        posted_only=posted_only,
        unposted_only=unposted_only
    )
    
    return JobsResponse(**result)


@router.get("/{user_id}/{job_id}", response_model=Job)
async def get_job(user_id: int, job_id: str):
    """
    Get a specific job.
    
    Args:
        user_id: User ID
        job_id: Job ID
        
    Returns:
        Job details
    """
    job = job_service.get_job_by_id(user_id, job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return Job(**job)


@router.post("/mark-posted")
async def mark_jobs_posted(request: MarkPostedRequest):
    """
    Mark jobs as posted to Telegram.
    
    Args:
        request: Mark posted request with user_id, job_ids, message_ids
        
    Returns:
        Number of jobs marked
    """
    count = job_service.mark_as_posted(
        user_id=request.user_id,
        job_ids=request.job_ids,
        message_ids=request.message_ids
    )
    
    return {"success": True, "count": count}


@router.delete("/{user_id}/{job_id}")
async def delete_job(user_id: int, job_id: str):
    """
    Delete a job.
    
    Args:
        user_id: User ID
        job_id: Job ID
        
    Returns:
        Success status
    """
    success = job_service.delete_job(user_id, job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"success": True, "message": "Job deleted"}
