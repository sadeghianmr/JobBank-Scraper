"""
Examples for working with the SQLite database.
Shows how to query, export, and manage stored jobs.
"""

from src.database import JobBankDB


def example_1_database_stats():
    """Check what's in your database."""
    print("Example 1: Database Statistics\n")
    
    with JobBankDB() as db:
        stats = db.get_stats()
        
        print(f"Total jobs in database: {stats['total_jobs']}")
        print(f"Active jobs: {stats['active_jobs']}")
        print(f"Added in last 24 hours: {stats['added_last_24h']}")
        
        print("\nJobs by source:")
        for source, count in stats['by_source'].items():
            print(f"  {source}: {count} jobs")


def example_2_query_jobs():
    """Get jobs from the database."""
    print("\nExample 2: Query Jobs from Database\n")
    
    with JobBankDB() as db:
        # Get all active jobs
        all_jobs = db.get_all_jobs(active_only=True)
        print(f"Total active jobs: {len(all_jobs)}")
        
        # Get only Job Bank posted jobs
        jb_jobs = db.get_jobs_by_source('Job Bank')
        print(f"Job Bank only: {len(jb_jobs)}")
        
        # Show first job
        if all_jobs:
            job = all_jobs[0]
            print(f"\nFirst job in database:")
            print(f"  Title: {job['title']}")
            print(f"  Company: {job['company']}")
            print(f"  Location: {job['location']}")


def example_3_export_database():
    """Export your database to files."""
    print("\nExample 3: Export Database\n")
    
    with JobBankDB() as db:
        # Export all active jobs
        db.export_to_csv('data/all_jobs.csv', active_only=True)
        print("Exported to data/all_jobs.csv")
        
        # You can also get jobs and process them
        jobs = db.get_all_jobs()
        print(f"Ready to analyze {len(jobs)} jobs!")


def example_4_check_duplicates():
    """See how duplicate detection works."""
    print("\nExample 4: Duplicate Detection\n")
    
    with JobBankDB() as db:
        # Check if a specific job exists
        job_id = "12345678"  # Example job ID
        exists = db.job_exists(job_id)
        print(f"Job {job_id} exists: {exists}")
        
        # When you scrape, duplicates are automatically skipped
        # The database only updates the 'last_seen' timestamp


def example_5_manual_insert():
    """Manually add a job to the database."""
    print("\nExample 5: Manual Job Insert\n")
    
    # Create a job dictionary
    job = {
        'job_id': '99999999',
        'title': 'Test Job',
        'company': 'Test Company',
        'location': 'Toronto, ON',
        'salary': '$50/hour',
        'job_type': 'Remote',
        'date_posted': 'Feb 22, 2026',
        'url': 'https://example.com',
        'source': 'Job Bank'
    }
    
    with JobBankDB() as db:
        is_new = db.add_job(job)
        if is_new:
            print("New job added to database")
        else:
            print("Job already existed (updated last_seen instead)")


def example_6_get_recent_jobs():
    """Find recently added jobs."""
    print("\nExample 6: Recent Jobs\n")
    
    with JobBankDB() as db:
        all_jobs = db.get_all_jobs(active_only=True)
        
        # Sort by scraped_at to get most recent
        recent = sorted(
            all_jobs, 
            key=lambda x: x['scraped_at'], 
            reverse=True
        )[:10]
        
        print("10 most recently scraped jobs:")
        for i, job in enumerate(recent, 1):
            print(f"{i}. {job['title']} at {job.get('company', 'N/A')}")


if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE EXAMPLES")
    print("=" * 60)
    print("\nNote: These examples require that you've already scraped some jobs.\n")
    
    # Uncomment the examples you want to run:
    example_1_database_stats()
    # example_2_query_jobs()
    # example_3_export_database()
    # example_4_check_duplicates()
    # example_5_manual_insert()
    # example_6_get_recent_jobs()
