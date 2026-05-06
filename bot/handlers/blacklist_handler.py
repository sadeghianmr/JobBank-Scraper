"""
Blacklist Handler for Job Bank Telegram Bot

Handles:
- Blacklist menu display
- Adding blacklist keywords (template-based)
- Removing blacklist keywords
- Blacklist template parsing

Why this is separate:
- Blacklist is a key filtering feature
- Simple but needs its own UI flow
- Easy to modify blacklist logic
- Testable keyword validation
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from bot.services.config_manager import ConfigManager
from bot.ui import keyboards, messages


class BlacklistHandler:
    """Handles blacklist keyword configuration."""
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize blacklist handler.
        
        Args:
            config_manager: ConfigManager instance
        """
        self.config_mgr = config_manager
        self.logger = logging.getLogger(__name__)
    
    async def show_blacklist_menu(self, query, user_id: int):
        """
        Show blacklist management menu.
        
        Displays:
        - List of blacklisted keywords
        - Buttons to remove each keyword
        - Button to add new keywords
        
        Args:
            query: CallbackQuery from button press
            user_id: Telegram user ID
        """
        self.logger.info(f"Showing blacklist menu for user {user_id}")
        
        config = self.config_mgr.load_user_config(user_id)
        blacklist = config.get('filters', {}).get('keywords_blacklist', [])
        
        if not blacklist:
            # No blacklist keywords
            message = messages.BLACKLIST_MENU.format(
                blacklist_list=messages.NO_BLACKLIST,
                count=0
            )
            keyboard = [
                [InlineKeyboardButton("➕ Add Keywords", callback_data="add_blacklist")],
                [InlineKeyboardButton("« Back to Menu", callback_data="back_to_menu")]
            ]
        else:
            # Build keyword list
            keyword_list = ""
            keyboard = []
            
            for i, keyword in enumerate(blacklist):
                keyword_list += f"• {keyword}\n"
                keyboard.append([
                    InlineKeyboardButton(f"❌ Remove '{keyword}'", callback_data=f"blacklist_remove_{i}")
                ])
            
            message = messages.BLACKLIST_MENU.format(
                blacklist_list=keyword_list.strip(),
                count=len(blacklist)
            )
            
            keyboard.append([InlineKeyboardButton("➕ Add Keywords", callback_data="add_blacklist")])
            keyboard.append([InlineKeyboardButton("« Back to Menu", callback_data="back_to_menu")])
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def show_add_blacklist_template(self, query, user_id: int):
        """
        Show template for adding blacklist keywords.
        
        Args:
            query: CallbackQuery from button press
            user_id: Telegram user ID
        """
        self.logger.info(f"Showing add blacklist template for user {user_id}")
        
        keyboard = [[InlineKeyboardButton("« Back to Blacklist", callback_data="menu_blacklist")]]
        
        await query.edit_message_text(
            messages.ADD_BLACKLIST_TEMPLATE,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def handle_add_blacklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Parse and add blacklist keywords from user's template message.
        
        Expected format:
            blacklist:
            - keyword1
            - keyword2
            - keyword3
        
        Or simpler format (just keywords, one per line):
            unpaid
            volunteer
            commission only
        
        Args:
            update: Update with message
            context: Callback context
        """
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        self.logger.info(f"Processing add blacklist from user {user_id}")
        
        try:
            # Parse blacklist template
            keywords = self._parse_blacklist_template(text)
            
            if not keywords:
                await update.message.reply_text(
                    "❌ No keywords found.\n\n" + messages.ADD_BLACKLIST_TEMPLATE,
                    parse_mode='Markdown'
                )
                return
            
            # Add keywords
            added_count = 0
            added_keywords = []
            
            for keyword in keywords:
                # Validate keyword
                if not self._is_valid_keyword(keyword):
                    continue
                
                # Add to config
                if self.config_mgr.add_blacklist_keyword(user_id, keyword):
                    added_count += 1
                    added_keywords.append(keyword)
            
            if added_count > 0:
                # Success
                keyword_str = ", ".join(f"'{k}'" for k in added_keywords)
                success_msg = messages.BLACKLIST_ADDED.format(
                    count=added_count,
                    keywords=keyword_str
                )
                await update.message.reply_text(success_msg, parse_mode='Markdown')
            else:
                # All already existed or invalid
                await update.message.reply_text(
                    "ℹ️ All keywords already exist in your blacklist or are invalid.",
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            self.logger.error(f"Error parsing blacklist for user {user_id}: {e}")
            await update.message.reply_text(
                messages.ERROR_INVALID_FORMAT + "\n\n" + messages.ADD_BLACKLIST_TEMPLATE,
                parse_mode='Markdown'
            )
    
    async def handle_remove_blacklist(self, query, user_id: int, index: int):
        """
        Remove a blacklist keyword by index.
        
        Args:
            query: CallbackQuery from button press
            user_id: Telegram user ID
            index: Index of keyword to remove (0-based)
        """
        self.logger.info(f"Removing blacklist keyword index {index} for user {user_id}")
        
        # Get keyword for confirmation message
        config = self.config_mgr.load_user_config(user_id)
        blacklist = config.get('filters', {}).get('keywords_blacklist', [])
        
        if 0 <= index < len(blacklist):
            keyword = blacklist[index]
            removed = self.config_mgr.remove_blacklist_keyword(user_id, index)
            
            if removed:
                await query.answer(f"✅ Removed '{keyword}'")
            else:
                await query.answer("❌ Keyword not found", show_alert=True)
        else:
            await query.answer("❌ Keyword not found", show_alert=True)
        
        # Refresh blacklist menu
        await self.show_blacklist_menu(query, user_id)
    
    def _parse_blacklist_template(self, text: str) -> list:
        """
        Parse blacklist template text into list of keywords.
        
        Supports two formats:
        1. List format: "- keyword"
        2. Simple format: one keyword per line
        
        Args:
            text: Template text from user
            
        Returns:
            List of keywords
        """
        lines = text.split('\n')
        keywords = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and the "blacklist:" header
            if not line or line.lower() == 'blacklist:' or line.startswith('#'):
                continue
            
            # List format: "- keyword"
            if line.startswith('- '):
                keyword = line[2:].strip()
                if keyword:
                    keywords.append(keyword)
            
            # Simple format: just the keyword
            elif ':' not in line:  # Avoid catching template lines like "blacklist:"
                keywords.append(line)
        
        return keywords
    
    def _is_valid_keyword(self, keyword: str) -> bool:
        """
        Validate a blacklist keyword.
        
        Args:
            keyword: Keyword to validate
            
        Returns:
            True if keyword is valid
        """
        # Must not be empty
        if not keyword or not keyword.strip():
            return False
        
        # Must be reasonable length
        if len(keyword) < 2:
            return False
        
        if len(keyword) > 100:
            return False
        
        return True


# Example usage
if __name__ == "__main__":
    """
    This shows how the blacklist handler would be used.
    """
    logging.basicConfig(level=logging.INFO)
    
    from bot.services.config_manager import ConfigManager
    
    config_mgr = ConfigManager()
    blacklist_handler = BlacklistHandler(config_mgr)
    
    # Test parsing
    template1 = """
    blacklist:
    - unpaid
    - volunteer
    - commission only
    """
    
    template2 = """
    unpaid
    volunteer
    commission only
    """
    
    keywords1 = blacklist_handler._parse_blacklist_template(template1)
    print(f"Parsed (list format): {keywords1}")
    
    keywords2 = blacklist_handler._parse_blacklist_template(template2)
    print(f"Parsed (simple format): {keywords2}")
