"""AI Processor for enhancing OCR results."""

import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from abc import ABC, abstractmethod

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

from tenacity import retry, stop_after_attempt, wait_exponential

from .pii_redaction import redact_for_ai

logger = logging.getLogger(__name__)


@dataclass
class AIExtractionResult:
    """AI extraction result."""
    subject: str
    title: str
    description: str
    due_date: Optional[str]
    priority: int
    keywords: List[str]
    estimated_time_minutes: Optional[int]
    materials_needed: List[str]
    confidence: float
    raw_response: Dict[str, Any]
    # New fields for enhanced extraction
    homework_type: Optional[str] = None  # "buku_teks", "buku_latihan", "worksheet", "project", "other"
    homework_type_display: Optional[str] = None  # Display name in local language
    potential_names: List[str] = None  # AI-suggested potential homework titles/names
    what_to_achieve: Optional[str] = None  # Learning objectives/what student should achieve
    exercises_list: List[str] = None  # List of specific exercises/questions
    page_numbers: Optional[str] = None  # Page numbers mentioned
    textbook_title: Optional[str] = None  # Name of textbook if buku teks
    workbook_title: Optional[str] = None  # Name of workbook if buku latihan
    
    def __post_init__(self):
        if self.potential_names is None:
            self.potential_names = []
        if self.exercises_list is None:
            self.exercises_list = []


class BaseAIProcessor(ABC):
    """Base AI processor interface."""
    
    @abstractmethod
    async def extract_homework(
        self,
        ocr_text: str,
        language: str = "en",
    ) -> AIExtractionResult:
        """Extract structured homework data from OCR text."""
        pass
    
    @abstractmethod
    async def generate_reminder_message(
        self,
        homework: Dict[str, Any],
        days_until_due: int,
        language: str = "en",
    ) -> str:
        """Generate personalized reminder message."""
        pass


class OpenAIProcessor(BaseAIProcessor):
    """OpenAI GPT-4 processor for homework extraction."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ):
        if not HAS_OPENAI:
            raise ImportError("OpenAI not installed. Run: pip install openai")
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def extract_homework(
        self,
        ocr_text: str,
        language: str = "en",
    ) -> AIExtractionResult:
        """Extract structured homework data from OCR text with PII redaction."""
        
        # Redact PII before sending to external AI
        redacted_text = redact_for_ai(ocr_text)
        
        # Use redacted text for AI processing
        system_prompt = self._get_system_prompt(language)
        user_prompt = f"Extract homework information from this OCR text:\n\n{redacted_text}"
        
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
            result = json.loads(content)
            
            return AIExtractionResult(
                subject=result.get("subject", ""),
                title=result.get("title", ""),
                description=result.get("description", ""),
                due_date=result.get("due_date"),
                priority=result.get("priority", 3),
                keywords=result.get("keywords", []),
                estimated_time_minutes=result.get("estimated_time_minutes"),
                materials_needed=result.get("materials_needed", []),
                confidence=result.get("confidence", 0.8),
                raw_response=result,
                # New fields
                homework_type=result.get("homework_type"),
                homework_type_display=result.get("homework_type_display"),
                potential_names=result.get("potential_names", []),
                what_to_achieve=result.get("what_to_achieve"),
                exercises_list=result.get("exercises_list", []),
                page_numbers=result.get("page_numbers"),
                textbook_title=result.get("textbook_title"),
                workbook_title=result.get("workbook_title"),
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response: {e}")
            return self._fallback_result(ocr_text)
        except Exception as e:
            logger.error(f"AI processing failed: {e}")
            return self._fallback_result(ocr_text)
    
    def _get_system_prompt(self, language: str) -> str:
        """Get system prompt for homework extraction."""
        
        prompts = {
            "en": """You are an AI assistant that extracts structured homework information from OCR text.

Extract the following fields from the homework text:

REQUIRED FIELDS:
- subject: The subject/course name (e.g., Mathematics, Science, Bahasa Melayu)
- title: A brief title for the homework
- description: Full description of what needs to be done
- due_date: Due date in YYYY-MM-DD format if found, otherwise null
- priority: Priority from 1-5 (5 being highest urgency)
- keywords: List of key terms/keywords from the homework
- estimated_time_minutes: Estimated time to complete, or null if not specified
- materials_needed: List of materials needed
- confidence: Your confidence in the extraction (0.0-1.0)

NEW - HOMEWORK TYPE DETECTION:
- homework_type: The type of homework. Must be one of:
  * "buku_teks" - Textbook exercises (e.g., "Buku Teks Matematik", "Textbook")
  * "buku_latihan" - Workbook/Exercise book (e.g., "Buku Latihan", "Activity Book", "Workbook")
  * "worksheet" - Printed worksheet/handout
  * "project" - Project-based assignment
  * "other" - Other type
- homework_type_display: Display name in the appropriate language (e.g., "Buku Teks", "Buku Latihan", "Worksheet")

NEW - POTENTIAL NAMES & OBJECTIVES:
- potential_names: Array of 2-3 AI-suggested potential homework titles/names based on the content (e.g., ["Algebra Exercises", "Chapter 5 Practice", "Linear Equations Homework"])
- what_to_achieve: What the student should achieve/learn from this homework. Describe the learning objectives in 1-2 sentences (e.g., "Practice solving linear equations and understand the concept of variables")

NEW - DETAILED EXERCISES:
- exercises_list: Array of specific exercises/questions found (e.g., ["Question 1a", "Exercise 2.3", "Page 45, Q1-5"])
- page_numbers: Page numbers mentioned (e.g., "45-47" or "Page 12")
- textbook_title: Name of textbook if mentioned (e.g., "Buku Teks Matematik Tingkatan 1")
- workbook_title: Name of workbook if mentioned (e.g., "Buku Aktiviti Matematik")

Return ONLY a valid JSON object with these fields.""",
            
            "zh": """你是一个从OCR文本中提取结构化作业信息的AI助手。

从作业文本中提取以下字段：

必填字段：
- subject: 学科/课程名称（例如：数学、科学、国语）
- title: 作业简要标题
- description: 需要完成的完整描述
- due_date: 截止日期（YYYY-MM-DD格式），如果未找到则为null
- priority: 优先级1-5（5为最高紧急度）
- keywords: 作业中的关键术语/关键词列表
- estimated_time_minutes: 预计完成时间，如果未指定则为null
- materials_needed: 所需材料列表
- confidence: 你对提取结果的信心（0.0-1.0）

新增 - 作业类型检测：
- homework_type: 作业类型。必须是以下之一：
  * "buku_teks" - 课本练习（例如："Buku Teks Matematik"、"Textbook"）
  * "buku_latihan" - 练习簿/作业本（例如："Buku Latihan"、"Activity Book"、"Workbook"）
  * "worksheet" - 印刷工作表
  * "project" - 专题作业
  * "other" - 其他类型
- homework_type_display: 以适当语言显示的类别名称（例如："课本"、"练习簿"、"工作表"）

新增 - 建议名称与目标：
- potential_names: AI根据内容建议的2-3个潜在作业标题/名称（例如：["代数练习", "第五章练习", "线性方程式作业"]）
- what_to_achieve: 学生应从此作业中达到/学习什么。用1-2句话描述学习目标（例如："练习解线性方程式并理解变量的概念"）

新增 - 详细练习：
- exercises_list: 找到的具体练习/问题列表（例如：["问题1a", "练习2.3", "第45页，Q1-5"]）
- page_numbers: 提到的页码（例如："45-47" 或 "第12页"）
- textbook_title: 如果提到课本名称（例如："Buku Teks Matematik Tingkatan 1"）
- workbook_title: 如果提到练习簿名称（例如："Buku Aktiviti Matematik"）

只返回包含这些字段的有效JSON对象。""",
            
            "ms": """Anda adalah pembantu AI yang mengekstrak maklumat kerja rumah berstruktur daripada teks OCR.

Ekstrak medan berikut dari teks kerja rumah:

