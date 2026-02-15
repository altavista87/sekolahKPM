"""OCR Pipeline for image processing."""

import cv2
import numpy as np
from PIL import Image, ImageEnhance
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging
import time

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """OCR result container."""
    text: str
    confidence: float
    language: str
    bounding_boxes: List[Dict[str, Any]]
    processing_time_ms: float
    engine: str


class ImagePreprocessor:
    """Image preprocessing for better OCR."""
    
    def __init__(
        self,
        denoise_strength: int = 10,
        contrast_enhancement: bool = True,
        deskew_enabled: bool = True,
    ):
        self.denoise_strength = denoise_strength
        self.contrast_enhancement = contrast_enhancement
        self.deskew_enabled = deskew_enabled
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """Apply full preprocessing pipeline."""
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Denoise
        gray = self._denoise(gray)
        
        # Enhance contrast
        if self.contrast_enhancement:
            gray = self._enhance_contrast(gray)
        
        # Deskew
        if self.deskew_enabled:
            gray = self._deskew(gray)
        
        # Binarization
        binary = self._binarize(gray)
        
        return binary
    
    def _denoise(self, image: np.ndarray) -> np.ndarray:
        """Apply denoising."""
        return cv2.fastNlMeansDenoising(
            image, None, self.denoise_strength, 7, 21
        )
    
    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance image contrast."""
        pil_img = Image.fromarray(image)
        enhancer = ImageEnhance.Contrast(pil_img)
        enhanced = enhancer.enhance(1.5)
        return np.array(enhanced)
    
    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """Correct image skew."""
        # Detect skew angle
        coords = np.column_stack(np.where(image > 0))
        
        if len(coords) < 100:
            return image
        
        angle = cv2.minAreaRect(coords)[-1]
        
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        # Rotate if angle is significant
        if abs(angle) > 0.5:
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                image, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )
            return rotated
        
        return image
    
    def _binarize(self, image: np.ndarray) -> np.ndarray:
        """Apply adaptive thresholding."""
        return cv2.adaptiveThreshold(
            image, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )
    
    def resize_if_needed(
        self,
        image: np.ndarray,
        max_size: Tuple[int, int] = (4096, 4096),
    ) -> np.ndarray:
        """Resize image if too large."""
        h, w = image.shape[:2]
        max_w, max_h = max_size
        
        if w > max_w or h > max_h:
            scale = min(max_w / w, max_h / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        return image


class OCRPipeline:
    """Main OCR processing pipeline."""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.preprocessor = ImagePreprocessor()
        self._easyocr = None
        self._tesseract = None
        self._init_engines()
    
    def _init_engines(self):
        """Initialize OCR engines."""
        # EasyOCR
        try:
            import easyocr
            self._easyocr = easyocr.Reader(
                ['en', 'ch_sim', 'ch_tra', 'ms'],
                gpu=self.config.get('easyocr_gpu', False),
                verbose=False,
            )
            logger.info("EasyOCR initialized")
        except Exception as e:
            logger.warning(f"EasyOCR not available: {e}")
        
        # Tesseract
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self._tesseract = pytesseract
            logger.info("Tesseract available")
        except Exception as e:
            logger.warning(f"Tesseract not available: {e}")
    
    async def process(
        self,
        image_path: str,
        preprocess: bool = True,
    ) -> OCRResult:
        """Process image through OCR pipeline."""
        start_time = time.time()
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")
        
        # Preprocess
        if preprocess:
            image = self.preprocessor.preprocess(image)
        
        # Run OCR
        results = []
        
        if self._easyocr and self.config.get('ocr_engine') in ('easyocr', 'hybrid'):
            try:
                result = self._run_easyocr(image)
                results.append(('easyocr', result))
            except Exception as e:
                logger.error(f"EasyOCR failed: {e}")
        
        if self._tesseract and self.config.get('ocr_engine') in ('tesseract', 'hybrid'):
            try:
                result = self._run_tesseract(image)
                results.append(('tesseract', result))
            except Exception as e:
                logger.error(f"Tesseract failed: {e}")
        
        # Merge or select best result
        if not results:
            raise RuntimeError("No OCR engine available")
        
        if len(results) == 1:
            engine, result = results[0]
        else:
            # Merge results
            engine, result = self._merge_results(results)
        
        processing_time = (time.time() - start_time) * 1000
        
        return OCRResult(
            text=result['text'],
            confidence=result['confidence'],
            language=result.get('language', 'unknown'),
            bounding_boxes=result.get('boxes', []),
            processing_time_ms=processing_time,
            engine=engine,
        )
    
    def _run_easyocr(self, image: np.ndarray) -> Dict:
        """Run EasyOCR."""
        results = self._easyocr.readtext(image)
        
        texts = []
        confidences = []
        boxes = []
        
        for bbox, text, conf in results:
            texts.append(text)
            confidences.append(conf)
            boxes.append({'text': text, 'confidence': conf, 'bbox': bbox})
        
        return {
            'text': '\n'.join(texts),
            'confidence': sum(confidences) / len(confidences) if confidences else 0,
            'boxes': boxes,
            'language': 'mixed',
        }
    
    def _run_tesseract(self, image: np.ndarray) -> Dict:
        """Run Tesseract OCR."""
        lang = self.config.get('ocr_languages', ['eng'])
        lang_str = '+'.join(lang)
        
        data = self._tesseract.image_to_data(
            image,
            lang=lang_str,
            config='--oem 3 --psm 6',
            output_type=self._tesseract.Output.DICT,
        )
        
        texts = []
        confidences = []
        boxes = []
        
        for i in range(len(data['text'])):
            if int(data['conf'][i]) > 30:
                text = data['text'][i].strip()
                if text:
                    texts.append(text)
                    confidences.append(int(data['conf'][i]) / 100)
                    boxes.append({
                        'text': text,
                        'confidence': int(data['conf'][i]) / 100,
                        'bbox': {
                            'x': data['left'][i],
                            'y': data['top'][i],
                            'w': data['width'][i],
                            'h': data['height'][i],
                        },
                    })
        
        return {
            'text': ' '.join(texts),
            'confidence': sum(confidences) / len(confidences) if confidences else 0,
            'boxes': boxes,
            'language': lang_str,
        }
    
    def _merge_results(
        self,
        results: List[Tuple[str, Dict]],
    ) -> Tuple[str, Dict]:
        """Merge results from multiple engines."""
        # Simple strategy: use best confidence
        best_engine, best_result = max(results, key=lambda x: x[1]['confidence'])
        
        # Alternative: combine unique texts
        all_texts = [r[1]['text'] for r in results]
        combined = self._combine_texts(all_texts)
        
        merged = {
            'text': combined,
            'confidence': best_result['confidence'],
            'boxes': best_result['boxes'],
            'language': best_result.get('language', 'mixed'),
        }
        
        return f"hybrid:{best_engine}", merged
    
    def _combine_texts(self, texts: List[str]) -> str:
        """Intelligently combine texts from multiple sources."""
        if not texts:
            return ""
        
        # For now, return longest text (most complete)
        return max(texts, key=len)
