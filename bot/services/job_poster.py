"""
Job Poster Service for Job Bank Telegram Bot

Handles:
- Triggering job scraping via API
- Fetching unposted jobs from database
- Filtering jobs by blacklist keywords
- Posting jobs to Telegram channels
- Marking jobs as posted
- Updating user statistics

Why this is separate:
- Core automation logic isolated
- Complex workflow needs clear structure
- Easy to test job posting flow
- Reusable across different contexts (scheduled, manual)
"""

import asyncio
import logging
from typing import Dict, Any, List
from telegram import Bot
from telegram.error import NetworkError, RetryAfter, TelegramError, TimedOut

from bot.services.api_client import JobBankAPI
from bot.services.config_manager import ConfigManager


class JobPoster:
    """Handles automated job checking and posting."""
    
    def __init__(self, api_client: JobBankAPI, config_manager: ConfigManager, bot: Bot):
        """
        Initialize job poster.
        
        Args:
            api_client: JobBankAPI instance
            config_manager: ConfigManager instance
            bot: Telegram Bot instance
        """
        self.api = api_client
        self.config_mgr = config_manager
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        
        # Track active users (user_id -> is_running status)
        self.active_users = {}
    
    async def check_and_post_jobs(self, user_id: int) -> int:
        """
        Check for new jobs and post them to user's channel.
        
        Complete workflow:
        1. Validate user configuration
        2. Trigger scraping for user's searches via API
        3. Fetch unposted jobs from API
        4. Filter by blacklist keywords
        5. Limit to max posts per run
        6. Post to Telegram channel
        7. Mark as posted via API
        8. Update user statistics
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Number of jobs posted
        """
        self.logger.info(f"Starting job check for user {user_id}")
        
        # Load user config
        config = self.config_mgr.load_user_config(user_id)
        
        # Validate configuration
        if not config.get('channel_id'):
            self.logger.warning(f"User {user_id} has no channel configured")
            return 0
        
        searches = config.get('searches', [])
        if not searches:
            self.logger.info(f"User {user_id} has no searches configured")
            return 0
        
        # Step 1: Trigger scraping for each search
        self.logger.info(f"Triggering scraping for {len(searches)} searches")
        
        # Track which search each job belongs to (for separator messages)
        from datetime import datetime
        search_info = {
            'timestamp': datetime.now(),
            'searches': searches,
            'job_bank_only': config['scraping'].get('job_bank_only', True)
        }
        
        for search in searches:
            try:
                keyword = search.get('keyword')
                location = search.get('location', 'Canada')
                pages = search.get('pages', 1000)
                job_bank_only = config['scraping'].get('job_bank_only', True)
                
                self.logger.info(f"Scraping: {keyword} in {location}")
                
                # Trigger scraping via API
                result = self.api.scrape_jobs(
                    user_id=user_id,
                    keyword=keyword,
                    location=location,
                    pages=pages,
                    job_bank_only=job_bank_only
                )
                
                self.logger.info(f"Scrape result: {result.get('jobs_found', 0)} jobs found")
                
            except Exception as e:
                self.logger.error(f"Error scraping for user {user_id}: {e}")
                continue
        
        # Step 2: Get all unposted jobs from API (no per-run cap on Telegram side)
        try:
            job_bank_only = config['scraping'].get('job_bank_only', True)
            request_limit = self.config_mgr.get_user_limit_request(user_id)
            unposted = self.api.get_unposted_jobs(
                user_id=user_id,
                job_bank_only=job_bank_only,
                limit=request_limit
            )
            self.logger.info(
                f"Found {len(unposted)} unposted jobs using user_limit_request={request_limit}"
            )
        except Exception as e:
            self.logger.error(f"Error fetching unposted jobs: {e}")
            return 0
        
        if not unposted:
            self.logger.info(f"No new jobs to post for user {user_id}")
            return 0
        
        # Step 3: Filter by blacklist
        blacklist = config.get('filters', {}).get('keywords_blacklist', [])
        if blacklist:
            filtered_jobs = self._filter_by_blacklist(unposted, blacklist)
            self.logger.info(
                f"Filtered {len(unposted) - len(filtered_jobs)} jobs by blacklist"
            )
            unposted = filtered_jobs
        
        if not unposted:
            self.logger.info(f"All jobs filtered by blacklist for user {user_id}")
            return 0
        
        # No cap: post all unposted jobs returned by the API
        jobs_to_post = unposted
        self.logger.info(f"Posting {len(jobs_to_post)} jobs (no per-run cap)")
        
        # Step 5: Post jobs to Telegram
        posted_count = await self._post_jobs_to_channel(
            user_id, jobs_to_post, config, search_info
        )
        
        # Step 6: Update user statistics
        self.config_mgr.increment_stat(user_id, 'posted_today', posted_count)
        self.config_mgr.increment_stat(user_id, 'total_posted', posted_count)
        
        self.logger.info(f"Successfully posted {posted_count} jobs for user {user_id}")
        return posted_count
    
    async def _post_jobs_to_channel(
        self, 
        user_id: int, 
        jobs: List[Dict[str, Any]], 
        config: Dict[str, Any],
        search_info: Dict[str, Any] = None
    ) -> int:
        """
        Post jobs to user's Telegram channel.
        
        Args:
            user_id: Telegram user ID
            jobs: List of job dictionaries
            config: User configuration
            search_info: Info about the search (timestamp, searches, job_bank_only)
            
        Returns:
            Number of jobs successfully posted
        """
        channel_id = config['channel_id']
        add_hashtags = config['posting'].get('add_hashtags', True)
        show_separator = config['posting'].get('show_search_separator', True)
        posted_count = 0
        
        # Post separator message if enabled
        if show_separator and search_info and jobs:
            try:
                await self._post_search_separator(channel_id, search_info, len(jobs))
            except Exception as e:
                self.logger.error(f"Error posting separator message: {e}")
        
        for index, job in enumerate(jobs, start=1):
            try:
                # Format job message
                message = self._format_job_message(job, add_hashtags)

                self.logger.info(
                    f"Posting job {index}/{len(jobs)} for user {user_id}: {job.get('job_id')}"
                )

                sent_message = await self._send_message_with_retry(
                    channel_id=channel_id,
                    message=message,
                    job_id=job.get('job_id')
                )

                self.logger.info(f"Posted job {job['job_id']} to channel")

                # Mark as posted via API
                try:
                    await self._mark_job_as_posted_with_retry(
                        user_id=user_id,
                        job_id=job['job_id'],
                        message_id=sent_message.message_id
                    )
                except Exception as e:
                    self.logger.error(f"Error marking job as posted: {e}")

                posted_count += 1

                # Respect configured delay between posts
                post_delay = config.get('user_post_delay', 3)
                await asyncio.sleep(post_delay)

            except TelegramError as e:
                # Log and continue - do not retry or wait
                self.logger.error(
                    f"Failed to post job {job.get('job_id')} for user {user_id}: {e}"
                )
                continue
            except Exception as e:
                self.logger.error(f"Unexpected error posting job: {e}")
                continue
        
        return posted_count

    async def _send_message_with_retry(self, channel_id: str, message: str, job_id: str, max_attempts: int = 3):
        """Send a Telegram message with retries for transient Telegram/network failures."""
        for attempt in range(1, max_attempts + 1):
            try:
                return await self.bot.send_message(
                    chat_id=channel_id,
                    text=message,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
            except RetryAfter as e:
                wait_seconds = int(getattr(e, "retry_after", 5)) + 1
                self.logger.warning(
                    f"Telegram rate limit while posting job {job_id}; "
                    f"retrying in {wait_seconds}s (attempt {attempt}/{max_attempts})"
                )
                await asyncio.sleep(wait_seconds)
            except (TimedOut, NetworkError) as e:
                if attempt == max_attempts:
                    raise
                wait_seconds = attempt * 5
                self.logger.warning(
                    f"Transient Telegram error while posting job {job_id}: {e}; "
                    f"retrying in {wait_seconds}s (attempt {attempt}/{max_attempts})"
                )
                await asyncio.sleep(wait_seconds)

        raise TelegramError(f"Failed to post job {job_id} after {max_attempts} attempts")

    async def _mark_job_as_posted_with_retry(
        self,
        user_id: int,
        job_id: str,
        message_id: int,
        max_attempts: int = 3
    ) -> None:
        """Mark a posted job in the API, retrying short-lived HTTP/API failures."""
        for attempt in range(1, max_attempts + 1):
            try:
                self.api.mark_jobs_as_posted(
                    user_id=user_id,
                    job_ids=[job_id],
                    message_ids=[message_id]
                )
                return
            except Exception:
                if attempt == max_attempts:
                    raise
                self.logger.warning(
                    f"Could not mark job {job_id} as posted; "
                    f"retrying (attempt {attempt}/{max_attempts})"
                )
                await asyncio.sleep(attempt * 2)
    
    def is_running(self, user_id: int) -> bool:
        """
        Check if bot is actively running for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if bot is running, False otherwise
        """
        return self.active_users.get(user_id, False)
    
    def start_user(self, user_id: int):
        """
        Mark user as having bot running.
        
        Args:
            user_id: Telegram user ID
        """
        self.active_users[user_id] = True
        self.logger.info(f"User {user_id} bot marked as running")
    
    def stop_user(self, user_id: int):
        """
        Mark user as having bot stopped.
        
        Args:
            user_id: Telegram user ID
        """
        self.active_users[user_id] = False
        self.logger.info(f"User {user_id} bot marked as stopped")
    
    def _filter_by_blacklist(
        self, 
        jobs: List[Dict[str, Any]], 
        blacklist: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Filter jobs by blacklist keywords.
        
        Checks job title and description for blacklisted keywords.
        
        Args:
            jobs: List of job dictionaries
            blacklist: List of blacklisted keywords
            
        Returns:
            Filtered list of jobs
        """
        if not blacklist:
            return jobs
        
        filtered_jobs = []
        
        for job in jobs:
            title_lower = job.get('title', '').lower()
            description_lower = job.get('description', '').lower()
            
            # Check if any blacklist keyword appears in title or description
            blacklisted = any(
                keyword.lower() in title_lower or keyword.lower() in description_lower
                for keyword in blacklist
            )
            
            if not blacklisted:
                filtered_jobs.append(job)
            else:
                self.logger.debug(
                    f"Filtered job '{job.get('title')}' due to blacklist"
                )
        
        return filtered_jobs
    
    async def _post_search_separator(
        self,
        channel_id: str,
        search_info: Dict[str, Any],
        job_count: int
    ):
        """
        Post a separator message before posting jobs.
        
        Args:
            channel_id: Telegram channel ID
            search_info: Info about the search (timestamp, searches, job_bank_only)
            job_count: Number of jobs being posted
        """
        from datetime import datetime
        
        timestamp = search_info.get('timestamp', datetime.now())
        searches = search_info.get('searches', [])
        job_bank_only = search_info.get('job_bank_only', True)
        
        # Format timestamp
        time_str = timestamp.strftime("%B %d, %Y at %I:%M %p")
        
        # Build search descriptions
        search_descriptions = []
        for search in searches:
            keyword = search.get('keyword', 'Unknown')
            location = search.get('location', 'Canada')
            search_descriptions.append(f"  • {keyword} in {location}")
        
        searches_text = "\n".join(search_descriptions) if search_descriptions else "  • No searches configured"
        
        # Build separator message
        message = f"<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        message += f"<b>📊 NEW JOB SEARCH RESULTS</b>\n"
        message += f"<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        message += f"🗓 <b>Date:</b> {time_str}\n"
        message += f"🔍 <b>Searches:</b>\n{searches_text}\n"
        message += f"🏢 <b>Source:</b> {'Job Bank Only' if job_bank_only else 'All Sources'}\n"
        message += f"📝 <b>Jobs Found:</b> {job_count}\n\n"
        message += f"<b>━━━━━━━━━━━━━━━━━━━━━━</b>"
        
        try:
            await self.bot.send_message(
                chat_id=channel_id,
                text=message,
                parse_mode='HTML'
            )
            self.logger.info(f"Posted search separator to channel")
        except Exception as e:
            self.logger.error(f"Failed to post separator: {e}")
            raise
    
    def _format_job_message(self, job: Dict[str, Any], add_hashtags: bool = True) -> str:
        """
        Format job data as a Telegram message.
        
        Args:
            job: Job dictionary from database
            add_hashtags: Whether to add hashtags
            
        Returns:
            Formatted message string
        """
        title = job.get('title', 'Unknown Title')
        company = job.get('company', 'Unknown Company')
        location = job.get('location', 'Unknown Location')
        salary = job.get('salary', 'Not specified')
        job_type = job.get('job_type', 'Not specified')
        date_posted = job.get('date_posted', 'Unknown')
        link = job.get('url', '')  # Database stores URL as 'url' not 'link'
        
        # Escape HTML special characters
        def escape_html(text):
            return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Build message using HTML formatting for better link support
        message = f"<b>{escape_html(title)}</b>\n\n"
        message += f"🏢 <b>Company:</b> {escape_html(company)}\n"
        message += f"📍 <b>Location:</b> {escape_html(location)}\n"
        message += f"💰 <b>Salary:</b> {escape_html(salary)}\n"
        message += f"📄 <b>Type:</b> {escape_html(job_type)}\n"
        message += f"📅 <b>Posted:</b> {escape_html(date_posted)}\n"
        
        if link:
            message += f"\n\n🔗 <b><a href=\"{link}\">Apply Here</a></b>"
        
        if add_hashtags:
            # Add relevant hashtags
            message += "\n\n#job #canada #hiring"
        
        return message


# Example usage
if __name__ == "__main__":
    """
    This shows how the job poster service would be used.
    """
    logging.basicConfig(level=logging.INFO)
    
    from bot.services.api_client import JobBankAPI
    from bot.services.config_manager import ConfigManager
    from telegram import Bot
    
    # Initialize components
    api = JobBankAPI(base_url="http://localhost:8000")
    config_mgr = ConfigManager()
    # bot = Bot(token="TELEGRAM_BOT_TOKEN_FROM_ENV")
    
    # job_poster = JobPoster(api, config_mgr, bot)
    
    print("Job Poster Service initialized")
    print("Handles: scraping trigger, job fetching, filtering, posting")