MEDAN WAJIB:
- subject: Nama subjek/kursus (contoh: Matematik, Sains, Bahasa Melayu)
- title: Tajuk ringkas untuk kerja rumah
- description: Penerangan penuh apa yang perlu dilakukan
- due_date: Tarikh akhir dalam format YYYY-MM-DD jika dijumpai, jika tidak null
- priority: Keutamaan dari 1-5 (5 adalah paling mendesak)
- keywords: Senarai istilah utama/kata kunci dari kerja rumah
- estimated_time_minutes: Anggaran masa untuk selesai, atau null jika tidak ditentukan
- materials_needed: Senarai bahan yang diperlukan
- confidence: Keyakinan anda dalam pengekstrakan (0.0-1.0)

BAHARU - PENGESANAN JENIS KERJA RUMAH:
- homework_type: Jenis kerja rumah. Mestilah salah satu daripada:
  * "buku_teks" - Latihan buku teks (contoh: "Buku Teks Matematik", "Textbook")
  * "buku_latihan" - Buku latihan/aktiviti (contoh: "Buku Latihan", "Activity Book", "Workbook")
  * "worksheet" - Lembaran kerja bercetak
  * "project" - Kerja berbentuk projek
  * "other" - Jenis lain
- homework_type_display: Nama paparan dalam bahasa yang sesuai (contoh: "Buku Teks", "Buku Latihan", "Worksheet")

BAHARU - NAMA CADANGAN & OBJEKTIF:
- potential_names: Tatasusunan 2-3 tajuk/nama kerja rumah yang dicadangkan oleh AI berdasarkan kandungan (contoh: ["Latihan Algebra", "Latihan Bab 5", "Kerja Rumah Persamaan Linear"])
- what_to_achieve: Apa yang pelajar harus capai/pelajari daripada kerja rumah ini. Terangkan objektif pembelajaran dalam 1-2 ayat (contoh: "Berlatih menyelesaikan persamaan linear dan memahami konsep pemboleh ubah")

BAHARU - LATIHAN TERPERINCI:
- exercises_list: Tatasusunan latihan/soalan khusus yang dijumpai (contoh: ["Soalan 1a", "Latihan 2.3", "Muka surat 45, S1-5"])
- page_numbers: Nombor muka surat yang disebut (contoh: "45-47" atau "Muka surat 12")
- textbook_title: Nama buku teks jika disebut (contoh: "Buku Teks Matematik Tingkatan 1")
- workbook_title: Nama buku latihan jika disebut (contoh: "Buku Aktiviti Matematik")

