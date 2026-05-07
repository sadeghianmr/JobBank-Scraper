"""
Example: run a small workflow through the local FastAPI backend.

Start the API first:
    ./start_api.sh

Then run:
    python examples/api_workflow.py
"""

import os
from pprint import pprint

import httpx

from _paths import PROJECT_ROOT  # noqa: F401


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
EXAMPLE_USER_ID = int(os.getenv("EXAMPLE_USER_ID", "900001"))


def main():
    """Scrape, read unposted jobs, mark a small sample, and print stats."""
    with httpx.Client(base_url=API_BASE_URL, timeout=120) as client:
        health = client.get("/health")
        health.raise_for_status()
        print("Health check:")
        pprint(health.json())

        scrape = client.post(
            "/api/v1/scraper/scrape",
            json={
                "user_id": EXAMPLE_USER_ID,
                "keyword": "data analyst",
                "location": "Vancouver",
                "pages": 1,
                "job_bank_only": True,
                "recent_jobs_only": True,
                "headless": True,
            },
        )
        scrape.raise_for_status()
        print("\nScrape result:")
        pprint(scrape.json())

        jobs = client.get(
            f"/api/v1/jobs/{EXAMPLE_USER_ID}",
            params={"unposted_only": True, "recent_days": 30, "limit": 5},
        )
        jobs.raise_for_status()
        payload = jobs.json()

        print(f"\nUnposted jobs returned: {len(payload['jobs'])}")
        for job in payload["jobs"]:
            print(f"- {job['job_id']}: {job['title']} at {job.get('company') or 'Unknown'}")

        sample_job_ids = [job["job_id"] for job in payload["jobs"][:2]]
        if sample_job_ids:
            marked = client.post(
                "/api/v1/jobs/mark-posted",
                json={
                    "user_id": EXAMPLE_USER_ID,
                    "job_ids": sample_job_ids,
                    "message_ids": [1000 + index for index, _ in enumerate(sample_job_ids)],
                },
            )
            marked.raise_for_status()
            print("\nMarked sample jobs as posted:")
            pprint(marked.json())

        stats = client.get(f"/api/v1/jobs/{EXAMPLE_USER_ID}/stats")
        stats.raise_for_status()
        print("\nUser stats:")
        pprint(stats.json())


if __name__ == "__main__":
    try:
        main()
    except httpx.ConnectError:
        print(f"Could not connect to {API_BASE_URL}. Start the API with ./start_api.sh first.")
