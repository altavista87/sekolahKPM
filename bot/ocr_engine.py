"""OCR Engine for extracting text from homework images."""

import base64
import json
import logging
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
import io
import time
import asyncio

import numpy as np
from PIL import Image

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    from pipeline.advanced_vision_ocr import (
        AdvancedVisionOCR, 
        EnsembleVisionOCR,
        VisionOCRResult,
        HomeworkExtraction,
        extract_homework_from_image
    )
    HAS_ADVANCED_VISION = True
except ImportError:
    HAS_ADVANCED_VISION = False

logger = logging.getLogger(__name__)


@dataclass
class OCResult:
    """OCR result data."""
    text: str
    confidence: float
    language: str
    bounding_boxes: List[Dict[str, Any]]
    processing_time_ms: float


class TogetherAIOCR:
    """Together AI Vision API for OCR using Llama 4 and other vision models."""
    
    API_URL = "https://api.together.xyz/v1/chat/completions"
    
    def __init__(self, api_key: str, model: str = "meta-llama/Llama-4-Scout-17B-16E-Instruct"):
        if not HAS_HTTPX:
            raise ImportError("httpx not installed. Run: pip install httpx")
        self.api_key = api_key
        self.model = model
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
    
    async def process_image(
        self,
        image_path: str,
        language_hint: str = "en",
    ) -> OCResult:
        """Process image using Together AI Vision API."""
        start_time = time.time()
        
        # Encode image
        base64_image = self._encode_image(image_path)
        mime_type = self._get_mime_type(image_path)
        
        # Prepare prompt based on language
        prompts = {
            "en": "Extract all text from this homework image. Return ONLY the extracted text, nothing else.",
            "zh": "从这张作业图片中提取所有文字。只返回提取的文字，其他不要。",
            "ms": "Ekstrak semua teks dari gambar kerja rumah ini. Hanya kembalikan teks yang diekstrak.",
        }
        prompt = prompts.get(language_hint, prompts["en"])
        
        # Prepare request payload
        payload = {
            "model": self.model,
            "messages": [
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
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.API_URL,
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
            
            # Extract text from response
            extracted_text = data["choices"][0]["message"]["content"].strip()
            
            processing_time = (time.time() - start_time) * 1000
            
            # Calculate rough confidence based on response
            confidence = 0.9 if len(extracted_text) > 10 else 0.7
            
            return OCResult(
                text=extracted_text,
                confidence=confidence,
                language=language_hint,
                bounding_boxes=[],  # Vision API doesn't provide bounding boxes
                processing_time_ms=processing_time,
            )
            
        except Exception as e:
            logger.error(f"Together AI OCR failed: {e}")
            raise


class DeepSeekOCR:
    """DeepSeek API for OCR (if vision model available) or text enhancement."""
    
    API_URL = "https://api.deepseek.com/v1/chat/completions"
    
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        if not HAS_HTTPX:
            raise ImportError("httpx not installed. Run: pip install httpx")
        self.api_key = api_key
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    async def process_image(
        self,
        image_path: str,
        language_hint: str = "en",
    ) -> OCResult:
        """Process image using DeepSeek Vision (if available)."""
        start_time = time.time()
        
        # Encode image
        base64_image = self._encode_image(image_path)
        
        prompts = {
            "en": "Extract all text from this image. Return ONLY the extracted text.",
            "zh": "从图片中提取所有文字。只返回提取的文字。",
            "ms": "Ekstrak semua teks dari gambar ini. Hanya kembalikan teks.",
        }
        prompt = prompts.get(language_hint, prompts["en"])
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4096,
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.API_URL,
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
            
            extracted_text = data["choices"][0]["message"]["content"].strip()
            processing_time = (time.time() - start_time) * 1000
            
            return OCResult(
                text=extracted_text,
                confidence=0.85,
                language=language_hint,
                bounding_boxes=[],
                processing_time_ms=processing_time,
            )
            
        except Exception as e:
            logger.error(f"DeepSeek OCR failed: {e}")
            raise
    
    async def enhance_text(self, raw_text: str, language: str = "en") -> str:
        """Enhance/fix OCR text using DeepSeek."""
        prompts = {
            "en": f"Fix any OCR errors in this text and format it properly:\n\n{raw_text}",
            "zh": f"修正这段文字中的OCR错误并正确格式化：\n\n{raw_text}",
            "ms": f"Betulkan sebarang ralat OCR dalam teks ini:\n\n{raw_text}",
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompts.get(language, prompts["en"])}
            ],
            "max_tokens": 2048,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.API_URL,
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
            
            return data["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            logger.error(f"DeepSeek text enhancement failed: {e}")
            return raw_text


class GeminiOCR:
    """Google Gemini Vision API for OCR."""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        try:
            import google.generativeai as genai
            self.genai = genai
            self.genai.configure(api_key=api_key)
            self.model = self.genai.GenerativeModel(model)
        except ImportError:
            raise ImportError("Google Generative AI not installed. Run: pip install google-generativeai")
    
    async def process_image(
        self,
        image_path: str,
        language_hint: str = "en",
    ) -> OCResult:
        """Process image using Gemini Vision."""
        start_time = time.time()
        
        # Load image
        from PIL import Image
        image = Image.open(image_path)
        
        prompts = {
            "en": "Extract all text from this homework image. Return ONLY the extracted text, nothing else.",
            "zh": "从这张作业图片中提取所有文字。只返回提取的文字，其他不要。",
            "ms": "Ekstrak semua teks dari gambar kerja rumah ini. Hanya kembalikan teks.",
        }
        prompt = prompts.get(language_hint, prompts["en"])
        
        try:
            response = self.model.generate_content([prompt, image])
            extracted_text = response.text.strip()
            
            processing_time = (time.time() - start_time) * 1000
            
            return OCResult(
                text=extracted_text,
                confidence=0.9,
                language=language_hint,
                bounding_boxes=[],
                processing_time_ms=processing_time,
            )
            
        except Exception as e:
            logger.error(f"Gemini OCR failed: {e}")
            raise


class OCREngine:
    """Multi-engine OCR processor supporting traditional OCR and LLM Vision APIs."""
    
    SUPPORTED_LANGUAGES = {
        "en": "english",
        "zh": "chinese",
        "ms": "malay",
        "chi_sim": "chinese_simplified",
        "chi_tra": "chinese_traditional",
    }
    
    def __init__(
        self,
        tesseract_cmd: str = "/usr/bin/tesseract",
        ocr_language: str = "eng+chi_sim+chi_tra+msa",
        use_easyocr: bool = True,
        use_tesseract: bool = True,
        gpu: bool = False,
        # LLM Vision APIs
        together_api_key: Optional[str] = None,
        together_model: str = "meta-llama/Llama-4-Scout-17B-16E-Instruct",
        gemini_api_key: Optional[str] = None,
        gemini_model: str = "gemini-1.5-flash",
        deepseek_api_key: Optional[str] = None,
        deepseek_model: str = "deepseek-chat",
        preferred_engine: str = "auto",  # auto, together, gemini, deepseek, easyocr, tesseract
    ):
        self.tesseract_cmd = tesseract_cmd
        self.ocr_language = ocr_language
        self.use_easyocr = use_easyocr
        self.use_tesseract = use_tesseract
        self.gpu = gpu
        self.preferred_engine = preferred_engine
        
        # Initialize traditional OCR
        self._easyocr_reader = None
        self._tesseract_available = False
        
        # Initialize LLM Vision APIs
        self._together_ocr = None
        self._gemini_ocr = None
        self._deepseek_ocr = None
        
        self._initialize_engines(
            together_api_key=together_api_key,
            together_model=together_model,
            gemini_api_key=gemini_api_key,
            gemini_model=gemini_model,
            deepseek_api_key=deepseek_api_key,
            deepseek_model=deepseek_model,
        )
    
    def _initialize_engines(self, **kwargs):
        """Initialize all OCR engines."""
        # Initialize LLM Vision APIs first (preferred)
        if kwargs.get("together_api_key"):
            try:
                self._together_ocr = TogetherAIOCR(
                    api_key=kwargs["together_api_key"],
                    model=kwargs["together_model"],
                )
                logger.info(f"Together AI OCR initialized with model: {kwargs['together_model']}")
            except Exception as e:
                logger.warning(f"Failed to initialize Together AI OCR: {e}")
        
        if kwargs.get("gemini_api_key"):
            try:
                self._gemini_ocr = GeminiOCR(
                    api_key=kwargs["gemini_api_key"],
                    model=kwargs["gemini_model"],
                )
                logger.info(f"Gemini OCR initialized with model: {kwargs['gemini_model']}")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini OCR: {e}")
        
        if kwargs.get("deepseek_api_key"):
            try:
                self._deepseek_ocr = DeepSeekOCR(
                    api_key=kwargs["deepseek_api_key"],
                    model=kwargs["deepseek_model"],
                )
                logger.info(f"DeepSeek OCR initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize DeepSeek OCR: {e}")
        
        # Initialize traditional OCR as fallback
        if self.use_easyocr:
            try:
                import easyocr
                lang_list = ["en", "ch_sim", "ch_tra", "ms"]
                self._easyocr_reader = easyocr.Reader(
                    lang_list,
                    gpu=self.gpu,
                    verbose=False,
                )
                logger.info("EasyOCR initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize EasyOCR: {e}")
                self._easyocr_reader = None
        
        if self.use_tesseract:
            try:
                import pytesseract
                pytesseract.get_tesseract_version()
                self._tesseract_available = True
                logger.info("Tesseract OCR available")
            except Exception as e:
                logger.warning(f"Tesseract not available: {e}")
                self._tesseract_available = False
    
    def _select_engine(self) -> str:
        """Select the best available OCR engine."""
        if self.preferred_engine != "auto":
            return self.preferred_engine
        
        # Priority: LLM Vision APIs > Traditional OCR
        if self._together_ocr:
            return "together"
        if self._gemini_ocr:
            return "gemini"
        if self._deepseek_ocr:
            return "deepseek"
        if self._easyocr_reader:
            return "easyocr"
        if self._tesseract_available:
            return "tesseract"
        
        raise RuntimeError("No OCR engine available!")
    
    async def process_image(
        self,
        image_path: str,
        preprocess: bool = True,
        language_hint: str = "en",
    ) -> OCResult:
        """Process image and extract text using the best available engine."""
        start_time = time.time()
        
        engine = self._select_engine()
        logger.info(f"Using OCR engine: {engine}")
        
        try:
            if engine == "together":
                return await self._together_ocr.process_image(image_path, language_hint)
            elif engine == "gemini":
                return await self._gemini_ocr.process_image(image_path, language_hint)
            elif engine == "deepseek":
                return await self._deepseek_ocr.process_image(image_path, language_hint)
            else:
                # Traditional OCR path
                return await self._process_traditional(image_path, preprocess)
                
        except Exception as e:
            logger.error(f"Primary OCR engine ({engine}) failed: {e}")
            # Try fallback engines
            return await self._fallback_ocr(image_path, language_hint)
    
    async def _process_traditional(self, image_path: str, preprocess: bool) -> OCResult:
        """Process using traditional OCR engines."""
        import time
        start_time = time.time()
        
        # Load image
        image = self._load_image(image_path)
        
        # Preprocess if enabled
        if preprocess and HAS_CV2:
            image = self._preprocess_image(image)
        
        # Run OCR engines
        results = []
        
        if self._easyocr_reader:
            try:
                easyocr_result = self._run_easyocr(image)
                results.append(easyocr_result)
            except Exception as e:
                logger.error(f"EasyOCR failed: {e}")
        
        if self._tesseract_available:
            try:
                tesseract_result = self._run_tesseract(image)
                results.append(tesseract_result)
            except Exception as e:
                logger.error(f"Tesseract failed: {e}")
        
        # Merge results
        merged = self._merge_results(results)
        
        processing_time = (time.time() - start_time) * 1000
        
        return OCResult(
            text=merged["text"],
            confidence=merged["confidence"],
            language=self._detect_language(merged["text"]),
            bounding_boxes=merged["boxes"],
            processing_time_ms=processing_time,
        )
    
    async def _fallback_ocr(self, image_path: str, language_hint: str) -> OCResult:
        """Try fallback OCR engines."""
        engines = []
        
        if self._together_ocr:
            engines.append(("together", self._together_ocr.process_image))
        if self._gemini_ocr:
            engines.append(("gemini", self._gemini_ocr.process_image))
        if self._deepseek_ocr:
            engines.append(("deepseek", self._deepseek_ocr.process_image))
        if self._easyocr_reader:
            engines.append(("easyocr", lambda p, l: self._process_traditional(p, True)))
        
        for name, processor in engines:
            try:
                logger.info(f"Trying fallback OCR: {name}")
                return await processor(image_path, language_hint)
            except Exception as e:
                logger.warning(f"Fallback {name} failed: {e}")
                continue
        
        raise RuntimeError("All OCR engines failed!")
    
    def _load_image(self, image_path: str) -> np.ndarray:
        """Load image from path."""
        if HAS_CV2:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Failed to load image: {image_path}")
            return image
        else:
            # Fallback to PIL
            from PIL import Image
            img = Image.open(image_path)
            return np.array(img)
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR."""
        if not HAS_CV2:
            return image
            
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Adaptive thresholding
        binary = cv2.adaptiveThreshold(
            denoised, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )
        
        return binary
    
    def _run_easyocr(self, image: np.ndarray) -> Dict[str, Any]:
        """Run EasyOCR on image."""
        results = self._easyocr_reader.readtext(image)
        
        texts = []
        confidences = []
        boxes = []
        
        for bbox, text, conf in results:
            texts.append(text)
            confidences.append(conf)
            boxes.append({
                "text": text,
                "confidence": conf,
                "bbox": bbox,
            })
        
        full_text = " ".join(texts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "text": full_text,
            "confidence": avg_confidence,
            "boxes": boxes,
        }
    
    def _run_tesseract(self, image: np.ndarray) -> Dict[str, Any]:
        """Run Tesseract OCR on image."""
        import pytesseract
        
        custom_config = r'--oem 3 --psm 6'
        
        data = pytesseract.image_to_data(
            image,
            lang=self.ocr_language,
            config=custom_config,
            output_type=pytesseract.Output.DICT,
        )
        
        texts = []
        confidences = []
        boxes = []
        
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            if int(data['conf'][i]) > 30:  # Filter low confidence
                text = data['text'][i].strip()
                if text:
                    texts.append(text)
                    confidences.append(int(data['conf'][i]) / 100)
                    boxes.append({
                        "text": text,
                        "confidence": int(data['conf'][i]) / 100,
                        "bbox": {
                            "x": data['left'][i],
                            "y": data['top'][i],
                            "width": data['width'][i],
                            "height": data['height'][i],
                        },
                    })
        
        full_text = " ".join(texts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "text": full_text,
            "confidence": avg_confidence,
            "boxes": boxes,
        }
    
    def _merge_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge results from multiple OCR engines."""
        if not results:
            return {"text": "", "confidence": 0, "boxes": []}
        
        if len(results) == 1:
            return results[0]
        
        # Use result with highest confidence
        best = max(results, key=lambda r: r["confidence"])
        
        # Combine unique text segments
        all_texts = [r["text"] for r in results]
        combined_text = self._smart_merge_texts(all_texts)
        
        return {
            "text": combined_text,
            "confidence": best["confidence"],
            "boxes": best["boxes"],
        }
    
    def _smart_merge_texts(self, texts: List[str]) -> str:
        """Intelligently merge text from multiple sources."""
        if not texts:
            return ""
        
        # Use longest text as base
        base = max(texts, key=len)
        return base
    
    def _detect_language(self, text: str) -> str:
        """Detect language of text."""
        # Simple heuristic
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        total_chars = len(text.strip())
        
        if total_chars == 0:
            return "unknown"
        
        if chinese_chars / total_chars > 0.3:
            return "zh"
        
        # Check for Malay keywords
        malay_keywords = ['dan', 'atau', 'yang', 'untuk', 'dari', 'pada', 'dengan']
        text_lower = text.lower()
        malay_count = sum(1 for word in malay_keywords if word in text_lower)
        
        if malay_count >= 2:
            return "ms"
        
        return "en"
    
    def extract_homework_fields(self, text: str) -> Dict[str, Any]:
        """Extract structured fields from OCR text."""
        lines = text.split('\n')
        
        result = {
            "subject": "",
            "title": "",
            "description": "",
            "due_date": None,
            "raw_text": text,
        }
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if not result["subject"] and len(line) < 50:
                result["subject"] = line
        
        return result



class AdvancedOCREngine:
    """Enhanced OCR engine with advanced Vision LLM support and ensemble methods."""
    
    def __init__(
        self,
        # Traditional OCR settings
        tesseract_cmd: str = "/usr/bin/tesseract",
        ocr_language: str = "eng+chi_sim+chi_tra+msa",
        use_easyocr: bool = True,
        use_tesseract: bool = True,
        gpu: bool = False,
        # Vision API keys
        together_api_key: Optional[str] = None,
        together_model: str = "meta-llama/Llama-4-Scout-17B-16E-Instruct",
        gemini_api_key: Optional[str] = None,
        gemini_model: str = "gemini-1.5-flash",
        deepseek_api_key: Optional[str] = None,
        # Mode settings
        preferred_mode: str = "auto",  # auto, ensemble, vision, traditional
        enable_ensemble: bool = True,
    ):
        self.preferred_mode = preferred_mode
        self.enable_ensemble = enable_ensemble
        
        # Initialize traditional OCR for fallback
        self.traditional = None
        if use_easyocr or use_tesseract:
            try:
                self.traditional = OCREngine(
                    tesseract_cmd=tesseract_cmd,
                    ocr_language=ocr_language,
                    use_easyocr=use_easyocr,
                    use_tesseract=use_tesseract,
                    gpu=gpu,
                    preferred_engine="easyocr" if use_easyocr else "tesseract",
                )
            except Exception as e:
                logger.warning(f"Failed to initialize traditional OCR: {e}")
        
        # Initialize advanced vision OCR
        self.vision_ocr = None
        if HAS_ADVANCED_VISION:
            try:
                self.vision_ocr = AdvancedVisionOCR(
                    together_api_key=together_api_key,
                    gemini_api_key=gemini_api_key,
                    preferred_mode="ensemble" if enable_ensemble else "together",
                )
                logger.info("Advanced Vision OCR initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize advanced vision OCR: {e}")
        
        # Initialize legacy vision engines as backup
        self._init_legacy_vision(
            together_api_key=together_api_key,
            together_model=together_model,
            gemini_api_key=gemini_api_key,
            gemini_model=gemini_model,
            deepseek_api_key=deepseek_api_key,
        )
    
    def _init_legacy_vision(self, **kwargs):
        """Initialize legacy vision engines as fallback."""
        self._together_ocr = None
        self._gemini_ocr = None
        self._deepseek_ocr = None
        
        if kwargs.get("together_api_key"):
            try:
                self._together_ocr = TogetherAIOCR(
                    api_key=kwargs["together_api_key"],
                    model=kwargs.get("together_model", "meta-llama/Llama-4-Scout-17B-16E-Instruct"),
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Together AI: {e}")
        
        if kwargs.get("gemini_api_key"):
            try:
                self._gemini_ocr = GeminiOCR(
                    api_key=kwargs["gemini_api_key"],
                    model=kwargs.get("gemini_model", "gemini-1.5-flash"),
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")
        
        if kwargs.get("deepseek_api_key"):
            try:
                self._deepseek_ocr = DeepSeekOCR(
                    api_key=kwargs["deepseek_api_key"],
                    model="deepseek-chat",
                )
            except Exception as e:
                logger.warning(f"Failed to initialize DeepSeek: {e}")
    
    async def process_image(
        self,
        image_path: str,
        preprocess: bool = True,
        language_hint: str = "en",
    ) -> OCResult:
        """Process image with best available OCR engine."""
        start_time = time.time()
        
        # Determine which mode to use
        mode = self._select_mode()
        
        try:
            if mode == "advanced_vision" and self.vision_ocr:
                return await self._process_advanced_vision(image_path, language_hint)
            elif mode == "legacy_vision":
                return await self._process_legacy_vision(image_path, language_hint)
            elif self.traditional:
                return await self.traditional.process_image(image_path, preprocess, language_hint)
            else:
                raise RuntimeError("No OCR engine available")
                
        except Exception as e:
            logger.error(f"Primary OCR failed ({mode}): {e}")
            return await self._fallback_ocr(image_path, preprocess, language_hint)
    
    def _select_mode(self) -> str:
        """Select best OCR mode based on availability."""
        if self.preferred_mode == "traditional":
            return "traditional"
        elif self.preferred_mode == "vision":
            return "advanced_vision" if self.vision_ocr else "legacy_vision"
        elif self.preferred_mode == "ensemble":
            return "advanced_vision" if self.vision_ocr else "legacy_vision"
        else:  # auto
            if self.vision_ocr:
                return "advanced_vision"
            elif self._together_ocr or self._gemini_ocr or self._deepseek_ocr:
                return "legacy_vision"
            elif self.traditional:
                return "traditional"
            return "none"
    
    async def _process_advanced_vision(
        self,
        image_path: str,
        language_hint: str
    ) -> OCResult:
        """Process using advanced vision OCR."""
        result = await self.vision_ocr.process(image_path, language_hint)
        
        # Convert VisionOCRResult to OCResult
        return OCResult(
            text=result.text,
            confidence=result.confidence,
            language=language_hint,
            bounding_boxes=[],  # Vision APIs don't provide bounding boxes
            processing_time_ms=result.processing_time_ms,
        )
    
    async def _process_legacy_vision(
        self,
        image_path: str,
        language_hint: str
    ) -> OCResult:
        """Process using legacy vision OCR engines."""
        engines = []
        if self._together_ocr:
            engines.append(("together", self._together_ocr.process_image))
        if self._gemini_ocr:
            engines.append(("gemini", self._gemini_ocr.process_image))
        if self._deepseek_ocr:
            engines.append(("deepseek", self._deepseek_ocr.process_image))
        
        if not engines:
            raise RuntimeError("No legacy vision engines available")
        
        # Try engines in order
        for name, processor in engines:
            try:
                logger.info(f"Trying legacy vision engine: {name}")
                return await processor(image_path, language_hint)
            except Exception as e:
                logger.warning(f"Engine {name} failed: {e}")
                continue
        
        raise RuntimeError("All legacy vision engines failed")
    
    async def _fallback_ocr(
        self,
        image_path: str,
        preprocess: bool,
        language_hint: str
    ) -> OCResult:
        """Fallback OCR with multiple retries."""
        # Try all available methods
        attempts = []
        
        if self.vision_ocr:
            attempts.append(("advanced_vision", self._process_advanced_vision))
        if self._together_ocr or self._gemini_ocr or self._deepseek_ocr:
            attempts.append(("legacy_vision", lambda p, l: self._process_legacy_vision(p, l)))
        if self.traditional:
            attempts.append(("traditional", lambda p, l: self.traditional.process_image(p, preprocess, l)))
        
        for name, processor in attempts:
            try:
                logger.info(f"Fallback trying: {name}")
                return await processor(image_path, language_hint)
            except Exception as e:
                logger.warning(f"Fallback {name} failed: {e}")
                continue
        
        raise RuntimeError("All OCR engines failed")
    
    async def extract_structured_homework(
        self,
        image_path: str,
        language_hint: str = "en",
    ) -> HomeworkExtraction:
        """Extract structured homework data from image."""
        # Use advanced vision for structured extraction
        if self.vision_ocr:
            try:
                result = await self.vision_ocr.process(image_path, language_hint)
                return result.structured
            except Exception as e:
                logger.warning(f"Advanced structured extraction failed: {e}")
        
        # Fallback: use traditional OCR + AI enhancement
        ocr_result = await self.process_image(image_path, language_hint=language_hint)
        
        # Try to parse structured data from raw text
        return self._parse_homework_from_text(ocr_result.text)
    
    def _parse_homework_from_text(self, text: str) -> HomeworkExtraction:
        """Parse homework structure from raw OCR text."""
        lines = text.split('\n')
        
        extraction = HomeworkExtraction(
            raw_text=text,
            confidence=0.6,
        )
        
        # Simple heuristics for extraction
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect subject
            subjects = ['math', 'mathematics', 'science', 'english', 'chinese', 
                       'malay', 'bahasa', 'history', 'geography', 'physics', 
                       'chemistry', 'biology']
            line_lower = line.lower()
            for subj in subjects:
                if subj in line_lower and len(line) < 50:
                    extraction.subject = line
                    break
            
            # Detect due date
            date_patterns = [
                r'due\s*:?\s*(.+?)(?:\n|$)',
                r'submit\s*:?\s*(.+?)(?:\n|$)',
                r'deadline\s*:?\s*(.+?)(?:\n|$)',
                r'by\s+(.+?)(?:\n|$)',
            ]
            for pattern in date_patterns:
                match = re.search(pattern, line_lower)
                if match:
                    extraction.due_date = match.group(1).strip()
                    break
        
        # Use first substantial line as title
        for line in lines:
            if len(line.strip()) > 5 and len(line.strip()) < 100:
                extraction.title = line.strip()
                break
        
        extraction.description = text
        return extraction


# Factory function for creating the best available OCR engine
async def create_best_ocr_engine(
    together_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    deepseek_api_key: Optional[str] = None,
    preferred_mode: str = "auto",
) -> AdvancedOCREngine:
    """Create the best available OCR engine with given API keys."""
    engine = AdvancedOCREngine(
        together_api_key=together_api_key,
        gemini_api_key=gemini_api_key,
        deepseek_api_key=deepseek_api_key,
        preferred_mode=preferred_mode,
        enable_ensemble=True,
    )
    return engine
