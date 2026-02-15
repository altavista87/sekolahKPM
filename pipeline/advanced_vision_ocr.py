"""Advanced Vision OCR with ensemble methods and structured extraction."""

import base64
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import time
import re
from datetime import datetime

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

logger = logging.getLogger(__name__)


@dataclass
class HomeworkExtraction:
    """Structured homework extraction result."""
    subject: str = ""
    title: str = ""
    description: str = ""
    due_date: Optional[str] = None
    due_date_normalized: Optional[str] = None
    assignments: List[Dict[str, Any]] = field(default_factory=list)
    materials_needed: List[str] = field(default_factory=list)
    estimated_time: Optional[str] = None
    priority: str = "normal"  # low, normal, high, urgent
    raw_text: str = ""
    confidence: float = 0.0
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisionOCRResult:
    """Vision OCR result with metadata."""
    text: str
    structured: HomeworkExtraction
    confidence: float
    engine: str
    processing_time_ms: float
    image_quality_score: float = 0.0


class PromptEngineering:
    """Advanced prompts for better extraction."""
    
    HOMEWORK_SYSTEM_PROMPT = """You are an expert OCR system specialized in extracting homework information from images.
Your task is to:
1. Extract ALL text accurately from the homework image
2. Identify and structure the information into specific fields
3. Detect dates, subjects, and assignment details
4. Return ONLY valid JSON, no markdown formatting

Be precise and thorough. If information is unclear, mark it as such."""

    HOMEWORK_EXTRACTION_PROMPT = """Analyze this homework image and extract the following information in JSON format:

{
    "subject": "The school subject (Math, Science, English, etc.)",
    "title": "Brief title of the homework",
    "description": "Full description of what needs to be done",
    "due_date": "Due date as written in the image",
    "due_date_normalized": "Due date in YYYY-MM-DD format if detectable",
    "assignments": [
        {
            "task": "Individual task description",
            "page_numbers": "Page numbers if specified",
            "questions": "Specific questions to answer"
        }
    ],
    "materials_needed": ["List of materials required"],
    "estimated_time": "Estimated time to complete if mentioned",
    "priority": "Priority level: low, normal, high, or urgent"
}

Instructions:
- Extract ALL text visible in the image
- Identify the subject based on content
- Parse dates in various formats (e.g., "Due Friday", "Submit by 15/02/2026", etc.)
- Break down multiple assignments into the assignments array
- Return ONLY the JSON object, no additional text"""

    MULTILINGUAL_PROMPTS = {
        "en": HOMEWORK_EXTRACTION_PROMPT,
        "zh": """分析这张作业图片，并以JSON格式提取以下信息：

{
    "subject": "学科（数学、科学、英语等）",
    "title": "作业简短标题",
    "description": "需要完成的完整描述",
    "due_date": "图片中写明的截止日期",
    "due_date_normalized": "可检测到的YYYY-MM-DD格式日期",
    "assignments": [
        {
            "task": "具体任务描述",
            "page_numbers": "页码（如有）",
            "questions": "需要回答的具体问题"
        }
    ],
    "materials_needed": ["所需材料清单"],
    "estimated_time": "提及的预计完成时间",
    "priority": "优先级：low, normal, high, 或 urgent"
}

说明：
- 提取图片中所有可见文字
- 根据内容识别学科
- 解析各种日期格式
- 将多个作业分解到assignments数组
- 只返回JSON对象，不要其他文字""",
        "ms": """Analisis gambar kerja rumah ini dan ekstrak maklumat berikut dalam format JSON:

{
    "subject": "Subjek sekolah (Matematik, Sains, Bahasa Inggeris, dll.)",
    "title": "Tajuk ringkas kerja rumah",
    "description": "Penerangan lengkap apa yang perlu dilakukan",
    "due_date": "Tarikh akhir seperti tertulis dalam gambar",
    "due_date_normalized": "Tarikh akhir dalam format YYYY-MM-DD jika dapat dikesan",
    "assignments": [
        {
            "task": "Penerangan tugas individu",
            "page_numbers": "Nombor halaman jika dinyatakan",
            "questions": "Soalan spesifik untuk dijawab"
        }
    ],
    "materials_needed": ["Senarai bahan yang diperlukan"],
    "estimated_time": "Anggaran masa untuk selesai jika disebut",
    "priority": "Tahap keutamaan: low, normal, high, atau urgent"
}

Arahan:
- Ekstrak SEMUA teks yang kelihatan dalam gambar
- Kenal pasti subjek berdasarkan kandungan
- Parse tarikh dalam pelbagai format
- Pecahkan tugas berbilang ke dalam array assignments
- Hanya kembalikan objek JSON, tiada teks tambahan"""
    }


