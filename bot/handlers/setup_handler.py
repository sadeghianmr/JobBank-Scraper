"""
Setup Handler for Job Bank Telegram Bot

Handles:
- /start command - Initial user greeting and bot activation
- /setup command - Show setup instructions
- Configuration parsing - Process user's config template

Why this is separate:
- Setup logic is distinct from other features
- Easy to modify setup flow
- Can add setup wizards later
- Testable without full bot context
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from bot.services.config_manager import ConfigManager
from bot.ui import keyboards, messages


class SetupHandler:
    """Handles user setup and onboarding."""
    
    def __init__(self, config_manager: ConfigManager, bot):
        """
        Initialize setup handler.
        
        Args:
            config_manager: ConfigManager instance
            bot: Telegram Bot instance (for channel validation)
        """
        self.config_mgr = config_manager
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        
        # Job poster will be set by main bot
        self.job_poster = None
    
    def set_job_poster(self, job_poster):
        """
        Set job poster service (called by main bot).
        
        Args:
            job_poster: JobPoster instance
        """
        self.job_poster = job_poster
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /start command.
        
        Flow:
        1. Check if user is configured
        2. If not → show setup instructions
        3. If yes → activate bot and show main menu
        """
        user_id = update.effective_user.id
        username = update.effective_user.username or "User"
        
        self.logger.info(f"/start from user {user_id} ({username})")
        
        # Check if user has completed setup
        if not self.config_mgr.is_user_configured(user_id):
            # New user - show setup instructions
            await update.message.reply_text(
                messages.WELCOME_MESSAGE,
                parse_mode='Markdown'
            )
            await update.message.reply_text(
                messages.SETUP_PROMPT,
                parse_mode='Markdown'
            )
            await update.message.reply_text(
                messages.SETUP_TEMPLATE,
                parse_mode='Markdown'
            )
            return
        
        # Existing configured user - show welcome back message
        config = self.config_mgr.load_user_config(user_id)
        interval_hours = config['scraping'].get('interval_hours', 1)
        channel_id = config['channel_id']
        
        welcome_back = (
            f"✅ *Welcome back!*\n\n"
            f"Your bot is ready to run:\n"
            f"📬 Channel: `{channel_id}`\n"
            f"⏰ Check interval: {interval_hours} hours\n\n"
            f"Use the menu below to manage your bot:"
        )
        
        # Mark user as active/started
        if self.job_poster:
            self.job_poster.start_user(user_id)
        
        searches_count = len(config.get('searches', []))
        await update.message.reply_text(
            welcome_back,
            reply_markup=keyboards.main_menu_keyboard(has_searches=(searches_count > 0)),
            parse_mode='Markdown'
        )
    
    async def handle_setup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /setup command - Show setup instructions anytime.
        
        Useful for:
        - Users who want to reconfigure
        - Users who forgot the format
        """
        user_id = update.effective_user.id
        self.logger.info(f"/setup from user {user_id}")
        
        await update.message.reply_text(
            messages.SETUP_PROMPT,
            parse_mode='Markdown'
        )
        await update.message.reply_text(
            messages.SETUP_TEMPLATE,
            parse_mode='Markdown'
        )
    
    async def handle_config_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Parse and validate user's configuration template.
        
        Expected format:
            channel_id: @MyChannel
            interval_hours: 1
            job_bank_only: true
        
        Steps:
        1. Parse YAML-like format
        2. Validate required fields
        3. Test channel access
        4. Save configuration
        5. Show success message
        """
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        self.logger.info(f"Processing config from user {user_id}")
        
        try:
            # Parse config lines
            config_data = self._parse_config_text(text)
            
            # Validate required fields
            is_valid, error_msg = self._validate_config(config_data)
            if not is_valid:
                await update.message.reply_text(
                    f"❌ {error_msg}\n\n" + messages.SETUP_TEMPLATE,
                    parse_mode='Markdown'
                )
                return
            
            # Test channel access
            channel_id = config_data['channel_id']
            try:
                chat = await self.bot.get_chat(channel_id)
                self.logger.info(f"Successfully validated channel {channel_id} for user {user_id}")
            except TelegramError as e:
                error_text = (
                    f"❌ Cannot access channel: `{channel_id}`\n\n"
                    "Make sure:\n"
                    "1. Channel ID/username is correct\n"
                    "2. I'm added as an admin to the channel\n"
                    "3. I have permission to post messages\n\n"
                    f"Error: {str(e)}"
                )
                await update.message.reply_text(error_text, parse_mode='Markdown')
                return
            
            # Create full config structure
            full_config = self._build_full_config(user_id, config_data)
            
            # Save configuration
            self.config_mgr.save_user_config(user_id, full_config)
            
            # Mark user as active/started
            if self.job_poster:
                self.job_poster.start_user(user_id)
            
            # Show success message with main menu
            success_msg = messages.CONFIG_SAVED.format(
                channel_id=channel_id,
                interval_hours=config_data.get('interval_hours', 1),
                job_bank_only=config_data.get('job_bank_only', True)
            )
            
            await update.message.reply_text(
                success_msg,
                reply_markup=keyboards.main_menu_keyboard(has_searches=False),
                parse_mode='Markdown'
            )
            
            self.logger.info(f"Configuration saved successfully for user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error parsing config for user {user_id}: {e}")
            await update.message.reply_text(
                messages.ERROR_INVALID_CONFIG + "\n\n" + messages.SETUP_TEMPLATE,
                parse_mode='Markdown'
            )
    
    def _parse_config_text(self, text: str) -> dict:
        """
        Parse YAML-like config text into dictionary.
        
        Args:
            text: Config text from user
            
        Returns:
            Dictionary with parsed config values
        """
        lines = text.split('\n')
        config_data = {}
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                # Support both user-friendly and internal field names
                if key in ('channel_id', 'channel'):
                    config_data['channel_id'] = value
                elif key in ('interval_hours', 'interval'):
                    try:
                        config_data['interval_hours'] = float(value)
                    except ValueError:
                        config_data['interval_hours'] = 1
                elif key in ('job_bank_only', 'job bank only'):
                    config_data['job_bank_only'] = value.lower() in ('true', 'yes', '1')
        
        return config_data
    
    def _validate_config(self, config_data: dict) -> tuple[bool, str]:
        """
        Validate parsed configuration.
        
        Args:
            config_data: Parsed config dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required field
        if 'channel_id' not in config_data:
            return False, "Missing required field: `channel_id`"
        
        # Set defaults
        if 'interval_hours' not in config_data:
            config_data['interval_hours'] = 1
        
        if 'job_bank_only' not in config_data:
            config_data['job_bank_only'] = True
        
        # Validate interval
        interval = config_data.get('interval_hours', 1)
        if interval < 0.5:
            return False, "⚠️ Interval too short. Minimum is 0.5 hours (30 minutes)"
        
        if interval > 24:
            return False, "⚠️ Interval too long. Maximum is 24 hours"
        
        return True, ""
    
    def _build_full_config(self, user_id: int, config_data: dict) -> dict:
        """
        Build complete configuration structure.
        
        Args:
            user_id: Telegram user ID
            config_data: Parsed basic config
            
        Returns:
            Complete config dictionary
        """
        return {
            'user_id': user_id,
            'channel_id': config_data['channel_id'],
            'scraping': {
                'interval_hours': config_data.get('interval_hours', 1),
                'headless': True,
                'job_bank_only': config_data.get('job_bank_only', True)
            },
            'searches': [],
            'filters': {
                'keywords_blacklist': []
            },
            'posting': {
                'add_hashtags': True,
                'show_search_separator': True
            },
            'user_limit_request': self.config_mgr.default_user_limit_request,
            'user_post_delay': 3,
            'stats': {
                'posted_today': 0,
                'total_posted': 0
            }
        }


# Example usage
if __name__ == "__main__":
    """
    This shows how the setup handler would be used in the main bot.
    """
    logging.basicConfig(level=logging.INFO)
    
    # In real bot, these would be initialized properly
    from bot.services.config_manager import ConfigManager
    
    config_mgr = ConfigManager()
    # bot would be the actual Telegram Bot instance
    
    print("Setup Handler initialized")
    print("Handles: /start, /setup commands and config parsing")
