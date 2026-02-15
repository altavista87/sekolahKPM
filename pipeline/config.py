"""Pipeline configuration."""

from dataclasses import dataclass
from typing import List, Tuple
import os


@dataclass
class PipelineConfig:
    """Pipeline configuration."""
    
    # OCR Settings
    ocr_engine: str = "hybrid"  # easyocr, tesseract, hybrid
    ocr_languages: List[str] = None
    tesseract_cmd: str = "/usr/bin/tesseract"
    easyocr_gpu: bool = False
    
    # Image Processing
    max_image_size: Tuple[int, int] = (4096, 4096)
    preprocess_enabled: bool = True
    denoise_strength: int = 10
    contrast_enhancement: bool = True
    deskew_enabled: bool = True
    
    # AI Processing
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 2000
    ai_temperature: float = 0.7
    ai_timeout: int = 30
    
    # Validation
    min_confidence: float = 0.6
    require_due_date: bool = False
    max_description_length: int = 5000
    
    # Batch Processing
    batch_size: int = 10
    batch_timeout: int = 300
    parallel_workers: int = 4
    
    # Storage
    temp_dir: str = "./tmp"
    output_dir: str = "./output"
    keep_raw_images: bool = False
    
    @classmethod
    def from_env(cls) -> "PipelineConfig":
        """Load from environment."""
        langs = os.getenv("OCR_LANGUAGES", "eng,chi_sim,chi_tra,msa")
        return cls(
            ocr_engine=os.getenv("OCR_ENGINE", "hybrid"),
            ocr_languages=langs.split(","),
            tesseract_cmd=os.getenv("TESSERACT_CMD", "/usr/bin/tesseract"),
            easyocr_gpu=os.getenv("EASYOCR_GPU", "false").lower() == "true",
            preprocess_enabled=os.getenv("PREPROCESS_ENABLED", "true").lower() == "true",
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4"),
            parallel_workers=int(os.getenv("PIPELINE_WORKERS", "4")),
        )