class TogetherAIVision:
    """Together AI Vision API with advanced prompting."""
    
    API_URL = "https://api.together.xyz/v1/chat/completions"
    
    # Available vision models on Together AI (best to good)
    MODELS = {
        "llama4_scout": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
        "llama4_maverick": "meta-llama/Llama-4-Maverick-17B-128E-Instruct",
        "llama3_2_vision_90b": "meta-llama/Llama-3.2-90B-Vision-Instruct",
        "llama3_2_vision_11b": "meta-llama/Llama-3.2-11B-Vision-Instruct",
        "nim_llama3_2_vision_90b": "nim/meta/llama-3.2-90b-vision-instruct",
        "nim_llama3_2_vision_11b": "nim/meta/llama-3.2-11b-vision-instruct",
        "qwen2_5_vl_72b": "Qwen/Qwen2.5-VL-72B-Instruct",
        "qwen2_5_vl": "Qwen/Qwen2.5-VL-72B-Instruct",
    }
    
    def __init__(self, api_key: str, model: str = None):
        if not HAS_HTTPX:
            raise ImportError("httpx not installed")
        self.api_key = api_key
        # Use Llama-3.2 vision model by default for image processing
        # Note: Together AI uses 'nim/' prefix for some models
        self.model = model or self.MODELS["nim_llama3_2_vision_90b"]
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def _get_mime_type(self, image_path: str) -> str:
        """Get MIME type from file extension."""
        ext = Path(image_path).suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        return mime_types.get(ext, "image/jpeg")
    
    async def extract_structured(
        self,
        image_path: str,
        language: str = "en"
    ) -> Tuple[str, HomeworkExtraction]:
        """Extract structured homework data from image."""
        base64_image = self._encode_image(image_path)
        mime_type = self._get_mime_type(image_path)
        
        prompt = PromptEngineering.MULTILINGUAL_PROMPTS.get(
            language, 
            PromptEngineering.MULTILINGUAL_PROMPTS["en"]
        )
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": PromptEngineering.HOMEWORK_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.API_URL,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
        
        content = data["choices"][0]["message"]["content"]
        
        # Parse JSON response
        try:
            structured = json.loads(content)
            extraction = self._dict_to_extraction(structured)
            raw_text = structured.get("description", content)
            return raw_text, extraction
        except json.JSONDecodeError:
            # Fallback: extract JSON from markdown
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                structured = json.loads(json_match.group(1))
                extraction = self._dict_to_extraction(structured)
                return structured.get("description", content), extraction
            raise
    
    def _dict_to_extraction(self, data: Dict) -> HomeworkExtraction:
        """Convert dict to HomeworkExtraction."""
        return HomeworkExtraction(
            subject=data.get("subject", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            due_date=data.get("due_date"),
            due_date_normalized=data.get("due_date_normalized"),
            assignments=data.get("assignments", []),
            materials_needed=data.get("materials_needed", []),
            estimated_time=data.get("estimated_time"),
            priority=data.get("priority", "normal"),
            raw_text=json.dumps(data),
            confidence=0.9,
        )


class GeminiVision:
    """Google Gemini Vision API with structured extraction."""
    
    MODELS = {
        "flash": "gemini-2.0-flash",
        "flash_latest": "models/gemini-flash-latest",
        "pro": "gemini-2.5-pro",
        "pro_latest": "models/gemini-pro-latest",
    }
    
    def __init__(self, api_key: str, model: str = None):
        try:
            import google.generativeai as genai
            self.genai = genai
            self.genai.configure(api_key=api_key)
            model_name = model or self.MODELS["flash"]
            # Ensure model name has correct prefix
            if not model_name.startswith("models/") and "/" not in model_name:
                model_name = f"models/{model_name}"
            self.model = self.genai.GenerativeModel(model_name)
        except ImportError:
            raise ImportError("google-generativeai not installed")
    
    async def extract_structured(
        self,
        image_path: str,
        language: str = "en"
    ) -> Tuple[str, HomeworkExtraction]:
        """Extract structured homework data from image."""
        if not HAS_PIL:
            raise ImportError("PIL not installed")
        
        image = Image.open(image_path)
        prompt = PromptEngineering.MULTILINGUAL_PROMPTS.get(
            language,
            PromptEngineering.MULTILINGUAL_PROMPTS["en"]
        )
        
        response = self.model.generate_content(
            [prompt, image],
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 4096,
            }
        )
        
        content = response.text
        
        # Parse JSON response
        try:
            # Clean up markdown formatting if present
            content_clean = re.sub(r'^```json\s*', '', content)
            content_clean = re.sub(r'\s*```$', '', content_clean)
            structured = json.loads(content_clean)
            extraction = self._dict_to_extraction(structured)
            return structured.get("description", content), extraction
        except json.JSONDecodeError:
            # Fallback: create basic extraction
            extraction = HomeworkExtraction(
                description=content,
                raw_text=content,
                confidence=0.7
            )
            return content, extraction
    
    def _dict_to_extraction(self, data: Dict) -> HomeworkExtraction:
        """Convert dict to HomeworkExtraction."""
        return HomeworkExtraction(
            subject=data.get("subject", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            due_date=data.get("due_date"),
            due_date_normalized=data.get("due_date_normalized"),
            assignments=data.get("assignments", []),
            materials_needed=data.get("materials_needed", []),
            estimated_time=data.get("estimated_time"),
            priority=data.get("priority", "normal"),
            raw_text=json.dumps(data),
            confidence=0.9,
        )


class EnsembleVisionOCR:
    """Ensemble multiple vision APIs for higher accuracy."""
    
    def __init__(
        self,
        together_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        together_model: str = None,
        gemini_model: str = None,
    ):
        self.engines: Dict[str, Any] = {}
        
        if together_api_key:
            self.engines["together"] = TogetherAIVision(
                api_key=together_api_key,
                model=together_model
            )
        
        if gemini_api_key:
            self.engines["gemini"] = GeminiVision(
                api_key=gemini_api_key,
                model=gemini_model
            )
        
        if not self.engines:
            raise ValueError("At least one vision API key required")
    
    async def extract(
        self,
        image_path: str,
        language: str = "en",
        use_ensemble: bool = True
    ) -> VisionOCRResult:
        """Extract text using single best engine or ensemble."""
        start_time = time.time()
        
        if not use_ensemble or len(self.engines) == 1:
            # Use single best engine
            engine_name = list(self.engines.keys())[0]
            engine = self.engines[engine_name]
            raw_text, extraction = await engine.extract_structured(image_path, language)
            
            processing_time = (time.time() - start_time) * 1000
            return VisionOCRResult(
                text=raw_text,
                structured=extraction,
                confidence=extraction.confidence,
                engine=engine_name,
                processing_time_ms=processing_time,
            )
        
        # Ensemble mode: run all engines and merge
        results = await self._run_all_engines(image_path, language)
        merged = self._ensemble_merge(results)
        
        processing_time = (time.time() - start_time) * 1000
        return VisionOCRResult(
            text=merged.structured.description,
            structured=merged.structured,
            confidence=merged.confidence,
            engine="ensemble",
            processing_time_ms=processing_time,
        )
    
    async def _run_all_engines(
        self,
        image_path: str,
        language: str
    ) -> List[Tuple[str, str, HomeworkExtraction]]:
        """Run all available engines concurrently."""
        tasks = []
        engine_names = []
        
        for name, engine in self.engines.items():
            task = engine.extract_structured(image_path, language)
            tasks.append(task)
            engine_names.append(name)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = []
        for name, result in zip(engine_names, results):
            if isinstance(result, Exception):
                logger.warning(f"Engine {name} failed: {result}")
                continue
            raw_text, extraction = result
            valid_results.append((name, raw_text, extraction))
        
        return valid_results
    
    def _ensemble_merge(
        self,
        results: List[Tuple[str, str, HomeworkExtraction]]
    ) -> VisionOCRResult:
        """Merge results from multiple engines using voting/consensus."""
        if not results:
            raise RuntimeError("All engines failed")
        
        if len(results) == 1:
            name, raw_text, extraction = results[0]
            return VisionOCRResult(
                text=raw_text,
                structured=extraction,
                confidence=extraction.confidence,
                engine=name,
                processing_time_ms=0,
            )
        
        # Extract fields from all results
        subjects = [r[2].subject for r in results if r[2].subject]
        titles = [r[2].title for r in results if r[2].title]
        descriptions = [r[2].description for r in results if r[2].description]
        due_dates = [r[2].due_date for r in results if r[2].due_date]
        
        # Vote on each field
        merged = HomeworkExtraction(
            subject=self._vote_field(subjects),
            title=self._vote_field(titles),
            description=self._vote_longest(descriptions),  # Longest is usually most complete
            due_date=self._vote_field(due_dates),
            due_date_normalized=self._extract_first([r[2].due_date_normalized for r in results]),
            assignments=self._merge_assignments([r[2].assignments for r in results]),
            materials_needed=self._unique_list(
                [item for r in results for item in r[2].materials_needed]
            ),
            estimated_time=self._vote_field([r[2].estimated_time for r in results if r[2].estimated_time]),
            priority=self._vote_priority([r[2].priority for r in results]),
            raw_text="\n\n".join([f"[{r[0]}]: {r[1]}" for r in results]),
            confidence=min(0.95, 0.8 + 0.1 * len(results)),  # Higher confidence with consensus
            extraction_metadata={
                "engines_used": [r[0] for r in results],
                "vote_counts": {
                    "subject": len(subjects),
                    "title": len(titles),
                    "description": len(descriptions),
                }
            }
        )
        
        return VisionOCRResult(
            text=merged.description,
            structured=merged,
            confidence=merged.confidence,
            engine=f"ensemble({','.join(r[0] for r in results)})",
            processing_time_ms=0,
        )
    
    def _vote_field(self, values: List[str]) -> str:
        """Select most common value."""
        if not values:
            return ""
        from collections import Counter
        return Counter(values).most_common(1)[0][0]
    
    def _vote_longest(self, values: List[str]) -> str:
        """Select longest value (usually most complete)."""
        if not values:
            return ""
        return max(values, key=len)
    
    def _extract_first(self, values: List) -> Optional[str]:
        """Extract first non-null value."""
        for v in values:
            if v:
                return v
        return None
    
    def _merge_assignments(self, assignment_lists: List[List[Dict]]) -> List[Dict]:
        """Merge assignments from multiple sources."""
        seen = set()
        merged = []
        for assignments in assignment_lists:
            for a in assignments:
                task = a.get("task", "")
                if task and task not in seen:
                    seen.add(task)
                    merged.append(a)
        return merged
    
    def _unique_list(self, items: List[str]) -> List[str]:
        """Get unique items preserving order."""
        seen = set()
        result = []
        for item in items:
            if item and item.lower() not in seen:
                seen.add(item.lower())
                result.append(item)
        return result
    
    def _vote_priority(self, priorities: List[str]) -> str:
        """Vote on priority with precedence: urgent > high > normal > low."""
        if not priorities:
            return "normal"
        priority_order = ["urgent", "high", "normal", "low"]
        for p in priority_order:
            if p in priorities:
                return p
        return "normal"


class AdvancedVisionOCR:
    """Main interface for advanced vision OCR."""
    
    def __init__(
        self,
        together_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        preferred_mode: str = "ensemble",  # ensemble, together, gemini
    ):
        self.together_key = together_api_key
        self.gemini_key = gemini_api_key
        self.preferred_mode = preferred_mode
        
        # Initialize ensemble
        self.ensemble = EnsembleVisionOCR(
            together_api_key=together_api_key,
            gemini_api_key=gemini_api_key,
        )
    
    async def process(
        self,
        image_path: str,
        language: str = "en",
        extract_structured: bool = True,
    ) -> VisionOCRResult:
        """Process image with best available vision OCR."""
        use_ensemble = self.preferred_mode == "ensemble" and len(self.ensemble.engines) > 1
        
        return await self.ensemble.extract(
            image_path=image_path,
            language=language,
            use_ensemble=use_ensemble
        )
    
    async def process_with_fallback(
        self,
        image_path: str,
        language: str = "en",
    ) -> VisionOCRResult:
        """Process with automatic fallback on failure."""
        engines_to_try = list(self.ensemble.engines.keys())
        
        for engine_name in engines_to_try:
            try:
                engine = self.ensemble.engines[engine_name]
                raw_text, extraction = await engine.extract_structured(image_path, language)
                return VisionOCRResult(
                    text=raw_text,
                    structured=extraction,
                    confidence=extraction.confidence,
                    engine=engine_name,
                    processing_time_ms=0,
                )
            except Exception as e:
                logger.warning(f"Engine {engine_name} failed: {e}")
                continue
        
        raise RuntimeError("All vision OCR engines failed")


# Convenience function for quick usage
async def extract_homework_from_image(
    image_path: str,
    together_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    language: str = "en",
    use_ensemble: bool = True,
) -> VisionOCRResult:
    """Quick extraction function."""
    ocr = AdvancedVisionOCR(
        together_api_key=together_api_key,
        gemini_api_key=gemini_api_key,
        preferred_mode="ensemble" if use_ensemble else "together",
    )
    return await ocr.process(image_path, language, use_ensemble)
