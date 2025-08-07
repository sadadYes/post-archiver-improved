"""
Constants used throughout the post archiver application.
"""

# YouTube API constants
YOUTUBE_BASE_URL = "https://www.youtube.com"
YOUTUBE_API_BASE_URL = "https://www.youtube.com/youtubei/v1"
YOUTUBE_BROWSE_ENDPOINT = f"{YOUTUBE_API_BASE_URL}/browse"
YOUTUBE_NEXT_ENDPOINT = f"{YOUTUBE_API_BASE_URL}/next"

# Request headers
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
YOUTUBE_CLIENT_VERSION = "2.20241113.07.00"

# Community tab parameters
COMMUNITY_TAB_PARAMS = "Egljb21tdW5pdHnyBgQKAkoA"

# Default configuration values
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_MAX_COMMENTS = 100
DEFAULT_MAX_REPLIES = 200

# File naming patterns
POSTS_FILE_PREFIX = "posts"
SUMMARY_FILE_PREFIX = "summary"
IMAGES_DIR_NAME = "images"

# Timestamp estimation indicators
RELATIVE_TIME_INDICATORS = [
    'hour', 'hours', 'minute', 'minutes', 'day', 'days',
    'week', 'weeks', 'month', 'months', 'year', 'years',
    'ago', 'edited'
]
