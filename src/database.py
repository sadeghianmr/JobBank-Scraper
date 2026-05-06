"""Database module for storing and managing job data."""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.config import BASE_DIR, DEFAULT_USER_LIMIT_REQUEST


class JobBankDB:
    """SQLite database manager for Job Bank jobs."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            db_path = BASE_DIR / "data" / "jobbank.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        
        self.connection = None
        self._connect()
        self._create_table()
    
    def _connect(self):
        """Create database connection."""
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row  # Access columns by name
    
    def _create_table(self):
        """Create JobBank table if it doesn't exist."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS JobBank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            company TEXT,
            location TEXT,
            salary TEXT,
            job_type TEXT,
            date_posted TEXT,
            url TEXT,
            source TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            posted_to_telegram BOOLEAN DEFAULT 0,
            telegram_message_id INTEGER
        )
        """
        
        cursor = self.connection.cursor()
        cursor.execute(create_table_sql)
        
        # Check if telegram columns exist (for existing databases)
        cursor.execute("PRAGMA table_info(JobBank)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'posted_to_telegram' not in columns:
            cursor.execute("ALTER TABLE JobBank ADD COLUMN posted_to_telegram BOOLEAN DEFAULT 0")
        
        if 'telegram_message_id' not in columns:
            cursor.execute("ALTER TABLE JobBank ADD COLUMN telegram_message_id INTEGER")
        
        # Create index on job_id for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_id ON JobBank(job_id)
        """)
        
        # Create index on source for filtering
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_source ON JobBank(source)
        """)
        
        # Create index on posted_to_telegram for bot queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_posted_telegram ON JobBank(posted_to_telegram)
        """)
        
        self.connection.commit()
        print(f"✓ Database initialized: {self.db_path}")
    
    def job_exists(self, job_id: str) -> bool:
        """
        Check if a job already exists in database.
        
        Args:
            job_id: Job Bank job ID
            
        Returns:
            True if job exists, False otherwise
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT 1 FROM JobBank WHERE job_id = ?", (job_id,))
        return cursor.fetchone() is not None
    
    def add_job(self, job_data: Dict[str, Any]) -> bool:
        """
        Add a new job to database or update if exists.
        
        Args:
            job_data: Dictionary containing job information
            
        Returns:
            True if new job added, False if job already existed (updated instead)
        """
        job_id = job_data.get('job_id')
        
        if not job_id:
            print("⚠️  Job missing job_id, skipping database insert")
            return False
        
        cursor = self.connection.cursor()
        
        # Check if job exists
        if self.job_exists(job_id):
            # Update last_seen timestamp
            cursor.execute("""
                UPDATE JobBank 
                SET last_seen = CURRENT_TIMESTAMP,
                    is_active = 1
                WHERE job_id = ?
            """, (job_id,))
            self.connection.commit()
            return False  # Job already existed
        else:
            # Insert new job
            cursor.execute("""
                INSERT INTO JobBank (
                    job_id, title, company, location, salary, 
                    job_type, date_posted, url, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                job_data.get('title'),
                job_data.get('company'),
                job_data.get('location'),
                job_data.get('salary'),
                job_data.get('job_type'),
                job_data.get('date_posted'),
                job_data.get('url'),
                job_data.get('source')
            ))
            self.connection.commit()
            return True  # New job added
    
    def add_jobs_batch(self, jobs: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Add multiple jobs to database in batch.
        
        Args:
            jobs: List of job dictionaries
            
        Returns:
            Dictionary with counts of new, existing, and skipped jobs
        """
        stats = {'new': 0, 'existing': 0, 'skipped': 0}
        
        for job in jobs:
            if self.add_job(job):
                stats['new'] += 1
            else:
                if job.get('job_id'):
                    stats['existing'] += 1
                else:
                    stats['skipped'] += 1
        
        return stats
    
    def get_all_jobs(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Retrieve all jobs from database.
        
        Args:
            active_only: If True, only return active jobs
            
        Returns:
            List of job dictionaries
        """
        cursor = self.connection.cursor()
        
        if active_only:
            cursor.execute("SELECT * FROM JobBank WHERE is_active = 1 ORDER BY scraped_at DESC")
        else:
            cursor.execute("SELECT * FROM JobBank ORDER BY scraped_at DESC")
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_jobs_by_source(self, source: str) -> List[Dict[str, Any]]:
        """
        Get jobs filtered by source.
        
        Args:
            source: Job source (e.g., 'Job Bank', 'Indeed')
            
        Returns:
            List of job dictionaries
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM JobBank 
            WHERE source = ? AND is_active = 1 
            ORDER BY scraped_at DESC
        """, (source,))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with various statistics
        """
        cursor = self.connection.cursor()
        
        # Total jobs
        cursor.execute("SELECT COUNT(*) FROM JobBank")
        total = cursor.fetchone()[0]
        
        # Active jobs
        cursor.execute("SELECT COUNT(*) FROM JobBank WHERE is_active = 1")
        active = cursor.fetchone()[0]
        
        # Jobs by source
        cursor.execute("""
            SELECT source, COUNT(*) as count 
            FROM JobBank 
            WHERE is_active = 1 
            GROUP BY source 
            ORDER BY count DESC
        """)
        by_source = dict(cursor.fetchall())
        
        # Recent additions (last 24 hours)
        cursor.execute("""
            SELECT COUNT(*) FROM JobBank 
            WHERE scraped_at >= datetime('now', '-1 day')
        """)
        recent = cursor.fetchone()[0]
        
        return {
            'total_jobs': total,
            'active_jobs': active,
            'inactive_jobs': total - active,
            'by_source': by_source,
            'added_last_24h': recent
        }
    
    def mark_inactive(self, job_ids: List[str]):
        """
        Mark jobs as inactive (no longer available).
        
        Args:
            job_ids: List of job IDs to mark as inactive
        """
        cursor = self.connection.cursor()
        placeholders = ','.join('?' * len(job_ids))
        cursor.execute(f"""
            UPDATE JobBank 
            SET is_active = 0 
            WHERE job_id IN ({placeholders})
        """, job_ids)
        self.connection.commit()
    
    def export_to_csv(self, output_path: str, active_only: bool = True):
        """
        Export database to CSV file.
        
        Args:
            output_path: Path for output CSV file
            active_only: If True, only export active jobs
        """
        import pandas as pd
        
        jobs = self.get_all_jobs(active_only=active_only)
        df = pd.DataFrame(jobs)
        
        if not df.empty:
            # Reorder columns for better readability
            cols = ['job_id', 'title', 'company', 'location', 'salary', 
                   'job_type', 'date_posted', 'source', 'url', 
                   'scraped_at', 'last_seen', 'is_active']
            df = df[[col for col in cols if col in df.columns]]
            
            df.to_csv(output_path, index=False)
            print(f"✓ Exported {len(df)} jobs to {output_path}")
        else:
            print("⚠️  No jobs to export")
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
    
    def get_unposted_jobs(self, job_bank_only: bool = False, 
                         min_salary: Optional[int] = None,
                         locations: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get jobs that haven't been posted to Telegram yet.
        
        Args:
            job_bank_only: If True, only return Job Bank source jobs
            min_salary: Minimum salary filter (optional)
            locations: List of locations to filter (optional)
            
        Returns:
            List of unposted job dictionaries
        """
        cursor = self.connection.cursor()
        
        query = """
            SELECT * FROM JobBank 
            WHERE posted_to_telegram = 0 
            AND is_active = 1
        """
        params = []
        
        if job_bank_only:
            query += " AND source = ?"
            params.append("Job Bank")
        
        if locations:
            placeholders = ','.join('?' * len(locations))
            query += f" AND location IN ({placeholders})"
            params.extend(locations)
        
        query += " ORDER BY scraped_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        jobs = [dict(row) for row in rows]
        
        # Filter by salary if specified
        if min_salary:
            filtered_jobs = []
            for job in jobs:
                salary_str = job.get('salary', '')
                if salary_str and self._extract_salary_value(salary_str) >= min_salary:
                    filtered_jobs.append(job)
            return filtered_jobs
        
        return jobs
    
    def _extract_salary_value(self, salary_str: str) -> int:
        """
        Extract numeric salary value from string.
        
        Args:
            salary_str: Salary string (e.g., "$70,000 - $85,000")
            
        Returns:
            Minimum salary value as integer, or 0 if not found
        """
        import re
        # Find all numbers in the salary string
        numbers = re.findall(r'\d+(?:,\d+)*', salary_str)
        if numbers:
            # Remove commas and convert first number to int
            return int(numbers[0].replace(',', ''))
        return 0
    
    def mark_as_posted(self, job_id: str, message_id: Optional[int] = None):
        """
        Mark a job as posted to Telegram.
        
        Args:
            job_id: Job Bank job ID
            message_id: Telegram message ID (optional)
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE JobBank 
            SET posted_to_telegram = 1,
                telegram_message_id = ?
            WHERE job_id = ?
        """, (message_id, job_id))
        self.connection.commit()
    
    def mark_jobs_as_posted(self, job_ids: List[str]):
        """
        Mark multiple jobs as posted to Telegram.
        
        Args:
            job_ids: List of job IDs to mark as posted
        """
        cursor = self.connection.cursor()
        placeholders = ','.join('?' * len(job_ids))
        cursor.execute(f"""
            UPDATE JobBank 
            SET posted_to_telegram = 1 
            WHERE job_id IN ({placeholders})
        """, job_ids)
        self.connection.commit()
    
    def get_telegram_stats(self) -> Dict[str, int]:
        """
        Get Telegram posting statistics.
        
        Returns:
            Dictionary with posting statistics
        """
        cursor = self.connection.cursor()
        
        # Posted jobs
        cursor.execute("SELECT COUNT(*) FROM JobBank WHERE posted_to_telegram = 1")
        posted = cursor.fetchone()[0]
        
        # Unposted jobs
        cursor.execute("SELECT COUNT(*) FROM JobBank WHERE posted_to_telegram = 0 AND is_active = 1")
        unposted = cursor.fetchone()[0]
        
        # Posted today
        cursor.execute("""
            SELECT COUNT(*) FROM JobBank 
            WHERE posted_to_telegram = 1 
            AND scraped_at >= date('now')
        """)
        posted_today = cursor.fetchone()[0]
        
        return {
            'total_posted': posted,
            'unposted': unposted,
            'posted_today': posted_today
        }
    
    def search_jobs(
        self,
        keyword: Optional[str] = None,
        location: Optional[str] = None,
        min_salary: Optional[int] = None,
        limit: int = DEFAULT_USER_LIMIT_REQUEST
    ) -> List[Dict[str, Any]]:
        """
        Search jobs with filters.
        
        Args:
            keyword: Search in title and company
            location: Filter by location
            min_salary: Minimum salary (if parseable)
            limit: Maximum results
            
        Returns:
            List of matching jobs
        """
        cursor = self.connection.cursor()
        
        query = "SELECT * FROM JobBank WHERE is_active = 1"
        params = []
        
        if keyword:
            query += " AND (title LIKE ? OR company LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        if location:
            query += " AND location LIKE ?"
            params.append(f"%{location}%")
        
        # Note: min_salary filtering is approximate since salary is stored as text
        if min_salary:
            # This is a simple check - won't parse complex salary strings
            query += " AND salary LIKE ?"
            params.append(f"%{min_salary}%")
        
        query += " ORDER BY scraped_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific job by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job dictionary or None if not found
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM JobBank WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
