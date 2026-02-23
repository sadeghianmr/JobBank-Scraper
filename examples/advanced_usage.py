"""
Advanced scraping examples using the JobBankScraper class.
For users who need more control over the scraping process.
"""

from src.scraper import JobBankScraper
from src.utils import save_jobs_to_file


def example_1_context_manager():
    """Use the scraper with context manager for better control."""
    print("Example 1: Using Context Manager\n")
    
    with JobBankScraper(headless=True) as scraper:
        jobs = scraper.search_jobs(
            keyword="data scientist",
            location="Toronto",
            max_pages=2
        )
        
        print(f"Found {len(jobs)} jobs")
        
        # Get detailed info for first job
        if jobs:
            first_job = jobs[0]
            print(f"\nGetting details for: {first_job['title']}")
            details = scraper.get_job_details(first_job['url'])
            
            if details:
                print(f"Has description: {bool(details.get('description'))}")


def example_2_multiple_searches():
    """Run multiple searches in one session."""
    print("\nExample 2: Multiple Searches in One Session\n")
    
    keywords = ["python developer", "javascript developer", "java developer"]
    all_jobs = []
    
    with JobBankScraper() as scraper:
        for keyword in keywords:
            print(f"Searching for: {keyword}")
            jobs = scraper.search_jobs(
                keyword=keyword,
                location="Canada",
                max_pages=1
            )
            all_jobs.extend(jobs)
    
    print(f"\nTotal jobs collected: {len(all_jobs)}")
    save_jobs_to_file(all_jobs, "all_developer_jobs", "csv")


def example_3_filter_results():
    """Process and filter scraped results."""
    print("\nExample 3: Filtering Results\n")
    
    with JobBankScraper() as scraper:
        jobs = scraper.search_jobs(
            keyword="developer",
            location="Ontario",
            max_pages=2
        )
    
    # Filter for remote jobs
    remote_jobs = [
        job for job in jobs 
        if 'remote' in job.get('location', '').lower()
    ]
    
    # Filter for senior positions
    senior_jobs = [
        job for job in jobs
        if 'senior' in job.get('title', '').lower()
    ]
    
    print(f"Total jobs: {len(jobs)}")
    print(f"Remote jobs: {len(remote_jobs)}")
    print(f"Senior positions: {len(senior_jobs)}")


def example_4_visible_browser():
    """Watch the scraper work (debugging/learning)."""
    print("\nExample 4: Visible Browser Mode\n")
    
    # Set headless=False to see the browser
    with JobBankScraper(headless=False) as scraper:
        jobs = scraper.search_jobs(
            keyword="analyst",
            location="Toronto",
            max_pages=1
        )
        print(f"Scraped {len(jobs)} jobs (you saw the browser in action!)")


def example_5_error_handling():
    """Handle errors gracefully."""
    print("\nExample 5: Error Handling\n")
    
    try:
        with JobBankScraper() as scraper:
            jobs = scraper.search_jobs(
                keyword="software",
                location="Toronto",
                max_pages=100  # Might be a lot
            )
            print(f"Successfully scraped {len(jobs)} jobs")
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        print("But the program didn't crash!")


if __name__ == "__main__":
    print("=" * 60)
    print("ADVANCED USAGE EXAMPLES")
    print("=" * 60)
    
    # Uncomment the examples you want to run:
    example_1_context_manager()
    # example_2_multiple_searches()
    # example_3_filter_results()
    # example_4_visible_browser()  # Opens visible browser window
    # example_5_error_handling()
