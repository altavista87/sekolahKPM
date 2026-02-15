"""AI Processor for pipeline."""

import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

import openai
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Structured extraction result."""
    subject: str
    title: str
    description: str
    due_date: Optional[str]
    priority: int
    keywords: List[str]
    estimated_time_minutes: Optional[int]
    materials_needed: List[str]
    questions: List[str]
    page_numbers: List[str]
    confidence: float


class PipelineAIProcessor:
    """OpenAI processor for the pipeline."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def extract_homework(
        self,
        ocr_text: str,
        context: Optional[Dict] = None,
    ) -> ExtractionResult:
        """Extract structured homework data from OCR text."""
        
        system_prompt = """You are an AI assistant specialized in extracting structured homework information from OCR text.

Extract these fields:
- subject: Subject/course name (e.g., "Mathematics", "English")
- title: Brief, descriptive title
- description: Full description of the assignment
- due_date: Due date in YYYY-MM-DD format, or null
- priority: Priority 1-5 (5 = urgent/must do first)
- keywords: Key terms/concepts
- estimated_time_minutes: Estimated completion time, or null
- materials_needed: Materials required
- questions: List of specific questions/tasks
- page_numbers: Page/exercise numbers mentioned
- confidence: Your confidence 0.0-1.0

Return ONLY a valid JSON object."""

        user_prompt = f"Context: {json.dumps(context) if context else 'None'}\n\nOCR Text:\n{ocr_text}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            return ExtractionResult(
                subject=data.get("subject", ""),
                title=data.get("title", ""),
                description=data.get("description", ""),
                due_date=data.get("due_date"),
                priority=data.get("priority", 3),
                keywords=data.get("keywords", []),
                estimated_time_minutes=data.get("estimated_time_minutes"),
                materials_needed=data.get("materials_needed", []),
                questions=data.get("questions", []),
                page_numbers=data.get("page_numbers", []),
                confidence=data.get("confidence", 0.8),
            )
            
        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            return self._fallback_result(ocr_text)
    
    def _fallback_result(self, ocr_text: str) -> ExtractionResult:
        """Create fallback extraction result."""
        return ExtractionResult(
            subject="",
            title="Untitled Homework",
            description=ocr_text[:1000],
            due_date=None,
            priority=3,
            keywords=[],
            estimated_time_minutes=None,
            materials_needed=[],
            questions=[],
            page_numbers=[],
            confidence=0.5,
        )
    
    async def enhance_description(
        self,
        description: str,
    ) -> str:
        """Enhance homework description."""
        prompt = f"Enhance this homework description to be clearer and more detailed:\n\n{description}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that improves text clarity."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                temperature=0.5,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Description enhancement failed: {e}")
            return description
    
    async def categorize_homework(
        self,
        extraction: ExtractionResult,
    ) -> Dict[str, Any]:
        """Categorize homework by type and difficulty."""
        prompt = f"""Categorize this homework:
Subject: {extraction.subject}
Title: {extraction.title}
Description: {extraction.description}

Provide: type (worksheet, project, reading, etc.), difficulty (easy/medium/hard), skills_required"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.5,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Categorization failed: {e}")
            return {"type": "unknown", "difficulty": "medium", "skills_required": []}
