"""PII (Personally Identifiable Information) detection and redaction."""
import re
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


class PIIReductor:
    """Redacts PII from text before sending to external AI services."""
    
    # Regex patterns for PII detection
    PATTERNS = {
        # Malaysian IC Numbers (12 digits)
        'my_ic': (r'\b\d{6}-?\d{2}-?\d{4}\b', '[MY_IC]'),
        
        # Phone numbers (various formats)
        'phone': (
            r'\b(?:\+?6?01[0-46-9]-?\d{7,8}|\+?60[0-46-9]-?\d{7,8}|\+?6?01[0-46-9]\d{7,8})\b',
            '[PHONE]'
        ),
        
        # Email addresses
        'email': (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
        
        # Malaysian addresses (common patterns)
        'address': (
            r'\b(?:No\.?\s*\d+\s*,?\s*)?(?:Jalan|Lorong|Persiaran|Lebuh|Jln|Lrg)\s+[A-Za-z0-9\s]+(?:\d{5})?',
            '[ADDRESS]'
        ),
        
        # Postal codes (5 digits for Malaysia)
        'postal_code': (r'\b\d{5}\b', '[POSTCODE]'),
        
        # Names (Capitalized words that look like names)
        # This is a simple heuristic - names are 2-3 capitalized words
        'name': (
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b',
            '[NAME]'
        ),
        
        # School names (common patterns)
        'school_name': (
            r'\b(?:SK|SMK|SJK|SM|Sekolah)\s+[A-Za-z0-9\s]+\b',
            '[SCHOOL]'
        ),
        
        # URLs
        'url': (
            r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?',
            '[URL]'
        ),
    }
    
    # Context words that indicate PII
    PII_CONTEXT_WORDS = [
        'name', 'nama', 'student', 'pelajar', 'murid',
        'address', 'alamat', 'phone', 'telefon', 'contact',
        'email', 'ic', 'identity card', 'kad pengenalan',
        'parent', 'ibu', 'bapa', 'mother', 'father',
        'guardian', 'penjaga'
    ]
    
    def __init__(self):
        self.compiled_patterns = {}
        for key, (pattern, replacement) in self.PATTERNS.items():
            try:
                self.compiled_patterns[key] = (re.compile(pattern, re.IGNORECASE), replacement)
            except re.error as e:
                logger.error(f"Failed to compile pattern {key}: {e}")
    
    def redact(self, text: str, aggressive: bool = False) -> Tuple[str, Dict]:
        """
        Redact PII from text.
        
        Args:
            text: Input text that may contain PII
            aggressive: If True, also redact potential names
            
        Returns:
            Tuple of (redacted_text, redaction_report)
        """
        if not text:
            return text, {}
        
        original_text = text
        redacted_count = {}
        
        # Always redact high-confidence PII
        high_confidence = ['my_ic', 'phone', 'email', 'address', 'postal_code', 'url']
        
        for key in high_confidence:
            if key in self.compiled_patterns:
                pattern, replacement = self.compiled_patterns[key]
                matches = pattern.findall(text)
                if matches:
                    redacted_count[key] = len(matches)
                    text = pattern.sub(replacement, text)
        
        # Aggressive mode: also redact names and schools
        if aggressive:
            for key in ['name', 'school_name']:
                if key in self.compiled_patterns:
                    pattern, replacement = self.compiled_patterns[key]
                    matches = pattern.findall(text)
                    if matches:
                        redacted_count[key] = len(matches)
                        text = pattern.sub(replacement, text)
        
        # Log redaction summary
        if redacted_count:
            logger.info(f"PII redaction: {redacted_count}")
        
        return text, {
            'redacted_count': redacted_count,
            'original_length': len(original_text),
            'redacted_length': len(text),
            'aggressive_mode': aggressive
        }
    
    def contains_pii(self, text: str) -> Tuple[bool, List[str]]:
        """
        Check if text contains potential PII.
        
        Returns:
            Tuple of (has_pii, list_of_pii_types)
        """
        pii_types = []
        
        for key, (pattern, _) in self.compiled_patterns.items():
            if pattern.search(text):
                pii_types.append(key)
        
        return len(pii_types) > 0, pii_types
    
    def redact_homework_text(self, text: str) -> str:
        """
        Specialized redaction for homework text.
        Preserves educational content, removes personal info.
        """
        # Redact with aggressive mode for homework (contains student names)
        redacted, _ = self.redact(text, aggressive=True)
        return redacted


# Singleton instance
_reductor = None

def get_reductor() -> PIIReductor:
    """Get or create PII reductor singleton."""
    global _reductor
    if _reductor is None:
        _reductor = PIIReductor()
    return _reductor


def redact_for_ai(text: str) -> str:
    """Convenience function to redact text before sending to AI."""
    reductor = get_reductor()
    redacted, report = reductor.redact(text, aggressive=True)
    
    if report['redacted_count']:
        logger.info(
            f"Redacted {sum(report['redacted_count'].values())} PII items "
            f"before AI processing: {list(report['redacted_count'].keys())}"
        )
    
    return redacted
