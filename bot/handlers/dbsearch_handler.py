"""
Database Search Handler for Job Bank Telegram Bot

Handles:
- Database search menu display
- Search template parsing
- Executing database searches via API
- Displaying search results

Why this is separate:
- Database search is a distinct feature
- Complex search parameter parsing
- API integration isolated
- Easy to add search features
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from bot.services.api_client import JobBankAPI
from bot.services.config_manager import ConfigManager
from bot.ui import keyboards, messages


class DatabaseSearchHandler:
    """Handles job database search functionality."""
    
    def __init__(self, api_client: JobBankAPI, config_manager: ConfigManager):
        """
        Initialize database search handler.
        
        Args:
            api_client: JobBankAPI instance
        """
        self.api = api_client
        self.config_mgr = config_manager
        self.logger = logging.getLogger(__name__)
    
    async def show_db_search_menu(self, query, user_id: int):
        """
        Show database search template.
        
        Args:
            query: CallbackQuery from button press
            user_id: Telegram user ID
        """
        self.logger.info(f"Showing database search menu for user {user_id}")
        
        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="back_to_menu")]]
        
        await query.edit_message_text(
            messages.DB_SEARCH_TEMPLATE,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def handle_db_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Parse search template and execute database search.
        
        Expected format:
            dbsearch:
            keyword: Python
            location: Toronto
            min_salary: 50000
        
        All fields are optional.
        
        Args:
            update: Update with message
            context: Callback context
        """
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        self.logger.info(f"Processing database search from user {user_id}")
        
        try:
            # Parse search template
            search_params = self._parse_search_template(text)
            
            self.logger.info(f"Search params: {search_params}")
            
            # Show searching message
            searching_msg = await update.message.reply_text(
                "🔍 Searching database...",
                parse_mode='Markdown'
            )
            
            # Execute search via API using the user's configured request limit.
            user_limit = self.config_mgr.get_user_limit_request(user_id)
            
            results = self.api.search_jobs(
                user_id=user_id,
                keyword=search_params.get('keyword'),
                location=search_params.get('location'),
                min_salary=search_params.get('min_salary'),
                limit=user_limit
            )
            
            # Delete searching message
            await searching_msg.delete()
            
            # Extract jobs list from API response
            jobs_list = results.get('jobs', [])
            total_jobs = results.get('total', 0)
            
            # Format and send results
            if not jobs_list or len(jobs_list) == 0:
                await update.message.reply_text(
                    "🔍 *Search Results*\n\n"
                    "No jobs found matching your criteria.\n\n"
                    "Try adjusting your search filters.",
                    parse_mode='Markdown'
                )
                return
            
            # Format results message
            result_message = self._format_search_results(jobs_list, search_params, total_jobs)
            
            await update.message.reply_text(
                result_message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
        except Exception as e:
            self.logger.error(f"Error performing database search: {e}")
            await update.message.reply_text(
                messages.ERROR_GENERAL + "\n\n" + messages.DB_SEARCH_TEMPLATE,
                parse_mode='Markdown'
            )
    
    def _parse_search_template(self, text: str) -> dict:
        """
        Parse database search template into parameters.
        
        Args:
            text: Template text from user
            
        Returns:
            Dictionary with search parameters
        """
        lines = text.split('\n')
        search_params = {}
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and header
            if not line or line.lower() == 'dbsearch:' or line.startswith('#'):
                continue
            
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                # Only add if value is not empty
                if value:
                    if key == 'keyword':
                        search_params['keyword'] = value
                    elif key == 'location':
                        search_params['location'] = value
                    elif key in ('min_salary', 'salary', 'minsalary'):
                        try:
                            search_params['min_salary'] = float(value)
                        except ValueError:
                            self.logger.warning(f"Invalid salary value: {value}")
        
        return search_params
    
    def _format_search_results(self, results: list, search_params: dict, total: int = None) -> str:
        """
        Format search results into a readable message.
        
        Args:
            results: List of job dictionaries from API
            search_params: Search parameters used
            total: Total number of jobs (from API response)
            
        Returns:
            Formatted message string
        """
        if total is None:
            total = len(results)
        
        # Build criteria string
        criteria_parts = []
        if search_params.get('keyword'):
            criteria_parts.append(f"Keyword: *{search_params['keyword']}*")
        if search_params.get('location'):
            criteria_parts.append(f"Location: *{search_params['location']}*")
        if search_params.get('min_salary'):
            criteria_parts.append(f"Min Salary: *${search_params['min_salary']:,.0f}*")
        
        criteria_str = ", ".join(criteria_parts) if criteria_parts else "All jobs"
        
        # Build message
        message = f"🔍 *Search Results*\n\n"
        message += f"Criteria: {criteria_str}\n"
        message += f"Found: **{total} jobs**\n\n"
        
        # Add job listings
        for i, job in enumerate(results[:10], 1):
            title = job.get('title', 'Unknown')
            company = job.get('company', 'Unknown Company')
            location = job.get('location', 'Unknown Location')
            salary = job.get('salary', 'Not specified')
            
            message += f"**{i}. {title}**\n"
            message += f"   🏢 {company}\n"
            message += f"   📍 {location}\n"
            message += f"   💰 {salary}\n\n"
        
        if total > 10:
            message += f"\n_Showing first 10 of {total} results_"
        
        return message


# Example usage
if __name__ == "__main__":
    """
    This shows how the database search handler would be used.
    """
    logging.basicConfig(level=logging.INFO)
    
    from bot.services.api_client import JobBankAPI
    from bot.services.config_manager import ConfigManager
    
    api = JobBankAPI(base_url="http://localhost:8000")
    config_mgr = ConfigManager()
    db_search_handler = DatabaseSearchHandler(api, config_mgr)
    
    # Test parsing
    template = """
    dbsearch:
    keyword: Python Developer
    location: Toronto
    min_salary: 80000
    """
    
    params = db_search_handler._parse_search_template(template)
    print(f"Parsed search params: {params}")
