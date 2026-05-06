"""
 Keyboard layouts for Telegram bot.

This module contains all InlineKeyboardMarkup layouts used in the bot.
Centralizing UI makes it easy to maintain and update button layouts.

Why separate UI code?
- Single place to update button text
- Consistent styling across the bot
- Easier to add new buttons or modify layouts
- UI changes don't require touching business logic
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Any


def main_menu_keyboard(has_searches: bool = False) -> InlineKeyboardMarkup:
    """
    Main menu keyboard layout.
    
    Args:
        has_searches: Whether user has configured searches
        
    Returns:
        InlineKeyboardMarkup for main menu
    """
    keyboard = []
    
    # Always show "Check Now" at the top if user has searches configured
    if has_searches:
        keyboard.append([InlineKeyboardButton("🔄 Check for Jobs Now", callback_data="action_check")])
    
    # Main menu in double columns
    keyboard.extend([
        [
            InlineKeyboardButton("🔍 Manage Searches", callback_data="menu_searches"),
            InlineKeyboardButton("🚫 Manage Blacklist", callback_data="menu_blacklist")
        ],
        [
            InlineKeyboardButton("💾 Search Database", callback_data="menu_db_search"),
            InlineKeyboardButton("📊 Statistics", callback_data="menu_stats")
        ],
        [InlineKeyboardButton("⚙️ Settings", callback_data="menu_config")],
    ])
    
    return InlineKeyboardMarkup(keyboard)


def searches_menu_keyboard(searches: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """
    Searches management menu.
    
    Args:
        searches: List of user's search configurations
        
    Returns:
        InlineKeyboardMarkup with search list and controls
    """
    keyboard = []
    
    # List existing searches with remove buttons
    for idx, search in enumerate(searches):
        keyword = search.get('keyword', 'N/A')
        location = search.get('location', 'N/A')
        pages = search.get('pages', 1)
        
        button_text = f"🗑️ {keyword} in {location} ({pages}p)"
        keyboard.append([
            InlineKeyboardButton(button_text, callback_data=f"search_remove_{idx}")
        ])
    
    # Add new search button and back button in double column
    keyboard.append([
        InlineKeyboardButton("➕ Add New Search", callback_data="add_new_search"),
        InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def blacklist_menu_keyboard(blacklist: List[str]) -> InlineKeyboardMarkup:
    """
    Blacklist management menu.
    
    Args:
        blacklist: List of blacklisted keywords
        
    Returns:
        InlineKeyboardMarkup with blacklist and controls
    """
    keyboard = []
    
    # List blacklisted keywords with remove buttons
    for keyword in blacklist:
        keyboard.append([
            InlineKeyboardButton(
                f"🗑️ {keyword}",
                callback_data=f"blacklist_remove_{keyword}"
            )
        ])
    
    # Add new blacklist button and back button in double column
    keyboard.append([
        InlineKeyboardButton("➕ Add Blacklist", callback_data="add_blacklist"),
        InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def db_search_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Database search menu.
    
    Returns:
        InlineKeyboardMarkup for database search
    """
    keyboard = [
        [
            InlineKeyboardButton("🔍 Search Jobs", callback_data="start_db_search"),
            InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def settings_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Settings menu.
    
    Returns:
        InlineKeyboardMarkup for settings
    """
    keyboard = [
        [
            InlineKeyboardButton("📊 Statistics", callback_data="menu_stats"),
            InlineKeyboardButton("⚙️ Configuration", callback_data="menu_update_config")
        ],
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Simple back button.
    
    Returns:
        InlineKeyboardMarkup with just back button
    """
    keyboard = [[InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")]]
    return InlineKeyboardMarkup(keyboard)


def back_to_settings_keyboard() -> InlineKeyboardMarkup:
    """
    Back to settings button.
    
    Returns:
        InlineKeyboardMarkup with back to settings button
    """
    keyboard = [[InlineKeyboardButton("◀️ Back to Settings", callback_data="menu_config")]]
    return InlineKeyboardMarkup(keyboard)


def cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Cancel button for operations.
    
    Returns:
        InlineKeyboardMarkup with cancel button
    """
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="back_to_menu")]]
    return InlineKeyboardMarkup(keyboard)
