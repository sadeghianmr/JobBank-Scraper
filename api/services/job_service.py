"""Job service for database operations."""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.database import JobBankDB
from src.config import BASE_DIR
from src.user_config import get_user_limit_request

logger = logging.getLogger(__name__)


class JobService:
    """Service for job database operations."""
    
    def get_user_db_path(self, user_id: int) -> Path:
        """Get path to user's database."""
        user_data_dir = BASE_DIR / "data" / f"user_{user_id}"
        user_data_dir.mkdir(parents=True, exist_ok=True)
        return user_data_dir / "jobs.db"
    
    def get_jobs(
        self,
        user_id: int,
        keyword: Optional[str] = None,
        location: Optional[str] = None,
        min_salary: Optional[int] = None,
        source: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        posted_only: bool = False,
        unposted_only: bool = False
    ) -> Dict[str, Any]:
        """
        Get jobs from user's database.
        
        Args:
            user_id: User ID
            keyword: Filter by keyword
            location: Filter by location
            min_salary: Minimum salary
            source: Filter by source
            limit: Max results
            offset: Offset for pagination
            posted_only: Only posted jobs
            unposted_only: Only unposted jobs
            
        Returns:
            Dict with jobs and metadata
        """
        db_path = self.get_user_db_path(user_id)
        
        resolved_limit = get_user_limit_request(user_id) if limit is None else limit
        
        with JobBankDB(db_path=str(db_path)) as db:
            # Build query based on filters
            if unposted_only:
                jobs = db.get_unposted_jobs(
                    job_bank_only=(source == "Job Bank"),
                    min_salary=min_salary
                )
            else:
                jobs = db.search_jobs(
                    keyword=keyword,
                    location=location,
                    min_salary=min_salary,
                    limit=resolved_limit + offset  # Get more for offset
                )
            
            # Filter by posted status if needed
            if posted_only:
                jobs = [j for j in jobs if j.get('posted_to_telegram')]
            
            # Filter by source if specified
            if source:
                jobs = [j for j in jobs if j.get('source') == source]
            
            # Apply offset and limit
            total = len(jobs)
            jobs = jobs[offset:offset + resolved_limit]
            
            return {
                "total": total,
                "jobs": jobs,
                "limit": resolved_limit,
                "offset": offset
            }
    
    def get_job_by_id(self, user_id: int, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific job by ID."""
        db_path = self.get_user_db_path(user_id)
        
        with JobBankDB(db_path=str(db_path)) as db:
            return db.get_job(job_id)
    
    def mark_as_posted(
        self,
        user_id: int,
        job_ids: List[str],
        message_ids: Optional[List[int]] = None
    ) -> int:
        """Mark jobs as posted to Telegram."""
        db_path = self.get_user_db_path(user_id)
        
        with JobBankDB(db_path=str(db_path)) as db:
            if message_ids:
                count = 0
                for job_id, msg_id in zip(job_ids, message_ids):
                    db.mark_as_posted(job_id, msg_id)
                    count += 1
                return count
            else:
                db.mark_jobs_as_posted(job_ids)
                return len(job_ids)
    
    def get_stats(self, user_id: int) -> Dict[str, Any]:
        """Get statistics for user's database."""
        db_path = self.get_user_db_path(user_id)
        
        with JobBankDB(db_path=str(db_path)) as db:
            stats = db.get_stats()
            telegram_stats = db.get_telegram_stats()
            
            return {
                "total_jobs": stats.get('total_jobs', 0),
                "unposted_jobs": telegram_stats.get('unposted', 0),
                "posted_jobs": telegram_stats.get('total_posted', 0),
                "sources": stats.get('by_source', {})
            }
    
    def delete_job(self, user_id: int, job_id: str) -> bool:
        """Delete a job from user's database."""
        db_path = self.get_user_db_path(user_id)
        
        with JobBankDB(db_path=str(db_path)) as db:
            cursor = db.connection.cursor()
            cursor.execute("DELETE FROM JobBank WHERE job_id = ?", (job_id,))
            db.connection.commit()
            return cursor.rowcount > 0
