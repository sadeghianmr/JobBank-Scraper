"""
Configuration Manager for Job Bank Telegram Bot

Why this module exists:
- Centralizes all user configuration management
- Handles YAML reading/writing in one place
- Provides validation for configuration data
- Makes it easy to add new config fields
- Testable without Telegram dependencies

Example:
    from bot.services.config_manager import ConfigManager
    
    config_mgr = ConfigManager()
    config = config_mgr.load_user_config(user_id)
    config['channel_id'] = '@mynewchannel'
    config_mgr.save_user_config(user_id, config)
"""

import yaml
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from src.config import DEFAULT_USER_LIMIT_REQUEST, USER_CONFIGS_DIR
from src.user_config import normalize_user_limit_request


class ConfigManager:
    """Manages user configuration files (YAML)."""
    
    def __init__(self, users_dir: Optional[Path] = None):
        """
        Initialize config manager.
        
        Args:
            users_dir: Directory to store user configs (defaults to user_configs/)
        """
        self.users_dir = users_dir or USER_CONFIGS_DIR
        self.users_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.default_user_limit_request = DEFAULT_USER_LIMIT_REQUEST
    
    def get_user_config_path(self, user_id: int) -> Path:
        """
        Get path to user's config file.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Path to user's YAML config file
        """
        return self.users_dir / f"user_{user_id}.yaml"
    
    def user_exists(self, user_id: int) -> bool:
        """
        Check if user has a config file.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if user config exists
        """
        return self.get_user_config_path(user_id).exists()

    def list_user_ids(self) -> list[int]:
        """Return user IDs that have a config file."""
        user_ids = []

        for path in self.users_dir.glob("user_*.yaml"):
            try:
                user_ids.append(int(path.stem.replace("user_", "")))
            except ValueError:
                self.logger.warning(f"Skipping config with invalid user id: {path.name}")

        return sorted(user_ids)

    def list_configured_user_ids(self) -> list[int]:
        """Return user IDs that completed setup and have a channel configured."""
        configured_users = []

        for user_id in self.list_user_ids():
            config = self.load_user_config(user_id)
            if config.get("channel_id"):
                configured_users.append(user_id)

        return configured_users
    
    def load_user_config(self, user_id: int) -> Dict[str, Any]:
        """
        Load user configuration from YAML file.
        
        If config doesn't exist, returns a default config structure.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            User configuration dictionary
        """
        config_path = self.get_user_config_path(user_id)
        
        if not config_path.exists():
            self.logger.info(f"No config found for user {user_id}, returning default")
            return self._get_default_config(user_id)
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            if not isinstance(config, dict):
                self.logger.warning(f"Invalid config structure for user {user_id}, returning default")
                return self._get_default_config(user_id)

            if self._ensure_config_defaults(config):
                self.save_user_config(user_id, config)

            self.logger.info(f"Config loaded for user {user_id}")
            return config
        except Exception as e:
            self.logger.error(f"Error loading config for user {user_id}: {e}")
            return self._get_default_config(user_id)
    
    def save_user_config(self, user_id: int, config: Dict[str, Any]):
        """
        Save user configuration to YAML file.
        
        Args:
            user_id: Telegram user ID
            config: Configuration dictionary to save
        """
        config_path = self.get_user_config_path(user_id)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False)
            self.logger.info(f"Config saved for user {user_id}")
        except Exception as e:
            self.logger.error(f"Error saving config for user {user_id}: {e}")
            raise
    
    def delete_user_config(self, user_id: int):
        """
        Delete user's configuration file.
        
        Args:
            user_id: Telegram user ID
        """
        config_path = self.get_user_config_path(user_id)
        
        if config_path.exists():
            config_path.unlink()
            self.logger.info(f"Config deleted for user {user_id}")
    
    def is_user_configured(self, user_id: int) -> bool:
        """
        Check if user has completed initial setup.
        
        A user is considered configured if they have a channel_id set.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if user has completed setup
        """
        config = self.load_user_config(user_id)
        return config.get('channel_id') is not None
    
    def update_config_field(self, user_id: int, field_path: str, value: Any):
        """
        Update a specific field in user's config.
        
        Supports nested fields using dot notation.
        
        Examples:
            update_config_field(123, 'channel_id', '@mychannel')
            update_config_field(123, 'scraping.interval_hours', 2)
            update_config_field(123, 'stats.total_posted', 100)
        
        Args:
            user_id: Telegram user ID
            field_path: Dot-separated path to field (e.g., 'scraping.interval_hours')
            value: New value to set
        """
        config = self.load_user_config(user_id)
        
        # Navigate to nested field
        keys = field_path.split('.')
        current = config
        
        # Navigate to parent of target field
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Set the final value
        current[keys[-1]] = value
        
        self.save_user_config(user_id, config)
        self.logger.info(f"Updated {field_path} for user {user_id}")
    
    def add_search(self, user_id: int, search: Dict[str, Any]):
        """
        Add a search to user's searches list.
        
        Args:
            user_id: Telegram user ID
            search: Search dictionary with keyword, location, pages
        """
        config = self.load_user_config(user_id)
        
        if 'searches' not in config:
            config['searches'] = []
        
        # Check if search already exists (by keyword + location)
        search_key = (search['keyword'], search.get('location', 'Anywhere'))
        existing = [
            (s['keyword'], s.get('location', 'Anywhere')) 
            for s in config['searches']
        ]
        
        if search_key not in existing:
            config['searches'].append(search)
            self.save_user_config(user_id, config)
            self.logger.info(f"Added search for user {user_id}: {search['keyword']}")
            return True
        else:
            self.logger.info(f"Search already exists for user {user_id}: {search['keyword']}")
            return False
    
    def remove_search(self, user_id: int, index: int) -> bool:
        """
        Remove a search from user's searches list by index.
        
        Args:
            user_id: Telegram user ID
            index: Index of search to remove (0-based)
            
        Returns:
            True if search was removed, False if index was invalid
        """
        config = self.load_user_config(user_id)
        searches = config.get('searches', [])
        
        if 0 <= index < len(searches):
            removed = searches.pop(index)
            config['searches'] = searches
            self.save_user_config(user_id, config)
            self.logger.info(f"Removed search for user {user_id}: {removed['keyword']}")
            return True
        else:
            self.logger.warning(f"Invalid search index {index} for user {user_id}")
            return False
    
    def add_blacklist_keyword(self, user_id: int, keyword: str):
        """
        Add a keyword to user's blacklist.
        
        Args:
            user_id: Telegram user ID
            keyword: Keyword to blacklist
        """
        config = self.load_user_config(user_id)
        
        if 'filters' not in config:
            config['filters'] = {'keywords_blacklist': []}
        if 'keywords_blacklist' not in config['filters']:
            config['filters']['keywords_blacklist'] = []
        
        keyword_lower = keyword.lower()
        if keyword_lower not in [k.lower() for k in config['filters']['keywords_blacklist']]:
            config['filters']['keywords_blacklist'].append(keyword)
            self.save_user_config(user_id, config)
            self.logger.info(f"Added blacklist keyword for user {user_id}: {keyword}")
            return True
        else:
            self.logger.info(f"Blacklist keyword already exists for user {user_id}: {keyword}")
            return False
    
    def remove_blacklist_keyword(self, user_id: int, index: int) -> bool:
        """
        Remove a blacklist keyword by index.
        
        Args:
            user_id: Telegram user ID
            index: Index of keyword to remove (0-based)
            
        Returns:
            True if keyword was removed, False if index was invalid
        """
        config = self.load_user_config(user_id)
        blacklist = config.get('filters', {}).get('keywords_blacklist', [])
        
        if 0 <= index < len(blacklist):
            removed = blacklist.pop(index)
            config['filters']['keywords_blacklist'] = blacklist
            self.save_user_config(user_id, config)
            self.logger.info(f"Removed blacklist keyword for user {user_id}: {removed}")
            return True
        else:
            self.logger.warning(f"Invalid blacklist index {index} for user {user_id}")
            return False
    
    def increment_stat(self, user_id: int, stat_name: str, amount: int = 1):
        """
        Increment a statistics counter.
        
        Args:
            user_id: Telegram user ID
            stat_name: Name of stat to increment ('posted_today' or 'total_posted')
            amount: Amount to increment by (default: 1)
        """
        config = self.load_user_config(user_id)
        
        if 'stats' not in config:
            config['stats'] = {'posted_today': 0, 'total_posted': 0}
        
        if stat_name in config['stats']:
            config['stats'][stat_name] += amount
            self.save_user_config(user_id, config)
            self.logger.debug(f"Incremented {stat_name} for user {user_id}: +{amount}")
    
    def reset_daily_stats(self, user_id: int):
        """
        Reset daily statistics counters.
        
        Args:
            user_id: Telegram user ID
        """
        self.update_config_field(user_id, 'stats.posted_today', 0)
        self.logger.info(f"Reset daily stats for user {user_id}")

    def get_user_limit_request(self, user_id: int) -> int:
        """Get the user's configured API request limit from YAML config."""
        config = self.load_user_config(user_id)
        return normalize_user_limit_request(config.get('user_limit_request'))

    def get_last_job_search_at(self, user_id: int) -> Optional[datetime]:
        """Return the last scrape time as a timezone-aware datetime."""
        config = self.load_user_config(user_id)
        value = config.get('scraping', {}).get('last_job_search_at')

        if not value:
            return None

        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            self.logger.warning(f"Invalid last_job_search_at for user {user_id}: {value}")
            return None

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)

    def mark_job_search_completed(self, user_id: int, when: Optional[datetime] = None):
        """Save the time when a user's job search/scrape completed."""
        timestamp = when or datetime.now(timezone.utc)
        timestamp = timestamp.astimezone(timezone.utc).replace(microsecond=0)
        self.update_config_field(
            user_id,
            'scraping.last_job_search_at',
            timestamp.isoformat()
        )

    def is_job_search_due(self, user_id: int, now: Optional[datetime] = None) -> bool:
        """Check whether enough time passed since the user's last scrape."""
        config = self.load_user_config(user_id)
        scraping = config.get('scraping', {})

        try:
            interval_hours = float(scraping.get('interval_hours', 1))
        except (TypeError, ValueError):
            interval_hours = 1

        last_search = self.get_last_job_search_at(user_id)
        if last_search is None:
            return True

        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        return current_time.astimezone(timezone.utc) - last_search >= timedelta(hours=interval_hours)

    def _ensure_config_defaults(self, config: Dict[str, Any]) -> bool:
        """Add missing fields to older user configs without changing existing values."""
        changed = False

        def ensure_dict(key: str) -> Dict[str, Any]:
            nonlocal changed
            if not isinstance(config.get(key), dict):
                config[key] = {}
                changed = True
            return config[key]

        scraping = ensure_dict('scraping')
        scraping_defaults = {
            'interval_hours': 1,
            'headless': True,
            'job_bank_only': True,
            'last_job_search_at': None,
        }
        for key, value in scraping_defaults.items():
            if key not in scraping:
                scraping[key] = value
                changed = True

        filters = ensure_dict('filters')
        if 'keywords_blacklist' not in filters:
            filters['keywords_blacklist'] = []
            changed = True

        posting = ensure_dict('posting')
        posting_defaults = {
            'add_hashtags': True,
            'show_search_separator': True,
        }
        for key, value in posting_defaults.items():
            if key not in posting:
                posting[key] = value
                changed = True

        stats = ensure_dict('stats')
        for key in ('posted_today', 'total_posted'):
            if key not in stats:
                stats[key] = 0
                changed = True

        if 'user_limit_request' not in config:
            config['user_limit_request'] = self.default_user_limit_request
            changed = True

        if 'user_post_delay' not in config:
            config['user_post_delay'] = 3
            changed = True

        return changed
    
    def _get_default_config(self, user_id: int) -> Dict[str, Any]:
        """
        Get default configuration for a new user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Default config dictionary
        """
        return {
            'user_id': user_id,
            'channel_id': None,  # Must be set during setup
            'scraping': {
                'interval_hours': 1,
                'headless': True,
                'job_bank_only': True,
                'last_job_search_at': None
            },
            'searches': [],
            'filters': {
                'keywords_blacklist': []
            },
            'posting': {
                'add_hashtags': True,
                'show_search_separator': True
            },
            'user_limit_request': self.default_user_limit_request,
            'user_post_delay': 3,
            'stats': {
                'posted_today': 0,
                'total_posted': 0
            }
        }
    
    def validate_basic_config(self, config_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate basic configuration data.
        
        Args:
            config_data: Configuration data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        if 'channel_id' not in config_data:
            return False, "Missing required field: channel_id"
        
        # Validate interval if present
        if 'interval_hours' in config_data:
            try:
                interval = float(config_data['interval_hours'])
                if interval < 0.5:
                    return False, "Interval too short. Minimum is 0.5 hours (30 minutes)"
            except (ValueError, TypeError):
                return False, "Invalid interval_hours value"
        
        return True, None


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize manager
    mgr = ConfigManager()
    
    # Load config (gets default if doesn't exist)
    config = mgr.load_user_config(12345)
    print(f"User configured: {mgr.is_user_configured(12345)}")
    
    # Update channel
    mgr.update_config_field(12345, 'channel_id', '@testchannel')
    print(f"User configured: {mgr.is_user_configured(12345)}")
    
    # Add search
    mgr.add_search(12345, {
        'keyword': 'Python Developer',
        'location': 'Toronto',
        'pages': 5
    })
    
    # Add blacklist keyword
    mgr.add_blacklist_keyword(12345, 'senior')
    
    # View final config
    final_config = mgr.load_user_config(12345)
    print(f"\nFinal config:\n{yaml.dump(final_config, default_flow_style=False)}")
