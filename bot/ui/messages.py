"""
Message templates for Telegram bot.

This module contains all message text used by the bot.
Centralizing messages makes it easy to:
- Update wording without touching code logic
- Maintain consistent tone
- Add multi-language support later
- A/B test different messages

Think of this as the bot's "script" - all the things it says to users.
"""

from typing import List, Dict, Any


# ===========================================
# Welcome & Setup Messages
# ===========================================

WELCOME_MESSAGE = """
👋 Welcome to JobBank Scraper Bot!

I'll help you automatically find and post job listings from Job Bank to your Telegram channel.

Let's get you set up! Use /setup to configure your preferences.
"""

SETUP_PROMPT = """
⚙️ Let's configure your bot!

Please send me a configuration in this format:
"""

SETUP_TEMPLATE = """
```
Channel: @your_channel_name
Interval: 12
Job Bank Only: true
```
"""

SETUP_INSTRUCTIONS = """
**Instructions:**
- **Channel**: Your Telegram channel username (must start with @)
- **Interval**: Hours between automatic checks (1-24)
- **Job Bank Only**: 'true' or 'false' - whether to include Indeed/other sources

Copy the template above, fill in your details, and send it back to me!
You can add searches and blacklist keywords later from the menu.
"""

CONFIG_SAVED = """
✅ *Configuration Saved!*

Channel: `{channel_id}`
Interval: {interval_hours} hours
Job Bank only: {job_bank_only}

🎉 *Your bot is ready!*

*Next steps:*
1️⃣ Add job searches (use "🔍 Manage Searches" button)
2️⃣ Configure blacklist keywords (optional)
3️⃣ Click "🔄 Check for Jobs Now" when ready

Use the menu below to get started:
"""


# ===========================================
# Menu Messages
# ===========================================

MAIN_MENU = """
📋 **Main Menu**

What would you like to do?
"""

SEARCHES_MENU = """
🔍 **Manage Job Searches**

{search_list}

Active searches: {count}
"""

NO_SEARCHES = "_No searches configured yet._"

BLACKLIST_MENU = """
🚫 **Manage Blacklist**

{blacklist_list}

Blacklisted words: {count}
"""

NO_BLACKLIST = "_No blacklist keywords configured._"

DB_SEARCH_MENU = """
💾 **Search Job Database**

Search through all jobs stored in your database.
You can filter by keyword, location, or salary.
"""

SETTINGS_MENU = """
⚙️ **Settings**

Current configuration:
• Channel: {channel}
• Check interval: Every {interval} hours
• Job Bank only: {job_bank_only}
• Active searches: {search_count}
• Blacklist keywords: {blacklist_count}
"""


# ===========================================
# Templates for Adding Items
# ===========================================

ADD_SEARCH_TEMPLATE = """
➕ **Add New Search**

Send me your search in this format:

```
search:
keyword: Software Engineer
location: Toronto, ON
pages: 5
```

Example:
```
search:
keyword: Python Developer
location: Vancouver
pages: 3
```

Copy the template, fill it in, and send it back!
"""

ADD_BLACKLIST_TEMPLATE = """
➕ **Add Blacklist Keyword**

Send me keywords to blacklist, one per line:

```
blacklist:
senior
manager
director
```

Jobs containing these keywords in the title will be skipped.
"""

DB_SEARCH_TEMPLATE = """
💾 **Search Database**

Send me your search criteria:

```
dbsearch:
keyword: machine learning
location: Toronto
min_salary: 80000
```

All fields are optional. Leave blank to see all jobs.
"""


# ===========================================
# Success/Error Messages
# ===========================================

SEARCH_ADDED = """
✅ Search added successfully!

**{keyword}** in **{location}** ({pages} pages)

The bot will include this in the next check.
"""

SEARCH_REMOVED = """
✅ Search removed successfully!

The bot will no longer search for this.
"""

BLACKLIST_ADDED = """
✅ Blacklist keywords added!

Added {count} keyword(s): {keywords}

Jobs with these words will be skipped.
"""

BLACKLIST_REMOVED = """
✅ Blacklist keyword removed!

**{keyword}** is no longer blacklisted.
"""