Hanya kembalikan objek JSON yang sah dengan medan ini.""",
        }
        
        return prompts.get(language, prompts["en"])
    
    def _fallback_result(self, ocr_text: str) -> AIExtractionResult:
        """Create fallback result when AI fails."""
        return AIExtractionResult(
            subject="",
            title="",
            description=ocr_text[:500],
            due_date=None,
            priority=3,
            keywords=[],
            estimated_time_minutes=None,
            materials_needed=[],
            confidence=0.5,
            raw_response={},
            homework_type=None,
            homework_type_display=None,
            potential_names=[],
            what_to_achieve=None,
            exercises_list=[],
            page_numbers=None,
            textbook_title=None,
            workbook_title=None,
        )
    
    async def generate_reminder_message(
        self,
        homework: Dict[str, Any],
        days_until_due: int,
        language: str = "en",
    ) -> str:
        """Generate personalized reminder message."""
        
        templates = {
            "en": {
                "urgent": "🔔 URGENT: \"{title}\" is due in {days} day{'s' if days != 1 else ''}! Don't forget to complete it.",
                "upcoming": "📚 Reminder: \"{title}\" ({subject}) is due on {due_date}. Start working on it soon!",
                "tomorrow": "⏰ Tomorrow's deadline: \"{title}\". Make sure to finish it tonight!",
            },
            "zh": {
                "urgent": "🔔 紧急：\"{title}\" 还有{days}天到期！别忘了完成。",
                "upcoming": "📚 提醒：\"{title}\"（{subject}）截止日期是{due_date}。早点开始吧！",
                "tomorrow": "⏰ 明天截止：\"{title}\"。今晚一定要完成！",
            },
            "ms": {
                "urgent": "🔔 PENTING: \"{title}\" matang dalam {days} hari! Jangan lupa untuk menyiapkannya.",
                "upcoming": "📚 Peringatan: \"{title}\" ({subject}) matang pada {due_date}. Mulakan segera!",
                "tomorrow": "⏰ Matang esok: \"{title}\". Pastikan siap malam ini!",
            },
        }
        
        lang_templates = templates.get(language, templates["en"])
        
        if days_until_due == 1:
            template = lang_templates["tomorrow"]
        elif days_until_due <= 2:
            template = lang_templates["urgent"]
        else:
            template = lang_templates["upcoming"]
        
        return template.format(
            title=homework.get("title", "Homework"),
            subject=homework.get("subject", ""),
            days=days_until_due,
            due_date=homework.get("due_date", ""),
        )


class GeminiProcessor(BaseAIProcessor):
    """Google Gemini processor for homework extraction."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
    ):
        if not HAS_GEMINI:
            raise ImportError("Google Generative AI not installed. Run: pip install google-generativeai")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def extract_homework(
        self,
        ocr_text: str,
        language: str = "en",
    ) -> AIExtractionResult:
        """Extract structured homework data from OCR text using Gemini with PII redaction."""
        
        # Redact PII before sending to external AI
        redacted_text = redact_for_ai(ocr_text)
        
        prompt = self._get_prompt(language, redacted_text)
        
        try:
            response = self.model.generate_content(prompt)
            content = response.text
            
            # Extract JSON from response (Gemini might wrap in markdown)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            
            return AIExtractionResult(
                subject=result.get("subject", ""),
                title=result.get("title", ""),
                description=result.get("description", ""),
                due_date=result.get("due_date"),
                priority=result.get("priority", 3),
                keywords=result.get("keywords", []),
                estimated_time_minutes=result.get("estimated_time_minutes"),
                materials_needed=result.get("materials_needed", []),
                confidence=result.get("confidence", 0.8),
                raw_response=result,
                # New fields
                homework_type=result.get("homework_type"),
                homework_type_display=result.get("homework_type_display"),
                potential_names=result.get("potential_names", []),
                what_to_achieve=result.get("what_to_achieve"),
                exercises_list=result.get("exercises_list", []),
                page_numbers=result.get("page_numbers"),
                textbook_title=result.get("textbook_title"),
                workbook_title=result.get("workbook_title"),
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            return self._fallback_result(ocr_text)
        except Exception as e:
            logger.error(f"Gemini processing failed: {e}")
            return self._fallback_result(ocr_text)
    
    def _get_prompt(self, language: str, ocr_text: str) -> str:
        """Get extraction prompt for Gemini."""
        
        prompts = {
            "en": f"""Extract structured homework information from this OCR text.

Return ONLY a valid JSON object with these fields:

REQUIRED FIELDS:
- subject: The subject/course name (e.g., Mathematics, Science, Bahasa Melayu)
- title: A brief title for the homework
- description: Full description of what needs to be done
- due_date: Due date in YYYY-MM-DD format if found, otherwise null
- priority: Priority from 1-5 (5 being highest urgency)
- keywords: List of key terms/keywords from the homework
- estimated_time_minutes: Estimated time to complete, or null if not specified
- materials_needed: List of materials needed
- confidence: Your confidence in the extraction (0.0-1.0)

HOMEWORK TYPE DETECTION:
- homework_type: The type of homework. Must be one of: "buku_teks", "buku_latihan", "worksheet", "project", "other"
- homework_type_display: Display name in appropriate language (e.g., "Buku Teks", "Buku Latihan", "Worksheet")

POTENTIAL NAMES & OBJECTIVES:
- potential_names: Array of 2-3 AI-suggested potential homework titles based on content
- what_to_achieve: What the student should achieve/learn from this homework (1-2 sentences describing learning objectives)

DETAILED EXERCISES:
- exercises_list: Array of specific exercises/questions found (e.g., ["Question 1a", "Exercise 2.3", "Page 45, Q1-5"])
- page_numbers: Page numbers mentioned (e.g., "45-47" or "Page 12")
- textbook_title: Name of textbook if mentioned
- workbook_title: Name of workbook if mentioned

OCR text:
{ocr_text}""",
            
            "zh": f"""从OCR文本中提取结构化作业信息。

只返回包含这些字段的有效JSON对象：

必填字段：
- subject: 学科/课程名称（例如：数学、科学、国语）
- title: 作业简要标题
- description: 需要完成的完整描述
- due_date: 截止日期（YYYY-MM-DD格式），如果未找到则为null
- priority: 优先级1-5（5为最高紧急度）
- keywords: 作业中的关键术语/关键词列表
- estimated_time_minutes: 预计完成时间，如果未指定则为null
- materials_needed: 所需材料列表
- confidence: 你对提取结果的信心（0.0-1.0）

作业类型检测：
- homework_type: 作业类型。必须是以下之一："buku_teks"、"buku_latihan"、"worksheet"、"project"、"other"
- homework_type_display: 以适当语言显示的类别名称（例如："课本"、"练习簿"、"工作表"）

建议名称与目标：
- potential_names: AI根据内容建议的2-3个潜在作业标题/名称
- what_to_achieve: 学生应从此作业中达到/学习什么（用1-2句话描述学习目标）

详细练习：
- exercises_list: 找到的具体练习/问题列表（例如：["问题1a"、"练习2.3"、"第45页，Q1-5"]）
- page_numbers: 提到的页码（例如："45-47" 或 "第12页"）
- textbook_title: 如果提到课本名称
- workbook_title: 如果提到练习簿名称

OCR文本：
{ocr_text}""",
            
            "ms": f"""Ekstrak maklumat kerja rumah berstruktur daripada teks OCR.

Hanya kembalikan objek JSON yang sah dengan medan ini:

MEDAN WAJIB:
- subject: Nama subjek/kursus (contoh: Matematik, Sains, Bahasa Melayu)
- title: Tajuk ringkas untuk kerja rumah
- description: Penerangan penuh apa yang perlu dilakukan
- due_date: Tarikh akhir dalam format YYYY-MM-DD jika dijumpai, jika tidak null
- priority: Keutamaan dari 1-5 (5 adalah paling mendesak)
- keywords: Senarai istilah utama/kata kunci dari kerja rumah
- estimated_time_minutes: Anggaran masa untuk selesai, atau null jika tidak ditentukan
- materials_needed: Senarai bahan yang diperlukan
- confidence: Keyakinan anda dalam pengekstrakan (0.0-1.0)

PENGESANAN JENIS KERJA RUMAH:
- homework_type: Jenis kerja rumah. Mestilah salah satu daripada: "buku_teks", "buku_latihan", "worksheet", "project", "other"
- homework_type_display: Nama paparan dalam bahasa yang sesuai (contoh: "Buku Teks", "Buku Latihan", "Worksheet")

NAMA CADANGAN & OBJEKTIF:
- potential_names: Tatasusunan 2-3 tajuk kerja rumah yang dicadangkan oleh AI berdasarkan kandungan
- what_to_achieve: Apa yang pelajar harus capai/pelajari daripada kerja rumah ini (1-2 ayat menerangkan objektif pembelajaran)

LATIHAN TERPERINCI:
- exercises_list: Tatasusunan latihan/soalan khusus yang dijumpai (contoh: ["Soalan 1a", "Latihan 2.3", "Muka surat 45, S1-5"])
- page_numbers: Nombor muka surat yang disebut (contoh: "45-47" atau "Muka surat 12")
- textbook_title: Nama buku teks jika disebut
- workbook_title: Nama buku latihan jika disebut

Teks OCR:
{ocr_text}""",
        }
        
        return prompts.get(language, prompts["en"])
    
    def _fallback_result(self, ocr_text: str) -> AIExtractionResult:
        """Create fallback result when AI fails."""
        return AIExtractionResult(
            subject="",
            title="",
            description=ocr_text[:500],
            due_date=None,
            priority=3,
            keywords=[],
            estimated_time_minutes=None,
            materials_needed=[],
            confidence=0.5,
            raw_response={},
            homework_type=None,
            homework_type_display=None,
            potential_names=[],
            what_to_achieve=None,
            exercises_list=[],
            page_numbers=None,
            textbook_title=None,
            workbook_title=None,
        )
    
    async def generate_reminder_message(
        self,
        homework: Dict[str, Any],
        days_until_due: int,
        language: str = "en",
    ) -> str:
        """Generate personalized reminder message."""
        
        templates = {
            "en": {
                "urgent": "🔔 URGENT: \"{title}\" is due in {days} day{'s' if days != 1 else ''}! Don't forget to complete it.",
                "upcoming": "📚 Reminder: \"{title}\" ({subject}) is due on {due_date}. Start working on it soon!",
                "tomorrow": "⏰ Tomorrow's deadline: \"{title}\". Make sure to finish it tonight!",
            },
            "zh": {
                "urgent": "🔔 紧急：\"{title}\" 还有{days}天到期！别忘了完成。",
                "upcoming": "📚 提醒：\"{title}\"（{subject}）截止日期是{due_date}。早点开始吧！",
                "tomorrow": "⏰ 明天截止：\"{title}\"。今晚一定要完成！",
            },
            "ms": {
                "urgent": "🔔 PENTING: \"{title}\" matang dalam {days} hari! Jangan lupa untuk menyiapkannya.",
                "upcoming": "📚 Peringatan: \"{title}\" ({subject}) matang pada {due_date}. Mulakan segera!",
                "tomorrow": "⏰ Matang esok: \"{title}\". Pastikan siap malam ini!",
            },
        }
        
        lang_templates = templates.get(language, templates["en"])
        
        if days_until_due == 1:
            template = lang_templates["tomorrow"]
        elif days_until_due <= 2:
            template = lang_templates["urgent"]
        else:
            template = lang_templates["upcoming"]
        
        return template.format(
            title=homework.get("title", "Homework"),
            subject=homework.get("subject", ""),
            days=days_until_due,
            due_date=homework.get("due_date", ""),
        )


class AIProcessor:
    """Unified AI processor that supports both OpenAI and Gemini."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        provider: str = "openai",
    ):
        """
        Initialize AI processor.
        
        Args:
            api_key: API key for the provider
            model: Model name
            max_tokens: Max tokens (OpenAI only)
            temperature: Temperature (OpenAI only)
            provider: 'openai' or 'gemini'
        """
        self.provider = provider
        
        if provider == "gemini":
            self._processor = GeminiProcessor(api_key, model)
        else:
            self._processor = OpenAIProcessor(api_key, model, max_tokens, temperature)
    
    async def extract_homework(
        self,
        ocr_text: str,
        language: str = "en",
    ) -> AIExtractionResult:
        """Extract structured homework data from OCR text."""
        return await self._processor.extract_homework(ocr_text, language)
    
    async def generate_reminder_message(
        self,
        homework: Dict[str, Any],
        days_until_due: int,
        language: str = "en",
    ) -> str:
        """Generate personalized reminder message."""
        return await self._processor.generate_reminder_message(homework, days_until_due, language)
    
    async def validate_homework_data(
        self,
        extraction_result: AIExtractionResult,
    ) -> Dict[str, Any]:
        """Validate extracted homework data."""
        issues = []
        
        if not extraction_result.subject:
            issues.append("Subject is missing")
        
        if not extraction_result.description:
            issues.append("Description is missing")
        
        if extraction_result.confidence < 0.6:
            issues.append("Low confidence in extraction")
        
        # Validate date format if present
        if extraction_result.due_date:
            try:
                datetime.strptime(extraction_result.due_date, "%Y-%m-%d")
            except ValueError:
                issues.append("Invalid due date format")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "confidence": extraction_result.confidence,
        }
