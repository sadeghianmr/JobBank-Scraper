"""
Integration tests for scraper functionality.

These tests use the REAL scraper and actually scrape Job Bank.
They are slower (~10-30 seconds each) but verify real functionality.

WARNING: These tests hit the real Job Bank website.
Don't run them too frequently to avoid being rate-limited.
"""

import pytest


class TestScraperIntegration:
    """Test real scraping functionality."""
    
    @pytest.mark.slow
    def test_scrape_real_jobs_python(self, client, test_user_id, cleanup_test_db):
        """
        Test scraping REAL jobs from Job Bank.
        
        This test:
        1. Actually opens a browser (headless)
        2. Navigates to Job Bank website
        3. Searches for "python" jobs
        4. Scrapes 1 page of results
        5. Saves to database
        
        Takes ~10-20 seconds.
        """
        print("\n🔍 Testing real scraping: Python jobs in Toronto...")
        
        response = client.post(
            "/api/v1/scraper/scrape",
            json={
                "user_id": test_user_id,
                "keyword": "python",
                "location": "Toronto",
                "pages": 1,
                "job_bank_only": True,
                "headless": True
            }
        )
        
        # Verify response
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        print(f"✓ Response: {data}")
        
        # Verify success
        assert data["success"] is True
        assert "message" in data
        
        # Jobs should be found (Job Bank always has Python jobs in Toronto)
        assert data["jobs_found"] > 0, "No jobs found - this is unexpected!"
        assert isinstance(data["jobs_found"], int)
        
        print(f"✓ Found {data['jobs_found']} real jobs")
    
    @pytest.mark.slow
    def test_scrape_real_jobs_software_engineer(self, client, test_user_id, cleanup_test_db):
        """
        Test scraping with different keyword.
        
        Tests that scraper works with various search terms.
        """
        print("\n🔍 Testing real scraping: Software Engineer in Vancouver...")
        
        response = client.post(
            "/api/v1/scraper/scrape",
            json={
                "user_id": test_user_id,
                "keyword": "software engineer",
                "location": "Vancouver",
                "pages": 1,
                "job_bank_only": True,
                "headless": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["jobs_found"] > 0
        
        print(f"✓ Found {data['jobs_found']} software engineer jobs")
    
    @pytest.mark.slow
    def test_scrape_multiple_pages(self, client, test_user_id, cleanup_test_db):
        """
        Test scraping multiple pages.
        
        This test takes longer (~20-30 seconds) as it scrapes 2 pages.
        """
        print("\n🔍 Testing multi-page scraping...")
        
        response = client.post(
            "/api/v1/scraper/scrape",
            json={
                "user_id": test_user_id,
                "keyword": "data analyst",
                "location": "Canada",
                "pages": 2,  # Scrape 2 pages
                "job_bank_only": True,
                "headless": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["jobs_found"] > 10, "Expected more jobs from 2 pages"
        
        print(f"✓ Found {data['jobs_found']} jobs from 2 pages")
    
    def test_scrape_with_invalid_keyword(self, client, test_user_id, cleanup_test_db):
        """
        Test scraping with unlikely keyword.
        
        Should still succeed but might find 0 jobs.
        """
        print("\n🔍 Testing scraping with unlikely keyword...")
        
        response = client.post(
            "/api/v1/scraper/scrape",
            json={
                "user_id": test_user_id,
                "keyword": "xyzabc123unlikely",
                "location": "Toronto",
                "pages": 1,
                "job_bank_only": True,
                "headless": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should succeed even with 0 results
        assert data["success"] is True
        assert data["jobs_found"] >= 0
        
        print(f"✓ Handled unlikely keyword gracefully (found {data['jobs_found']} jobs)")


class TestJobPersistence:
    """Test that scraped jobs persist in database."""
    
    @pytest.mark.slow
    def test_jobs_saved_to_database(self, client, test_user_id, cleanup_test_db):
        """
        Test complete flow: scrape -> save -> retrieve.
        
        Verifies:
        1. Jobs are scraped
        2. Jobs are saved to database
        3. Jobs can be retrieved
        """
        print("\n💾 Testing job persistence...")
        
        # Step 1: Scrape jobs
        scrape_response = client.post(
            "/api/v1/scraper/scrape",
            json={
                "user_id": test_user_id,
                "keyword": "data analyst",
                "location": "Canada",
                "pages": 1,
                "job_bank_only": True,
                "headless": True
            }
        )
        
        assert scrape_response.status_code == 200
        scrape_data = scrape_response.json()
        assert scrape_data["success"] is True
        jobs_found = scrape_data["jobs_found"]
        
        print(f"✓ Scraped {jobs_found} jobs")
        
        # Step 2: Retrieve jobs from database
        jobs_response = client.get(f"/api/v1/jobs/{test_user_id}")
        
        assert jobs_response.status_code == 200
        jobs_data = jobs_response.json()
        
        # Verify jobs were saved
        assert jobs_data["total"] == jobs_found
        assert len(jobs_data["jobs"]) > 0
        
        print(f"✓ Retrieved {jobs_data['total']} jobs from database")
        
        # Step 3: Verify job structure
        first_job = jobs_data["jobs"][0]
        assert "job_id" in first_job
        assert "title" in first_job
        assert "company" in first_job
        assert "location" in first_job
        assert "url" in first_job
        assert "source" in first_job
        
        print(f"✓ Job structure valid: {first_job['title']} at {first_job['company']}")
    
    @pytest.mark.slow
    def test_unposted_jobs_filter(self, client, test_user_id, cleanup_test_db):
        """
        Test filtering unposted jobs.
        
        After scraping, all jobs should be unposted.
        """
        print("\n🔍 Testing unposted jobs filter...")
        
        # Scrape jobs
        client.post(
            "/api/v1/scraper/scrape",
            json={
                "user_id": test_user_id,
                "keyword": "developer",
                "location": "Toronto",
                "pages": 1,
                "job_bank_only": True,
                "headless": True
            }
        )
        
        # Get unposted jobs
        response = client.get(
            f"/api/v1/jobs/{test_user_id}",
            params={"unposted_only": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All jobs should be unposted
        assert data["total"] > 0
        for job in data["jobs"]:
            assert job["posted_to_telegram"] is False
        
        print(f"✓ All {data['total']} jobs are correctly marked as unposted")
    
    @pytest.mark.slow
    def test_mark_jobs_as_posted(self, client, test_user_id, cleanup_test_db):
        """
        Test marking jobs as posted.
        
        Verifies the complete workflow:
        1. Scrape jobs
        2. Get unposted jobs
        3. Mark some as posted
        4. Verify they're no longer unposted
        """
        print("\n✅ Testing mark as posted workflow...")
        
        # Step 1: Scrape jobs
        scrape_response = client.post(
            "/api/v1/scraper/scrape",
            json={
                "user_id": test_user_id,
                "keyword": "python",
                "location": "Toronto",
                "pages": 1,
                "job_bank_only": True,
                "headless": True
            }
        )
        assert scrape_response.status_code == 200
        
        # Step 2: Get unposted jobs
        unposted_response = client.get(
            f"/api/v1/jobs/{test_user_id}",
            params={"unposted_only": True, "limit": 3}
        )
        unposted_data = unposted_response.json()
        initial_unposted = unposted_data["total"]
        
        print(f"✓ Initial unposted count: {initial_unposted}")
        
        # Get first job to mark as posted
        job_to_mark = unposted_data["jobs"][0]
        job_id = job_to_mark["job_id"]
        
        # Step 3: Mark job as posted
        mark_response = client.post(
            "/api/v1/jobs/mark-posted",
            json={
                "user_id": test_user_id,
                "job_ids": [job_id],
                "message_ids": [12345]  # Fake Telegram message ID
            }
        )
        
        assert mark_response.status_code == 200
        mark_data = mark_response.json()
        assert mark_data["success"] is True
        assert mark_data["count"] == 1
        
        print(f"✓ Marked job {job_id} as posted")
        
        # Step 4: Verify unposted count decreased
        after_response = client.get(
            f"/api/v1/jobs/{test_user_id}",
            params={"unposted_only": True}
        )
        after_data = after_response.json()
        final_unposted = after_data["total"]
        
        assert final_unposted == initial_unposted - 1
        
        print(f"✓ Unposted count decreased: {initial_unposted} -> {final_unposted}")


class TestStatistics:
    """Test statistics functionality."""
    
    @pytest.mark.slow
    def test_statistics_after_scraping(self, client, test_user_id, cleanup_test_db):
        """
        Test that statistics are accurate after scraping.
        """
        print("\n📊 Testing statistics...")
        
        # Scrape jobs
        scrape_response = client.post(
            "/api/v1/scraper/scrape",
            json={
                "user_id": test_user_id,
                "keyword": "software",
                "location": "Toronto",
                "pages": 1,
                "job_bank_only": True,
                "headless": True
            }
        )
        jobs_found = scrape_response.json()["jobs_found"]
        
        # Get statistics
        stats_response = client.get(f"/api/v1/jobs/{test_user_id}/stats")
        
        assert stats_response.status_code == 200
        stats = stats_response.json()
        
        # Verify statistics
        assert stats["total_jobs"] == jobs_found
        assert stats["unposted_jobs"] == jobs_found  # All should be unposted
        assert stats["posted_jobs"] == 0
        assert "Job Bank" in stats["sources"]
        
        print(f"✓ Statistics accurate: {stats}")
