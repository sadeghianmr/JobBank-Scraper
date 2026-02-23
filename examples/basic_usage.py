"""
Basic usage examples for the Job Bank Scraper.
Start here if you're new to the project.
"""

from src.scraper import quick_search
from src.utils import save_jobs_to_file


def example_1_simple_search():
    """The simplest way to scrape jobs."""
    print("Example 1: Basic Job Search\n")
    
    jobs = quick_search(
        keyword="python developer",
        location="Toronto",
        max_pages=1
    )
    
    print(f"Found {len(jobs)} jobs")
    print(f"First job: {jobs[0]['title']} at {jobs[0].get('company', 'N/A')}")


def example_2_multiple_pages():
    """Scrape multiple pages of results."""
    print("\nExample 2: Scraping Multiple Pages\n")
    
    jobs = quick_search(
        keyword="data analyst",
        location="Vancouver",
        max_pages=3  # Scrapes 3 pages (75 jobs)
    )
    
    print(f"Scraped {len(jobs)} jobs from 3 pages")


def example_3_job_bank_only():
    """Filter out external job sources (Indeed, CareerBeacon, etc)."""
    print("\nExample 3: Job Bank Posts Only\n")
    
    # Get all jobs
    all_jobs = quick_search(
        keyword="software engineer",
        location="Toronto",
        max_pages=2,
        job_bank_only=False
    )
    
    # Get only Job Bank jobs
    jb_jobs = quick_search(
        keyword="software engineer",
        location="Toronto",
        max_pages=2,
        job_bank_only=True
    )
    
    print(f"All sources: {len(all_jobs)} jobs")
    print(f"Job Bank only: {len(jb_jobs)} jobs")
    print(f"Filtered out: {len(all_jobs) - len(jb_jobs)} external jobs")


def example_4_save_formats():
    """Save results in different formats."""
    print("\nExample 4: Different Output Formats\n")
    
    jobs = quick_search(keyword="designer", location="Montreal", max_pages=1)
    
    # Save as CSV
    save_jobs_to_file(jobs, filename="jobs_csv", format="csv")
    
    # Save as JSON
    save_jobs_to_file(jobs, filename="jobs_json", format="json")
    
    # Save as Excel
    save_jobs_to_file(jobs, filename="jobs_excel", format="excel")
    
    print("Saved in 3 formats: CSV, JSON, and Excel")


def example_5_without_database():
    """Scrape without saving to database (CSV only)."""
    print("\nExample 5: Skip Database Storage\n")
    
    jobs = quick_search(
        keyword="manager",
        location="Calgary",
        max_pages=1,
        use_database=False  # Don't save to database
    )
    
    print(f"Found {len(jobs)} jobs (saved to CSV only, not in database)")


if __name__ == "__main__":
    # Run the examples
    print("=" * 60)
    print("BASIC USAGE EXAMPLES")
    print("=" * 60)
    
    # Uncomment the examples you want to run:
    example_1_simple_search()
    # example_2_multiple_pages()
    # example_3_job_bank_only()
    # example_4_save_formats()
    # example_5_without_database()
