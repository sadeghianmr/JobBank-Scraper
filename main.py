"""
Canada Job Bank Scraper - Main Entry Point

This script provides a command-line interface for scraping jobs from the 
Canada Job Bank website (https://www.jobbank.gc.ca).
"""

import argparse
import sys
from src.scraper import JobBankScraper, quick_search
from src.utils import save_jobs_to_file, load_search_config
from src.config import DEFAULT_OUTPUT_FORMAT
from src.database import JobBankDB


def show_database_stats():
    """Display database statistics."""
    try:
        with JobBankDB() as db:
            stats = db.get_stats()
            
            print("\n" + "=" * 60)
            print("📊 DATABASE STATISTICS")
            print("=" * 60)
            print(f"\n📋 Total jobs in database: {stats['total_jobs']}")
            print(f"  ✓ Active jobs: {stats['active_jobs']}")
            print(f"  ✗ Inactive jobs: {stats['inactive_jobs']}")
            print(f"\n🆕 Added in last 24 hours: {stats['added_last_24h']}")
            
            if stats['by_source']:
                print("\n📦 Jobs by source:")
                for source, count in stats['by_source'].items():
                    print(f"  • {source}: {count} jobs")
            
            print("\n" + "=" * 60)
    except Exception as e:
        print(f"❌ Error reading database: {str(e)}")
        sys.exit(1)


def export_database(output_file: str):
    """Export database to CSV file."""
    try:
        with JobBankDB() as db:
            print(f"\n📥 Exporting database to {output_file}...")
            db.export_to_csv(output_file, active_only=True)
            print("✅ Export complete!\n")
    except Exception as e:
        print(f"❌ Error exporting database: {str(e)}")
        sys.exit(1)


def run_batch_search(config_file: str, args):
    """
    Run multiple searches from a config file.
    
    Args:
        config_file: Path to YAML config file
        args: Command line arguments
    """
    try:
        config = load_search_config(config_file)
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ Config file error: {str(e)}")
        sys.exit(1)
    
    # Get global settings from config or args
    global_settings = config.get('settings', {})
    headless = not args.no_headless if hasattr(args, 'no_headless') else global_settings.get('headless', True)
    use_database = not args.no_db if hasattr(args, 'no_db') else global_settings.get('use_database', True)
    job_bank_only = args.job_bank_only if hasattr(args, 'job_bank_only') else global_settings.get('job_bank_only', False)
    output_format = args.format if hasattr(args, 'format') else global_settings.get('format', 'csv')
    
    searches = config['searches']
    total_jobs = 0
    
    print("=" * 60)
    print("🇨🇦  Canada Job Bank Scraper - Batch Mode")
    print("=" * 60)
    print(f"\n📋 Running {len(searches)} search(es)...\n")
    
    for i, search in enumerate(searches, 1):
        keyword = search.get('keyword', '')
        location = search.get('location', '')
        pages = search.get('pages', 1)
        
        print(f"\n[{i}/{len(searches)}] Searching: {keyword or 'Any'} in {location or 'Canada'}")
        print("-" * 60)
        
        try:
            jobs = quick_search(
                keyword=keyword,
                location=location,
                max_pages=pages,
                headless=headless,
                job_bank_only=job_bank_only,
                use_database=use_database
            )
            
            if jobs:
                # Generate filename from search params
                filename_parts = []
                if keyword:
                    filename_parts.append(keyword.replace(' ', '_'))
                if location:
                    filename_parts.append(location.replace(' ', '_').replace(',', ''))
                
                filename = '_'.join(filename_parts) if filename_parts else f'batch_search_{i}'
                
                save_jobs_to_file(jobs, filename=filename, format=output_format)
                total_jobs += len(jobs)
                print(f"✓ Found {len(jobs)} jobs")
            else:
                print("⚠️  No jobs found for this search")
                
        except Exception as e:
            print(f"❌ Error in search {i}: {str(e)}")
            continue
    
    print("\n" + "=" * 60)
    print("📊 Batch Search Complete")
    print(f"   Total jobs found: {total_jobs}")
    print(f"   Completed {len(searches)} search(es)")
    print("=" * 60)


