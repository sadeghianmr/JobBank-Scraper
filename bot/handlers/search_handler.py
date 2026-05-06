"""
Search Handler for Job Bank Telegram Bot

Handles:
- Searches menu display
- Adding new searches (template-based)
- Removing searches
- Search template parsing

Why this is separate:
- Search management is a core feature
- Complex parsing logic isolated
- Easy to modify search flow
- Testable search validation
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from bot.services.config_manager import ConfigManager
from bot.ui import keyboards, messages


class SearchHandler:
    """Handles job search configuration."""
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize search handler.
        
        Args:
            config_manager: ConfigManager instance
        """
        self.config_mgr = config_manager
        self.logger = logging.getLogger(__name__)
    
    async def show_searches_menu(self, query, user_id: int):
        """
        Show searches management menu.
        
        Displays:
        - List of active searches
        - Buttons to remove each search
        - Button to add new search
        
        Args:
            query: CallbackQuery from button press
            user_id: Telegram user ID
        """
        self.logger.info(f"Showing searches menu for user {user_id}")
        
        config = self.config_mgr.load_user_config(user_id)
        searches = config.get('searches', [])
        
        if not searches:
            # No searches configured
            message = messages.SEARCHES_MENU.format(
                search_list=messages.NO_SEARCHES,
                count=0
            )
            keyboard = [
                [InlineKeyboardButton("➕ Add Search", callback_data="add_new_search")],
                [InlineKeyboardButton("« Back to Menu", callback_data="back_to_menu")]
            ]
        else:
            # Build search list
            search_list = ""
            keyboard = []
            
            for i, search in enumerate(searches, 1):
                keyword = search.get('keyword', 'Any')
                location = search.get('location', 'Canada')
                pages = search.get('pages', 1000)
                
                search_list += f"{i}. **{keyword}** in {location} ({pages} pages)\n"
                keyboard.append([
                    InlineKeyboardButton(f"❌ Remove #{i}", callback_data=f"search_remove_{i-1}")
                ])
            
            message = messages.SEARCHES_MENU.format(
                search_list=search_list.strip(),
                count=len(searches)
            )
            
            keyboard.append([InlineKeyboardButton("➕ Add Search", callback_data="add_new_search")])
            keyboard.append([InlineKeyboardButton("« Back to Menu", callback_data="back_to_menu")])
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def show_add_search_template(self, query, user_id: int):
        """
        Show template for adding a new search.
        
        Args:
            query: CallbackQuery from button press
            user_id: Telegram user ID
        """
        self.logger.info(f"Showing add search template for user {user_id}")
        
        keyboard = [[InlineKeyboardButton("« Back to Searches", callback_data="menu_searches")]]
        
        await query.edit_message_text(
            messages.ADD_SEARCH_TEMPLATE,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def handle_add_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Parse and add a new search from user's template message.
        
        Expected format:
            search:
            keyword: Python Developer
            location: Toronto, ON
            pages: 500
        
        Args:
            update: Update with message
            context: Callback context
        """
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        self.logger.info(f"Processing add search from user {user_id}")
        
        try:
            # Parse search template
            search_data = self._parse_search_template(text)
            
            # Validate required fields
            is_valid, error_msg = self._validate_search(search_data)
            if not is_valid:
                await update.message.reply_text(
                    f"❌ {error_msg}\n\n" + messages.ADD_SEARCH_TEMPLATE,
                    parse_mode='Markdown'
                )
                return
            
            # Set defaults
            if 'location' not in search_data:
                search_data['location'] = 'Canada'
            if 'pages' not in search_data:
                search_data['pages'] = 1000
            
            # Add search
            added = self.config_mgr.add_search(user_id, search_data)
            
            if added:
                # Success
                success_msg = messages.SEARCH_ADDED.format(
                    keyword=search_data['keyword'],
                    location=search_data['location'],
                    pages=search_data['pages']
                )
                await update.message.reply_text(success_msg, parse_mode='Markdown')
            else:
                # Already exists
                await update.message.reply_text(
                    "ℹ️ This search already exists in your configuration.",
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            self.logger.error(f"Error parsing search for user {user_id}: {e}")
            await update.message.reply_text(
                messages.ERROR_INVALID_FORMAT + "\n\n" + messages.ADD_SEARCH_TEMPLATE,
                parse_mode='Markdown'
            )
    
    async def handle_remove_search(self, query, user_id: int, index: int):
        """
        Remove a search by index.
        
        Args:
            query: CallbackQuery from button press
            user_id: Telegram user ID
            index: Index of search to remove (0-based)
        """
        self.logger.info(f"Removing search index {index} for user {user_id}")
        
        removed = self.config_mgr.remove_search(user_id, index)
        
        if removed:
            await query.answer("✅ Search removed")
        else:
            await query.answer("❌ Search not found", show_alert=True)
        
        # Refresh searches menu
        await self.show_searches_menu(query, user_id)
    
    def _parse_search_template(self, text: str) -> dict:
        """
        Parse search template text into dictionary.
        
        Args:
            text: Template text from user
            
        Returns:
            Dictionary with search parameters
        """
        lines = text.split('\n')
        search_data = {}
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line == 'search:':
                continue
            
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'keyword':
                    search_data['keyword'] = value
                elif key == 'location':
                    search_data['location'] = value
                elif key == 'pages':
                    try:
                        search_data['pages'] = int(value)
                    except ValueError:
                        search_data['pages'] = 1000
        
        return search_data
    
    def _validate_search(self, search_data: dict) -> tuple[bool, str]:
        """
        Validate search data.
        
        Args:
            search_data: Parsed search dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required field
        if 'keyword' not in search_data or not search_data['keyword']:
            return False, "Missing required field: `keyword`"
        
        # Validate pages if present
        if 'pages' in search_data:
            pages = search_data['pages']
            if pages < 1:
                return False, "Pages must be at least 1"
            if pages > 5000:
                return False, "Pages cannot exceed 5000 (too many)"
        
        return True, ""


# Example usage
if __name__ == "__main__":
    """
    This shows how the search handler would be used.
    """
    logging.basicConfig(level=logging.INFO)
    
    from bot.services.config_manager import ConfigManager
    
    config_mgr = ConfigManager()
    search_handler = SearchHandler(config_mgr)
    
    # Test parsing
    template = """
    search:
    keyword: Python Developer
    location: Toronto, ON
    pages: 500
    """
    
    search_data = search_handler._parse_search_template(template)
    print(f"Parsed search: {search_data}")
    
    is_valid, error = search_handler._validate_search(search_data)
    print(f"Valid: {is_valid}, Error: {error}")
