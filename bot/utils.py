"""Utility functions for Telegram Bot."""

import re
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from pathlib import Path

import pytz

logger = logging.getLogger(__name__)


# Date parsing patterns for multiple languages
DATE_PATTERNS = {
    "en": [
        r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})",  # DD/MM/YYYY or MM/DD/YYYY
        r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{2,4})",
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2})[,\s]+(\d{2,4})",
    ],
    "zh": [
        r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})[日]?",
        r"(\d{1,2})[月/-](\d{1,2})[日]?",
    ],
}

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_date(text: str, timezone: str = "Asia/Singapore") -> Optional[datetime]:
    """Extract date from text."""
    text_lower = text.lower()
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    
    # Check for relative dates
    if "tomorrow" in text_lower or "明天" in text:
        return now + timedelta(days=1)
    if "today" in text_lower or "今天" in text:
        return now
    if "next week" in text_lower or "下星期" in text:
        return now + timedelta(weeks=1)
    
    # Try pattern matching
    for lang, patterns in DATE_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        if lang == "en":
                            # Try DD/MM/YYYY first
                            day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                            if month > 12:  # Must be MM/DD/YYYY
                                day, month = month, day
                        else:  # zh
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                            if year < 100:
                                year += 2000
                        
                        # Default to current year if not specified
                        if year < 100:
                            year += 2000
                        
                        dt = datetime(year, month, day, 23, 59, tzinfo=tz)
                        return dt
                except (ValueError, IndexError):
                    continue
    
    return None


def format_date(dt: datetime, language: str = "en") -> str:
    """Format date for display."""
    if language == "zh":
        return dt.strftime("%Y年%m月%d日")
    elif language == "ms":
        return dt.strftime("%d %B %Y")
    else:
        return dt.strftime("%d %B %Y")


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    # Remove path components
    filename = os.path.basename(filename)
    # Replace unsafe characters
    filename = re.sub(r'[^\w\-.]', '_', filename)
    # Limit length
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:96] + ext
    return filename


def validate_file_size(file_path: str, max_size_mb: int = 20) -> bool:
    """Validate file size."""
    try:
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)
        return size_mb <= max_size_mb
    except OSError:
        return False


def validate_file_extension(filename: str, allowed_extensions: Tuple[str, ...]) -> bool:
    """Validate file extension."""
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext in allowed_extensions


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to max length."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def estimate_reading_time(text: str, words_per_minute: int = 200) -> int:
    """Estimate reading time in minutes."""
    word_count = len(text.split())
    return max(1, word_count // words_per_minute)


def format_duration(seconds: int) -> str:
    """Format duration in human readable form."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def get_priority_emoji(priority: int) -> str:
    """Get emoji for priority level."""
    emojis = {1: "⚪", 2: "🔵", 3: "🟡", 4: "🟠", 5: "🔴"}
    return emojis.get(priority, "⚪")


def get_status_emoji(status: str) -> str:
    """Get emoji for status."""
    emojis = {
        "pending": "⏳",
        "in_progress": "🔄",
        "completed": "✅",
        "overdue": "⚠️",
    }
    return emojis.get(status, "❓")


def mask_sensitive_data(text: str, visible_chars: int = 4) -> str:
    """Mask sensitive data like phone numbers."""
    if len(text) <= visible_chars * 2:
        return "*" * len(text)
    return text[:visible_chars] + "*" * (len(text) - visible_chars * 2) + text[-visible_chars:]


def chunk_list(items: List, chunk_size: int) -> List[List]:
    """Split list into chunks."""
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed."""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        # Clean old requests
        if key in self.requests:
            self.requests[key] = [t for t in self.requests[key] if t > window_start]
        else:
            self.requests[key] = []
        
        # Check limit
        if len(self.requests[key]) >= self.max_requests:
            return False
        
        self.requests[key].append(now)
        return True
