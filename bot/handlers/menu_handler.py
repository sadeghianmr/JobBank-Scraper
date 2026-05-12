"""
Menu Handler for Job Bank Telegram Bot

Handles:
- /menu command
- Main menu display
- "Check Now" manual job checking
- Routing between different menus

Why this is separate:
- Central navigation hub
- Routes to other handlers
- Keeps routing logic in one place
- Easy to add new menu items
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from bot.services.config_manager import ConfigManager
from bot.ui import keyboards, messages


class MenuHandler:
    """Handles bot menu navigation and display."""
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize menu handler.
        
        Args:
            config_manager: ConfigManager instance
        """
        self.config_mgr = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Job poster will be set by main bot
        self.job_poster = None

    async def _safe_answer(self, query, *args, **kwargs):
        """Answer a callback query, ignoring stale Telegram callback IDs."""
        try:
            await query.answer(*args, **kwargs)
        except TelegramError as e:
            self.logger.warning(f"Could not answer callback: {e}")
    
    def set_job_poster(self, job_poster):
        """
        Set job poster service (called by main bot).
        
        Args:
            job_poster: JobPoster instance
        """
        self.job_poster = job_poster
    
    async def handle_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /menu command - Show main menu.
        
        Displays:
        - Bot status (running/stopped)
        - Current configuration summary
        - Navigation buttons
        """
        user_id = update.effective_user.id
        self.logger.info(f"/menu from user {user_id}")
        
        # Load user config
        config = self.config_mgr.load_user_config(user_id)
        
        # Check if user is configured
        if not self.config_mgr.is_user_configured(user_id):
            await update.message.reply_text(
                messages.ERROR_NO_CONFIG,
                parse_mode='Markdown'
            )
            return
        
        # Build status message
        channel_id = config.get('channel_id', 'Not set')
        searches_count = len(config.get('searches', []))
        blacklist_count = len(config.get('filters', {}).get('keywords_blacklist', []))
        
        # Check if bot is running (job poster active)
        is_running = self.job_poster and self.job_poster.is_running(user_id) if self.job_poster else False
        status = "✅ Running" if is_running else "⏸️ Stopped"
        
        menu_text = messages.MAIN_MENU + f"\n" + (
            f"Status: {status}\n"
            f"📬 Channel: `{channel_id}`\n"
            f"🔍 Searches: {searches_count}\n"
            f"🚫 Blacklist: {blacklist_count} keywords"
        )
        
        await update.message.reply_text(
            menu_text,
            reply_markup=keyboards.main_menu_keyboard(has_searches=(searches_count > 0)),
            parse_mode='Markdown'
        )
    
    async def show_menu(self, query, user_id: int):
        """
        Show main menu (callback from buttons).
        
        Args:
            query: CallbackQuery from button press
            user_id: Telegram user ID
        """
        self.logger.info(f"Showing main menu for user {user_id}")
        
        # Load user config
        config = self.config_mgr.load_user_config(user_id)
        
        # Build status message
        channel_id = config.get('channel_id', 'Not set')
        searches_count = len(config.get('searches', []))
        blacklist_count = len(config.get('filters', {}).get('keywords_blacklist', []))
        
        # Check if bot is running (job poster active)
        is_running = self.job_poster and self.job_poster.is_running(user_id) if self.job_poster else False
        status = "✅ Running" if is_running else "⏸️ Stopped"
        
        menu_text = messages.MAIN_MENU + f"\n" + (
            f"Status: {status}\n"
            f"📬 Channel: `{channel_id}`\n"
            f"🔍 Searches: {searches_count}\n"
            f"🚫 Blacklist: {blacklist_count} keywords"
        )
        
        await query.edit_message_text(
            menu_text,
            reply_markup=keyboards.main_menu_keyboard(has_searches=(searches_count > 0)),
            parse_mode='Markdown'
        )
    
    async def handle_check_now(self, query, user_id: int):
        """
        Handle "Check for Jobs Now" button.
        
        Triggers manual job check and posts new jobs to channel.
        
        Args:
            query: CallbackQuery from button press
            user_id: Telegram user ID
        """
        self.logger.info(f"Manual job check requested by user {user_id}")
        
        # Check if user is configured
        if not self.config_mgr.is_user_configured(user_id):
            await self._safe_answer(query, "❌ Please configure your bot first!", show_alert=True)
            return
        
        # Check if user has searches configured
        config = self.config_mgr.load_user_config(user_id)
        if not config.get('searches'):
            await self._safe_answer(
                query,
                "❌ No searches configured! Add some searches first.",
                show_alert=True
            )
            return
        
        # Show checking message
        await query.edit_message_text(
            messages.CHECKING_JOBS,
            parse_mode='Markdown'
        )
        
        try:
            # Trigger job check and posting
            if self.job_poster:
                posted_count = await self.job_poster.check_and_post_jobs(user_id)
                summary = self.job_poster.get_last_run_summary(user_id)

                if summary:
                    result_message = self.job_poster.format_run_summary(
                        summary,
                        status="✅ Manual check complete"
                    )
                else:
                    result_message = messages.CHECKING_COMPLETE.format(
                        new_jobs=posted_count,
                        posted_jobs=posted_count
                    )
                
                await query.edit_message_text(
                    result_message,
                    reply_markup=keyboards.back_to_menu_keyboard(),
                )
            else:
                # Job poster not initialized yet
                await query.edit_message_text(
                    "⚠️ Job checking service is not ready yet.",
                    reply_markup=keyboards.back_to_menu_keyboard(),
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            self.logger.error(f"Error checking jobs for user {user_id}: {e}")
            await query.edit_message_text(
                messages.ERROR_GENERAL + "\n\nPlease try again.",
                reply_markup=keyboards.back_to_menu_keyboard(),
                parse_mode='Markdown'
            )
    
    async def route_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Route button callbacks to appropriate handlers.
        
        This is the main callback dispatcher for menu navigation.
        Other handlers will handle their own specific callbacks.
        
        Args:
            update: Update with callback query
            context: Callback context
            
        Returns:
            str: Action type for further routing by main bot
        """
        query = update.callback_query
        user_id = query.from_user.id
        action = query.data
        
        self.logger.debug(f"Button callback: {action} from user {user_id}")
        
        # Answer callback to stop loading indicator
        await self._safe_answer(query)
        
        # Route based on action
        if action == "back_to_menu":
            await self.show_menu(query, user_id)
            return "menu"
        
        elif action == "action_check":
            await self.handle_check_now(query, user_id)
            return "check"
        
        else:
            # Return action for main bot to route to other handlers
            return action


# Example usage
if __name__ == "__main__":
    """
    This shows how the menu handler would be used in the main bot.
    """
    logging.basicConfig(level=logging.INFO)
    
    from bot.services.config_manager import ConfigManager
    
    config_mgr = ConfigManager()
    menu_handler = MenuHandler(config_mgr)
    
    print("Menu Handler initialized")
    print("Handles: /menu command, main menu display, navigation routing")
