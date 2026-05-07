"""
Settings Handler for Job Bank Telegram Bot

Handles:
- Settings/configuration menu display
- Statistics display
- Configuration updates
- Config template parsing

Why this is separate:
- Settings are a complete feature area
- Statistics need special formatting
- Config updates need validation
- Easy to add new settings
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from bot.services.config_manager import ConfigManager
from bot.services.api_client import JobBankAPI
from bot.ui import keyboards, messages


class SettingsHandler:
    """Handles bot settings and statistics."""
    
    def __init__(self, config_manager: ConfigManager, api_client: JobBankAPI, bot):
        """
        Initialize settings handler.
        
        Args:
            config_manager: ConfigManager instance
            api_client: JobBankAPI instance
            bot: Telegram Bot instance (for channel validation)
        """
        self.config_mgr = config_manager
        self.api = api_client
        self.bot = bot
        self.logger = logging.getLogger(__name__)
    
    async def show_settings_menu(self, query, user_id: int):
        """
        Show settings/configuration menu.
        
        Displays:
        - Current configuration
        - Statistics
        - Options to update config
        
        Args:
            query: CallbackQuery from button press
            user_id: Telegram user ID
        """
        self.logger.info(f"Showing settings menu for user {user_id}")
        
        config = self.config_mgr.load_user_config(user_id)
        
        # Build settings message
        channel_id = config.get('channel_id', 'Not set')
        interval_hours = config['scraping'].get('interval_hours', 1)
        job_bank_only = config['scraping'].get('job_bank_only', True)
        recent_jobs_only = config['scraping'].get('recent_jobs_only', True)
        add_hashtags = config['posting'].get('add_hashtags', True)
        
        message = messages.SETTINGS_MENU.format(
            channel=channel_id,
            interval=interval_hours,
            job_bank_only=job_bank_only,
            recent_jobs_only=recent_jobs_only,
            search_count=len(config.get('searches', [])),
            blacklist_count=len(config.get('filters', {}).get('keywords_blacklist', []))
        )
        
        message += (
            f"\n*Posting Settings:*\n"
            f"• Max posts per run: {max_posts}\n"
            f"• Add hashtags: {add_hashtags}\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Update Config", callback_data="menu_update_config")],
            [InlineKeyboardButton("« Back to Menu", callback_data="back_to_menu")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def show_stats(self, query, user_id: int):
        """
        Show user and global statistics.
        
        Args:
            query: CallbackQuery from button press
            user_id: Telegram user ID
        """
        self.logger.info(f"Showing statistics for user {user_id}")
        
        # Get user config
        config = self.config_mgr.load_user_config(user_id)
        user_stats = config.get('stats', {})
        
        # Get stats from API
        try:
            api_stats = self.api.get_stats(user_id)
            
            message = (
                "📊 *Statistics*\n\n"
                "*Your Bot:*\n"
                f"• Posted today: {user_stats.get('posted_today', 0)}\n"
                f"• Total posted: {user_stats.get('total_posted', 0)}\n"
                f"• Active searches: {len(config.get('searches', []))}\n\n"
                "*Database:*\n"
                f"• Total jobs: {api_stats.get('total_jobs', 0)}\n"
                f"• Unposted jobs: {api_stats.get('unposted_jobs', 0)}\n"
                f"• Posted to Telegram: {api_stats.get('posted_jobs', 0)}"
            )
            
            # Add sources breakdown if available
            if 'sources' in api_stats:
                message += "\n\n*By Source:*\n"
                for source, count in api_stats['sources'].items():
                    message += f"• {source}: {count}\n"
            
        except Exception as e:
            self.logger.error(f"Error fetching stats: {e}")
            message = (
                "📊 *Statistics*\n\n"
                "*Your Bot:*\n"
                f"• Posted today: {user_stats.get('posted_today', 0)}\n"
                f"• Total posted: {user_stats.get('total_posted', 0)}\n"
                f"• Active searches: {len(config.get('searches', []))}\n\n"
                "⚠️ Could not fetch database statistics."
            )
        
        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="back_to_menu")]]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def show_update_config_template(self, query, user_id: int):
        """
        Show template for updating configuration.
        
        Args:
            query: CallbackQuery from button press
            user_id: Telegram user ID
        """
        self.logger.info(f"Showing config update template for user {user_id}")
        
        config = self.config_mgr.load_user_config(user_id)
        
        template = messages.UPDATE_CONFIG_TEMPLATE.format(
            channel=config.get('channel_id', '@YourChannel'),
            interval=config['scraping'].get('interval_hours', 1),
            job_bank_only=str(config['scraping'].get('job_bank_only', True)).lower(),
            recent_jobs_only=str(config['scraping'].get('recent_jobs_only', True)).lower()
        )
        
        keyboard = [[InlineKeyboardButton("« Back to Settings", callback_data="menu_config")]]
        
        await query.edit_message_text(
            template,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def handle_update_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Parse and apply configuration updates.
        
        Expected format:
            channel_id: @MyChannel
            interval_hours: 2
            job_bank_only: true
            recent_jobs_only: true
        
        Args:
            update: Update with message
            context: Callback context
        """
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        self.logger.info(f"Processing config update from user {user_id}")
        
        try:
            # Parse config text
            config_data = self._parse_config_text(text)
            
            if not config_data:
                await update.message.reply_text(
                    "❌ No configuration changes found.\n\n" +
                    "Please use the template format.",
                    parse_mode='Markdown'
                )
                return
            
            # Validate changes
            is_valid, error_msg = self._validate_config_updates(config_data)
            if not is_valid:
                await update.message.reply_text(
                    f"❌ {error_msg}\n\n" +
                    "Please correct and try again.",
                    parse_mode='Markdown'
                )
                return
            
            # Test channel access if channel_id changed
            if 'channel_id' in config_data:
                try:
                    await self.bot.get_chat(config_data['channel_id'])
                except TelegramError as e:
                    await update.message.reply_text(
                        f"❌ Cannot access channel: `{config_data['channel_id']}`\n\n"
                        "Make sure:\n"
                        "1. Channel ID/username is correct\n"
                        "2. I'm added as an admin\n"
                        "3. I have permission to post\n\n"
                        f"Error: {str(e)}",
                        parse_mode='Markdown'
                    )
                    return
            
            # Apply updates
            self._apply_config_updates(user_id, config_data)
            
            # Success message
            changes = []
            if 'channel_id' in config_data:
                changes.append(f"• Channel: `{config_data['channel_id']}`")
            if 'interval_hours' in config_data:
                changes.append(f"• Interval: {config_data['interval_hours']} hours")
            if 'job_bank_only' in config_data:
                changes.append(f"• Job Bank only: {config_data['job_bank_only']}")
            if 'recent_jobs_only' in config_data:
                changes.append(f"• Last 30 days only: {config_data['recent_jobs_only']}")
            
            changes_str = "\n".join(changes)
            
            await update.message.reply_text(
                f"✅ *Configuration Updated!*\n\n"
                f"*Changes:*\n{changes_str}\n\n"
                "Your new settings are now active.",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            self.logger.error(f"Error updating config for user {user_id}: {e}")
            await update.message.reply_text(
                messages.ERROR_GENERAL + "\n\n" +
                "Please check your configuration format and try again.",
                parse_mode='Markdown'
            )
    
    def _parse_config_text(self, text: str) -> dict:
        """Parse configuration update text."""
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
                
                if key == 'channel_id' or key == 'channel':
                    config_data['channel_id'] = value
                elif key == 'interval_hours' or key == 'interval':
                    try:
                        config_data['interval_hours'] = float(value)
                    except ValueError:
                        pass
                elif key == 'job_bank_only':
                    config_data['job_bank_only'] = value.lower() in ('true', 'yes', '1')
                elif key == 'recent_jobs_only':
                    config_data['recent_jobs_only'] = value.lower() in ('true', 'yes', '1')
        
        return config_data
    
    def _validate_config_updates(self, config_data: dict) -> tuple[bool, str]:
        """Validate configuration updates."""
        if 'interval_hours' in config_data:
            interval = config_data['interval_hours']
            if interval < 0.5:
                return False, "Interval too short. Minimum is 0.5 hours (30 minutes)"
            if interval > 24:
                return False, "Interval too long. Maximum is 24 hours"
        
        return True, ""
    
    def _apply_config_updates(self, user_id: int, config_data: dict):
        """Apply configuration updates to user config."""
        if 'channel_id' in config_data:
            self.config_mgr.update_config_field(user_id, 'channel_id', config_data['channel_id'])
        
        if 'interval_hours' in config_data:
            self.config_mgr.update_config_field(
                user_id, 'scraping.interval_hours', config_data['interval_hours']
            )
        
        if 'job_bank_only' in config_data:
            self.config_mgr.update_config_field(
                user_id, 'scraping.job_bank_only', config_data['job_bank_only']
            )
        if 'recent_jobs_only' in config_data:
            self.config_mgr.update_config_field(
                user_id, 'scraping.recent_jobs_only', config_data['recent_jobs_only']
            )
        
        self.logger.info(f"Config updated for user {user_id}: {config_data}")


# Example usage
if __name__ == "__main__":
    """
    This shows how the settings handler would be used.
    """
    logging.basicConfig(level=logging.INFO)
    
    from bot.services.config_manager import ConfigManager
    from bot.services.api_client import JobBankAPI
    
    config_mgr = ConfigManager()
    api = JobBankAPI(base_url="http://localhost:8000")
    
    print("Settings Handler initialized")
    print("Handles: settings menu, statistics, config updates")
