"""Secure logging configuration with token redaction."""
import logging
import re


class TokenRedactionFilter(logging.Filter):
    """Filter to redact sensitive tokens from logs."""
    
    # Patterns to redact
    SENSITIVE_PATTERNS = [
        (r'\d{9,10}:[A-Za-z0-9_-]{35}', '[TELEGRAM_BOT_TOKEN_REDACTED]'),
        (r'Bearer\s+[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+', 'Bearer [JWT_REDACTED]'),
        (r'api[_-]?key["\']?\s*[:=]\s*["\']?[a-zA-Z0-9]{32,}', 'api_key=[REDACTED]'),
        (r'secret["\']?\s*[:=]\s*["\']?[a-zA-Z0-9]{16,}', 'secret=[REDACTED]'),
    ]
    
    def filter(self, record):
        if isinstance(record.msg, str):
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                record.msg = re.sub(pattern, replacement, record.msg)
        # Also check args if it's a formatted string
        if record.args:
            record.args = tuple(
                self._redact(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True
    
    def _redact(self, message):
        """Redact sensitive patterns from a message string."""
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            message = re.sub(pattern, replacement, message)
        return message


def setup_secure_logging(level=logging.INFO):
    """Configure secure logging with token redaction."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=level,
    )
    
    # Add redaction filter to root logger
    root_logger = logging.getLogger()
    root_logger.addFilter(TokenRedactionFilter())
    
    # Also redact httpx library logs which log URLs
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.addFilter(TokenRedactionFilter())
    
    # Redact telegram library logs as well
    telegram_logger = logging.getLogger("telegram")
    telegram_logger.addFilter(TokenRedactionFilter())
    
    return root_logger
