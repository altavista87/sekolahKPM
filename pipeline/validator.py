"""Data validation for extracted homework."""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ValidationIssue:
    """Validation issue."""
    field: str
    message: str
    severity: str = "warning"  # error, warning, info


@dataclass
class ValidationResult:
    """Validation result."""
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    confidence_score: float = 0.0
    suggestions: List[str] = field(default_factory=list)


class DataValidator:
    """Validator for homework data."""
    
    # Valid subjects (can be extended)
    VALID_SUBJECTS = {
        "mathematics", "math", "english", "science", "physics", "chemistry",
        "biology", "history", "geography", "chinese", "malay", "tamil",
        "art", "music", "pe", "computer", "programming",
    }
    
    # Date patterns
    DATE_PATTERNS = [
        r"\d{4}-\d{2}-\d{2}",  # YYYY-MM-DD
        r"\d{1,2}/\d{1,2}/\d{2,4}",  # DD/MM/YYYY or MM/DD/YYYY
        r"\d{1,2}-\d{1,2}-\d{2,4}",  # DD-MM-YYYY
    ]
    
    def __init__(self, min_confidence: float = 0.6):
        self.min_confidence = min_confidence
    
    def validate(
        self,
        extraction: Dict[str, Any],
        raw_text: str,
    ) -> ValidationResult:
        """Validate extracted homework data."""
        issues = []
        suggestions = []
        
        # Validate subject
        subject_valid, subject_issues = self._validate_subject(
            extraction.get("subject", "")
        )
        issues.extend(subject_issues)
        
        # Validate title
        title_valid, title_issues = self._validate_title(
            extraction.get("title", "")
        )
        issues.extend(title_issues)
        
        # Validate description
        desc_valid, desc_issues = self._validate_description(
            extraction.get("description", ""),
            raw_text,
        )
        issues.extend(desc_issues)
        
        # Validate due date
        date_valid, date_issues = self._validate_due_date(
            extraction.get("due_date")
        )
        issues.extend(date_issues)
        
        # Validate confidence
        confidence = extraction.get("confidence", 0)
        if confidence < self.min_confidence:
            issues.append(ValidationIssue(
                field="confidence",
                message=f"Low confidence score: {confidence:.2f}",
                severity="warning",
            ))
        
        # Calculate overall validity
        errors = [i for i in issues if i.severity == "error"]
        is_valid = len(errors) == 0
        
        # Generate suggestions
        suggestions = self._generate_suggestions(extraction, issues)
        
        return ValidationResult(
            valid=is_valid,
            issues=issues,
            confidence_score=confidence,
            suggestions=suggestions,
        )
    
    def _validate_subject(self, subject: str) -> tuple:
        """Validate subject field."""
        issues = []
        
        if not subject:
            issues.append(ValidationIssue(
                field="subject",
                message="Subject is missing",
                severity="error",
            ))
            return False, issues
        
        subject_lower = subject.lower()
        if subject_lower not in self.VALID_SUBJECTS:
            issues.append(ValidationIssue(
                field="subject",
                message=f"Unrecognized subject: {subject}",
                severity="warning",
            ))
        
        return True, issues
    
    def _validate_title(self, title: str) -> tuple:
        """Validate title field."""
        issues = []
        
        if not title:
            issues.append(ValidationIssue(
                field="title",
                message="Title is missing",
                severity="error",
            ))
            return False, issues
        
        if len(title) < 3:
            issues.append(ValidationIssue(
                field="title",
                message="Title is too short",
                severity="warning",
            ))
        
        if len(title) > 200:
            issues.append(ValidationIssue(
                field="title",
                message="Title is too long (max 200 chars)",
                severity="warning",
            ))
        
        return True, issues
    
    def _validate_description(
        self,
        description: str,
        raw_text: str,
    ) -> tuple:
        """Validate description field."""
        issues = []
        
        if not description:
            issues.append(ValidationIssue(
                field="description",
                message="Description is missing",
                severity="warning",
            ))
        
        if len(description) < len(raw_text) * 0.5:
            issues.append(ValidationIssue(
                field="description",
                message="Description may be incomplete",
                severity="info",
            ))
        
        return True, issues
    
    def _validate_due_date(self, due_date: Optional[str]) -> tuple:
        """Validate due date field."""
        issues = []
        
        if not due_date:
            return True, issues  # Optional field
        
        try:
            dt = datetime.strptime(due_date, "%Y-%m-%d")
            
            # Check if date is in the past
            if dt.date() < datetime.now().date():
                issues.append(ValidationIssue(
                    field="due_date",
                    message="Due date is in the past",
                    severity="warning",
                ))
            
            # Check if date is too far in future (> 1 year)
            from datetime import timedelta
            if dt > datetime.now() + timedelta(days=365):
                issues.append(ValidationIssue(
                    field="due_date",
                    message="Due date is more than 1 year away",
                    severity="warning",
                ))
            
        except ValueError:
            issues.append(ValidationIssue(
                field="due_date",
                message=f"Invalid date format: {due_date}",
                severity="error",
            ))
        
        return True, issues
    
    def _generate_suggestions(
        self,
        extraction: Dict[str, Any],
        issues: List[ValidationIssue],
    ) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []
        
        # Missing fields
        if not extraction.get("subject"):
            suggestions.append("Please specify the subject")
        
        if not extraction.get("due_date"):
            suggestions.append("Consider adding a due date")
        
        # Low confidence
        if extraction.get("confidence", 0) < 0.7:
            suggestions.append("Please review the extracted information for accuracy")
        
        # Specific suggestions based on issues
        for issue in issues:
            if issue.field == "subject" and issue.severity == "warning":
                suggestions.append(f"Verify subject name: {extraction.get('subject')}")
        
        return suggestions
    
    def validate_batch(
        self,
        extractions: List[Dict[str, Any]],
    ) -> List[ValidationResult]:
        """Validate multiple extractions."""
        return [
            self.validate(ext, ext.get("raw_text", ""))
            for ext in extractions
        ]
