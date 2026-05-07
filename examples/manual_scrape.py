"""
Example: use the shared scraper package without the API or Telegram bot.

Run:
    python examples/manual_scrape.py
"""

from _paths import PROJECT_ROOT  # noqa: F401

from src.scraper import quick_search
from src.utils import save_jobs_to_file


def main():
    """Run one small scrape and export the results."""
    jobs = quick_search(
        keyword="python developer",
        location="Toronto",
        max_pages=1,
        headless=True,
        job_bank_only=True,
        recent_jobs_only=True,
        use_database=False,
    )

    print(f"Found {len(jobs)} jobs")

    for job in jobs[:5]:
        print(f"- {job['title']} at {job.get('company') or 'Unknown'}")

    if jobs:
        output_path = save_jobs_to_file(
            jobs,
            filename="example_manual_scrape",
            format="csv",
        )
        print(f"\nSaved export to {output_path}")


if __name__ == "__main__":
    main()
