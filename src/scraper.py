"""Main scraper module for Canada Job Bank."""

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import time
from urllib.parse import urlencode

from src.config import (
    JOB_SEARCH_URL, 
    HEADLESS, 
    TIMEOUT, 
    MAX_RETRIES,
    DEFAULT_SEARCH_PARAMS
)
from src.utils import (
    get_random_user_agent, 
    wait_random, 
    clean_text,
    format_job_data
)
from src.database import JobBankDB


class JobBankScraper:
    """Scraper for Canada Job Bank website."""
    
    def __init__(self, headless: bool = HEADLESS, use_database: bool = True):
        """
        Initialize the Job Bank scraper.
        
        Args:
            headless: Run browser in headless mode
            use_database: Save jobs to database automatically
        """
        self.headless = headless
        self.use_database = use_database
        self.db = None
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # Initialize database if enabled
        if self.use_database:
            self.db = JobBankDB()
        
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        
    def start(self):
        """Start the browser."""
        print("🚀 Starting browser...")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        
        # Create a new context with a random user agent
        self.context = self.browser.new_context(
            user_agent=get_random_user_agent(),
            viewport={'width': 1920, 'height': 1080}
        )
        
        self.page = self.context.new_page()
        self.page.set_default_timeout(TIMEOUT)
        print("✓ Browser started")
        
    def close(self):
        """Close the browser and cleanup."""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        if self.db:
            self.db.close()
        print("✓ Browser closed")
        
    def search_jobs(self, 
                    keyword: str = "", 
                    location: str = "",
                    max_pages: int = 1,
                    job_bank_only: bool = False) -> List[Dict[str, Any]]:
        """
        Search for jobs on Job Bank.
        
        Args:
            keyword: Job keyword or title
            location: Location (city, province, or postal code)
            max_pages: Maximum number of pages to scrape
            job_bank_only: If True, only return jobs posted directly on Job Bank
            
        Returns:
            List of job dictionaries
        """
        all_jobs = []
        new_jobs_count = 0
        existing_jobs_count = 0
        
        # Build search URL
        params = DEFAULT_SEARCH_PARAMS.copy()
        if keyword:
            params['searchstring'] = keyword
        if location:
            params['locationstring'] = location
            
        search_url = f"{JOB_SEARCH_URL}?{urlencode(params)}"
        
        print(f"\n🔍 Searching for: '{keyword}' in '{location}'")
        print(f"📄 Scraping up to {max_pages} page(s)...")
        
        for page_num in range(1, max_pages + 1):
            try:
                # Add page parameter for pagination
                if page_num > 1:
                    page_params = params.copy()
                    page_params['page'] = str(page_num)
                    page_url = f"{JOB_SEARCH_URL}?{urlencode(page_params)}"
                else:
                    page_url = search_url
                
                print(f"\n📑 Scraping page {page_num}...")
                jobs = self._scrape_search_page(page_url, job_bank_only=job_bank_only)
                
                if not jobs:
                    print(f"No more jobs found on page {page_num}")
                    break
                    
                # Save to database if enabled
                if self.use_database and self.db and jobs:
                    stats = self.db.add_jobs_batch(jobs)
                    new_jobs_count += stats['new']
                    existing_jobs_count += stats['existing']
                    print(f"✓ Found {len(jobs)} jobs on page {page_num} ({stats['new']} new, {stats['existing']} existing)")
                else:
                    print(f"✓ Found {len(jobs)} jobs on page {page_num}")
                
                all_jobs.extend(jobs)
                
                # Wait before next page
                if page_num < max_pages and jobs:
                    print("⏳ Waiting 2 seconds before next page...")
                    time.sleep(2)
                    
            except Exception as e:
                print(f"❌ Error on page {page_num}: {str(e)}")
                break
        
        print(f"\n✅ Total jobs scraped: {len(all_jobs)}")
        if self.use_database and self.db:
            print(f"   📊 Database: {new_jobs_count} new, {existing_jobs_count} already existed")
        return all_jobs
    
    def _scrape_search_page(self, url: str, job_bank_only: bool = False) -> List[Dict[str, Any]]:
        """
        Scrape a single search results page.
        
        Args:
            url: Search page URL
            job_bank_only: If True, only return jobs posted directly on Job Bank
            
        Returns:
            List of job dictionaries from the page
        """
        jobs = []
        
        # Navigate to page
        try:
            self.page.goto(url, wait_until='networkidle', timeout=TIMEOUT)
            wait_random(1, 2)
        except PlaywrightTimeout:
            print("⚠️  Page load timeout, trying to continue...")
        
        # Wait for job listings to load
        try:
            self.page.wait_for_selector('a.resultJobItem', timeout=10000)
        except PlaywrightTimeout:
            print("⚠️  No job listings found")
            return jobs
        
        # Get page content
        content = self.page.content()
        soup = BeautifulSoup(content, 'lxml')
        
        # Find all job listings (they are <a> tags with class resultJobItem)
        job_articles = soup.find_all('a', class_='resultJobItem')
        
        for article in job_articles:
            try:
                job_data = self._extract_job_data(article)
                if job_data:
                    # Filter by source if job_bank_only is True
                    if job_bank_only and job_data.get('source') != 'Job Bank':
                        continue
                    jobs.append(format_job_data(job_data))
            except Exception as e:
                print(f"⚠️  Error extracting job data: {str(e)}")
                continue
        
        return jobs
    
    def _extract_job_data(self, article) -> Optional[Dict[str, Any]]:
        """
        Extract job data from a job listing element.
        
        Args:
            article: BeautifulSoup element (an <a> tag with class resultJobItem)
            
        Returns:
            Dictionary with job data or None
        """
        job = {}
        
        # Job URL and ID
        href = article.get('href', '')
        if href:
            job['url'] = f"https://www.jobbank.gc.ca{href}"
            job['job_id'] = href.split('/')[-1].split(';')[0] if '/' in href else None
        else:
            return None
        
        # Job title - in <span class="noctitle"> inside <h3 class="title">
        title_elem = article.find('span', class_='noctitle')
        if title_elem:
            job['title'] = clean_text(title_elem.get_text())
        else:
            return None
        
        # Find the list of details
        details_list = article.find('ul', class_='list-unstyled')
        if details_list:
            # Date posted
            date_elem = details_list.find('li', class_='date')
            if date_elem:
                job['date_posted'] = clean_text(date_elem.get_text())
            
            # Company name
            company_elem = details_list.find('li', class_='business')
            if company_elem:
                job['company'] = clean_text(company_elem.get_text())
            
            # Location
            location_elem = details_list.find('li', class_='location')
            if location_elem:
                job['location'] = clean_text(location_elem.get_text())
            
            # Salary
            salary_elem = details_list.find('li', class_='salary')
            if salary_elem:
                job['salary'] = clean_text(salary_elem.get_text())
        
        # Job type (remote, on-site, hybrid) - in <span class="telework">
        telework_elem = article.find('span', class_='telework')
        if telework_elem:
            job['job_type'] = clean_text(telework_elem.get_text())
        
        # Job source - determine if posted on Job Bank or external source
        # Check for "Posted on Job Bank" indicator
        posted_on_jb = article.find('span', class_='postedonJB')
        if posted_on_jb:
            job['source'] = 'Job Bank'
        else:
            # Check for external source in the source list item or job-source span
            source_elem = None
            if details_list:
                source_li = details_list.find('li', class_='source')
                if source_li:
                    source_elem = source_li
            
            if not source_elem:
                # Try to find job-source span
                source_span = article.find('span', class_='job-source')
                if source_span:
                    source_elem = source_span
            
            if source_elem:
                source_text = clean_text(source_elem.get_text())
                # Clean up source names
                if 'indeed' in source_text.lower():
                    job['source'] = 'Indeed'
                elif 'careerbeacon' in source_text.lower():
                    job['source'] = 'CareerBeacon'
                else:
                    job['source'] = source_text if source_text else 'Job Bank'
            else:
                job['source'] = 'Job Bank'  # Default to Job Bank if no external source found
        
        return job
    
    def get_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific job.
        
        Args:
            job_url: URL of the job posting
            
        Returns:
            Dictionary with detailed job data
        """
        try:
            self.page.goto(job_url, wait_until='networkidle', timeout=TIMEOUT)
            wait_random(1, 2)
            
            content = self.page.content()
            soup = BeautifulSoup(content, 'lxml')
            
            details = {}
            
            # Job description
            desc_elem = soup.find('section', id='job-description')
            if desc_elem:
                details['description'] = clean_text(desc_elem.get_text())
            
            # Additional job details from the details section
            details_section = soup.find('section', class_='job-details')
            if details_section:
                # Extract all key-value pairs
                labels = details_section.find_all('dt')
                for label in labels:
                    key = clean_text(label.get_text()).lower().replace(' ', '_')
                    value_elem = label.find_next_sibling('dd')
                    if value_elem:
                        details[key] = clean_text(value_elem.get_text())
            
            return details
            
        except Exception as e:
            print(f"❌ Error getting job details: {str(e)}")
            return None


def quick_search(keyword: str = "", location: str = "", max_pages: int = 1,
                 headless: bool = True, job_bank_only: bool = False,
                 use_database: bool = True) -> List[Dict[str, Any]]:
    """
    Quick search function for convenience.
    
    Args:
        keyword: Job keyword or title
        location: Location (city, province, or postal code)
        max_pages: Maximum number of pages to scrape
        headless: Run browser in headless mode
        job_bank_only: If True, only return jobs posted directly on Job Bank
        use_database: Save jobs to database (default: True)
        
    Returns:
        List of job dictionaries
    """
    with JobBankScraper(headless=headless, use_database=use_database) as scraper:
        return scraper.search_jobs(keyword, location, max_pages, job_bank_only)