def main():
    """Main function to run the scraper."""
    parser = argparse.ArgumentParser(
        description='Scrape jobs from Canada Job Bank',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for Python jobs in Toronto
  python main.py -k "python developer" -l "Toronto, ON" -p 3
  
  # Search for data analyst jobs anywhere in Canada
  python main.py -k "data analyst" -p 5
  
  # Search and save as JSON
  python main.py -k "software engineer" -l "Vancouver" -f json
  
  # Only show jobs posted directly on Job Bank (exclude Indeed, etc.)
  python main.py -k "developer" -l "Toronto" --job-bank-only
  
  # Run with visible browser (not headless)
  python main.py -k "project manager" --no-headless
        """
    )
    
    # Search parameters
    parser.add_argument(
        '-k', '--keyword',
        type=str,
        default='',
        help='Job keyword or title to search for'
    )
    
    parser.add_argument(
        '-l', '--location',
        type=str,
        default='',
        help='Location (city, province, or postal code)'
    )
    
    parser.add_argument(
        '-p', '--pages',
        type=int,
        default=1,
        help='Maximum number of pages to scrape (default: 1)'
    )
    
    # Output options
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output filename (without extension)'
    )
    
    parser.add_argument(
        '-f', '--format',
        type=str,
        choices=['csv', 'json', 'excel'],
        default=DEFAULT_OUTPUT_FORMAT,
        help=f'Output format (default: {DEFAULT_OUTPUT_FORMAT})'
    )
    
    # Browser options
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Run browser in visible mode (not headless)'
    )
    
    # Filter options
    parser.add_argument(
        '--job-bank-only',
        action='store_true',
        help='Only return jobs posted directly on Job Bank (exclude external sources like Indeed, CareerBeacon)'
    )
    
    # Database options
    parser.add_argument(
        '--no-db',
        action='store_true',
        help='Disable database storage (jobs will only be saved to file)'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show database statistics and exit'
    )
    
    parser.add_argument(
        '--export',
        type=str,
        metavar='FILE',
        help='Export database to CSV file and exit (e.g., --export jobs.csv)'
    )
    
    # Batch search option
    parser.add_argument(
        '-c', '--config',
        type=str,
        metavar='FILE',
        help='Run batch searches from a YAML config file (e.g., --config searches.yaml)'
    )
    
    args = parser.parse_args()
    
    # Handle database-only operations
    if args.stats:
        show_database_stats()
        sys.exit(0)
    
    if args.export:
        export_database(args.export)
        sys.exit(0)
    
    # Handle batch search from config file
    if args.config:
        run_batch_search(args.config, args)
        sys.exit(0)
    
    # Validate inputs for single search
    if not args.keyword and not args.location:
        print("⚠️  Please provide at least a keyword or location to search.")
        parser.print_help()
        sys.exit(1)
    
    try:
        # Run the scraper
        print("=" * 60)
        print("🇨🇦  Canada Job Bank Scraper")
        print("=" * 60)
        
        headless = not args.no_headless
        use_database = not args.no_db
        
        jobs = quick_search(
            keyword=args.keyword,
            location=args.location,
            max_pages=args.pages,
            headless=headless,
            job_bank_only=args.job_bank_only,
            use_database=use_database
        )
        
        if jobs:
            # Save results
            output_file = save_jobs_to_file(
                jobs, 
                filename=args.output,
                format=args.format
            )
            
            # Print summary
            print("\n" + "=" * 60)
            print("📊 Summary:")
            print(f"   Total jobs found: {len(jobs)}")
            print(f"   Output file: {output_file}")
            print("=" * 60)
        else:
            print("\n⚠️  No jobs found matching your criteria.")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Scraping interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
