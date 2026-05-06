"""
Main entry point for the modular Job Bank Telegram Bot.

This module wires together all handlers and services to create
the complete bot application.

Why this architecture?
- **Modular**: Each feature is a separate handler
- **Testable**: Components can be tested in isolation
- **Maintainable**: Easy to understand and modify
- **Scalable**: Easy to add new features

To run:
    python -m bot.main

Or from project root:
    python -m bot.main
"""

import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)

# Import services
from bot.services.api_client import JobBankAPI
from bot.services.config_manager import ConfigManager
from bot.services.job_poster import JobPoster

# Import handlers
from bot.handlers.setup_handler import SetupHandler
from bot.handlers.menu_handler import MenuHandler
from bot.handlers.search_handler import SearchHandler
from bot.handlers.blacklist_handler import BlacklistHandler
from bot.handlers.dbsearch_handler import DatabaseSearchHandler
from bot.handlers.settings_handler import SettingsHandler

# Import UI components (not directly used but good to import for validation)
from bot.ui import keyboards, messages
from src.logging_config import configure_logging


class JobBankBot:
    """
    Main bot application that orchestrates all handlers and services.
    
    This class:
    - Initializes all services (API client, config manager, job poster)
    - Creates all handlers (setup, menu, searches, etc.)
    - Registers command and callback handlers with Telegram
    - Manages the bot lifecycle (start, run, stop)
    """
    
    def __init__(self, bot_token: str, api_base_url: str = "http://localhost:8000"):
        """
        Initialize the bot.
        
        Args:
            bot_token: Telegram bot token
            api_base_url: Base URL for the JobBank API
        """
        self.bot_token = bot_token
        self.api_base_url = api_base_url
        
        # Setup logging
        self.logger = configure_logging(__name__, "bot/bot.log")
        
        # Will be initialized in initialize()
        self.application = None
        self.bot = None
        
        # Services
        self.api_client = None
        self.config_mgr = None
        self.job_poster = None
        
        # Handlers
        self.setup_handler = None
        self.menu_handler = None
        self.search_handler = None
        self.blacklist_handler = None
        self.dbsearch_handler = None
        self.settings_handler = None
        
        self.logger.info("JobBankBot instance created (Modular Architecture v2.0)")
    
    async def initialize(self):
        """
        Initialize all bot components.
        
        Order of operations:
        1. Create Telegram Application
        2. Initialize services (API client, config manager, job poster)
        3. Initialize handlers
        4. Register command handlers
        5. Register message handlers (for templates)
        6. Register callback query handlers (for buttons)
        """
        self.logger.info("Initializing bot...")
        
        # 1. Create Telegram Application
        self.application = Application.builder().token(self.bot_token).build()
        self.bot = self.application.bot
        
        # 2. Initialize services
        self.logger.info("Initializing services...")
        self.api_client = JobBankAPI(base_url=self.api_base_url)
        self.config_mgr = ConfigManager()
        self.job_poster = JobPoster(self.api_client, self.config_mgr, self.bot)
        
        # 3. Initialize handlers
        self.logger.info("Initializing handlers...")
        self.setup_handler = SetupHandler(self.config_mgr, self.bot)
        self.setup_handler.set_job_poster(self.job_poster)  # Inject job poster
        self.menu_handler = MenuHandler(self.config_mgr)
        self.menu_handler.set_job_poster(self.job_poster)  # Inject job poster
        self.search_handler = SearchHandler(self.config_mgr)
        self.blacklist_handler = BlacklistHandler(self.config_mgr)
        self.dbsearch_handler = DatabaseSearchHandler(self.api_client, self.config_mgr)
        self.settings_handler = SettingsHandler(self.config_mgr, self.api_client, self.bot)
        
        # 4. Register command handlers
        self.logger.info("Registering command handlers...")
        self.application.add_handler(CommandHandler("start", self.setup_handler.handle_start))
        self.application.add_handler(CommandHandler("setup", self.setup_handler.handle_setup))
        self.application.add_handler(CommandHandler("menu", self.menu_handler.handle_menu))
        self.application.add_handler(CommandHandler("help", self._handle_help))
        
        # 5. Register message handlers for templates
        # Order matters! More specific patterns first
        self.logger.info("Registering message handlers...")
        
        # Config template: contains "channel_id:" and "interval" (MUST be first for initial setup)
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & (
                    filters.Regex(r'(?i)channel_id:') | filters.Regex(r'(?i)interval')
                ),
                self._route_config_message
            )
        )
        
        # Database search template: contains "dbsearch:" (case-insensitive)
        # MUST be before search handler since it also contains "keyword:"
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.Regex(r'(?i)dbsearch:'),
                self.dbsearch_handler.handle_db_search
            )
        )
        
        # Blacklist template: contains "blacklist:" or multiple lines starting with "-" (case-insensitive)
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.Regex(r'(?i)blacklist:'),
                self.blacklist_handler.handle_add_blacklist
            )
        )
        
        # Search template: contains "search:" or "keyword:" (case-insensitive)
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & (
                    filters.Regex(r'(?i)search:') | filters.Regex(r'(?i)keyword:')
                ),
                self.search_handler.handle_add_search
            )
        )
        
        # 6. Register callback query handler (must be last)
        self.logger.info("Registering callback query handler...")
        self.application.add_handler(CallbackQueryHandler(self._handle_callback))
        
        self.logger.info("✅ Bot initialized successfully!")
    
    async def _route_config_message(self, update, context):
        """
        Route config messages to appropriate handler.
        
        Config messages can be:
        - Initial setup (handle_config_message)
        - Config update (handle_update_config)
        """
        user_id = update.effective_user.id
        
        # Check if user is configured
        if self.config_mgr.is_user_configured(user_id):
            # Existing user updating config
            await self.settings_handler.handle_update_config(update, context)
        else:
            # New user doing initial setup
            await self.setup_handler.handle_config_message(update, context)
    
    async def _handle_callback(self, update, context):
        """
        Central callback query router.
        
        Routes button callbacks to appropriate handlers based on callback data.
        """
        query = update.callback_query
        user_id = query.from_user.id
        action = query.data
        
        self.logger.debug(f"Callback: {action} from user {user_id}")
        
        # Answer callback to remove loading state
        await query.answer()
        
        # Route to appropriate handler
        if action == "back_to_menu":
            await self.menu_handler.show_menu(query, user_id)
        
        elif action == "action_check":
            await self.menu_handler.handle_check_now(query, user_id)
        
        elif action == "menu_searches":
            await self.search_handler.show_searches_menu(query, user_id)
        
        elif action == "add_new_search":
            await self.search_handler.show_add_search_template(query, user_id)
        
        elif action.startswith("search_remove_"):
            index = int(action.replace("search_remove_", ""))
            await self.search_handler.handle_remove_search(query, user_id, index)
        
        elif action == "menu_blacklist":
            await self.blacklist_handler.show_blacklist_menu(query, user_id)
        
        elif action == "add_blacklist":
            await self.blacklist_handler.show_add_blacklist_template(query, user_id)
        
        elif action.startswith("blacklist_remove_"):
            index = int(action.replace("blacklist_remove_", ""))
            await self.blacklist_handler.handle_remove_blacklist(query, user_id, index)
        
        elif action == "menu_db_search":
            await self.dbsearch_handler.show_db_search_menu(query, user_id)
        
        elif action == "menu_stats":
            await self.settings_handler.show_stats(query, user_id)
        
        elif action == "menu_config":
            await self.settings_handler.show_settings_menu(query, user_id)
        
        elif action == "menu_update_config":
            await self.settings_handler.show_update_config_template(query, user_id)
        
        else:
            self.logger.warning(f"Unknown callback action: {action}")
            await query.answer("Unknown action", show_alert=True)
    
    async def _handle_help(self, update, context):
        """Handle /help command."""
        await update.message.reply_text(
            messages.HELP_MESSAGE,
            parse_mode='Markdown'
        )
    
    async def run(self):
        """
        Run the bot.
        
        This starts the bot and keeps it running until interrupted.
        """
        await self.initialize()
        
        self.logger.info("🤖 Bot is running! Press Ctrl+C to stop.")
        
        # Start the bot
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal...")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Gracefully shutdown the bot."""
        self.logger.info("Shutting down bot...")
        
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
        
        self.logger.info("✅ Bot stopped successfully")


async def main():
    """
    Main entry point for the bot application.
    
    Loads environment configuration and starts the bot.
    """
    load_dotenv()

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    api_url = os.getenv("API_BASE_URL", "http://localhost:8000")

    if not bot_token:
        print("❌ Error: TELEGRAM_BOT_TOKEN is not set")
        print("\nCreate a .env file from .env.example and add your Telegram bot token.")
        return

    # Create and run bot
    bot = JobBankBot(bot_token=bot_token, api_base_url=api_url)
    await bot.run()


if __name__ == "__main__":
    """
    Run the bot when this file is executed directly.
    
    Usage:
        python -m bot.main
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
