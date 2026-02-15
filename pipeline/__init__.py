"""
EduSync OCR + AI Pipeline Module

Provides image processing, OCR extraction, and AI enhancement capabilities.
"""

__version__ = "1.0.0"

from .ocr import OCRPipeline, ImagePreprocessor
from .ai_processor import PipelineAIProcessor
from .validator import DataValidator, ValidationResult
from .image_manager import ImageManager
from .batch import BatchProcessor
from .curriculum import CurriculumMapper

__all__ = [
    "OCRPipeline",
    "ImagePreprocessor",
    "PipelineAIProcessor",
    "DataValidator",
    "ValidationResult",
    "ImageManager",
    "BatchProcessor",
    "CurriculumMapper",
]