CONFIG_UPDATED = """
✅ Configuration updated!

Your new settings are active.
"""


# ===========================================
# Job Checking Messages
# ===========================================

CHECKING_JOBS = """
🔍 Checking for new jobs...

This may take a minute depending on how many searches you have configured.
"""

CHECKING_COMPLETE = """
✅ Check complete!

Found {new_jobs} new jobs.
{posted_jobs} jobs posted to your channel.
"""

NO_NEW_JOBS = """
ℹ️ No new jobs found.

The bot will check again in {interval} hours.
"""

SCRAPING_IN_PROGRESS = """
🔄 Scraping jobs: **{keyword}** in **{location}**

Found {found} jobs so far...
"""


# ===========================================
# Statistics Messages
# ===========================================

def format_stats_message(stats: Dict[str, Any]) -> str:
    """
    Format statistics data into a readable message.
    
    Args:
        stats: Statistics dictionary from API
        
    Returns:
        Formatted statistics message
    """
    total = stats.get('total_jobs', 0)
    posted = stats.get('posted_jobs', 0)
    unposted = stats.get('unposted_jobs', 0)
    sources = stats.get('sources', {})
    
    message = f"""
📊 **Database Statistics**

**Total Jobs:** {total}
**Posted to Channel:** {posted}
**Not Yet Posted:** {unposted}

**By Source:**
"""
    
    for source, count in sources.items():
        message += f"• {source}: {count}\n"
    
    if not sources:
        message += "_No jobs in database yet._\n"
    
    return message


def format_db_search_results(results: Dict[str, Any]) -> str:
    """
    Format database search results into a message.
    
    Args:
        results: Search results from API
        
    Returns:
        Formatted results message
    """
    total = results.get('total', 0)
    jobs = results.get('jobs', [])
    
    if total == 0:
        return "❌ No jobs found matching your criteria."
    
    message = f"💾 **Found {total} jobs**\n\n"
    
    for job in jobs[:10]:  # Show first 10
        title = job.get('title', 'Unknown')
        company = job.get('company', 'Unknown')
        location = job.get('location', 'Unknown')
        message += f"• **{title}** at {company}\n  📍 {location}\n\n"
    
    if total > 10:
        message += f"\n_Showing 10 of {total} results._"
    
    return message


# ===========================================
# Error Messages
# ===========================================

ERROR_GENERAL = """
❌ An error occurred. Please try again.

If the problem persists, contact support.
"""

ERROR_INVALID_FORMAT = """
❌ Invalid format!

Please use the template provided and try again.
"""

ERROR_INVALID_CONFIG = """
❌ Could not parse configuration.

Please use the exact format provided in the template.
"""

ERROR_NO_CONFIG = """
❌ You haven't set up your bot yet!

Use /setup to configure your preferences first.
"""

ERROR_API_UNAVAILABLE = """
❌ The API server is currently unavailable.

Please try again in a few minutes.
"""

ERROR_SCRAPING_FAILED = """
❌ Failed to scrape jobs.

This might be due to:
• Network issues
• Job Bank website changes
• Invalid search parameters

Please try again or adjust your search.
"""


# ===========================================
# Help Messages
# ===========================================

HELP_MESSAGE = """
🤖 **JobBank Scraper Bot - Help**

**Commands:**
/start - Start the bot
/setup - Configure bot settings
/menu - Show main menu
/help - Show this help message

**Features:**
• Automatic job scraping from Job Bank
• Post jobs to your Telegram channel
• Blacklist unwanted keywords
• Search your job database
• View statistics

**Need Help?**
Make sure you've configured the bot using /setup first!
"""


# ===========================================
# Update Config Template
# ===========================================

UPDATE_CONFIG_TEMPLATE = """
⚙️ **Update Configuration**

Current settings:
```
Channel: {channel}
Interval: {interval}
Job Bank Only: {job_bank_only}
```

Send me updated settings in this format:
```
Channel: @your_channel
Interval: 12
Job Bank Only: true
```

You can update all fields or just some of them.
"""
