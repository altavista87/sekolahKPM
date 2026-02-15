"""Batch processing for multiple homework submissions."""

import asyncio
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor

from .ocr import OCRPipeline, OCRResult
from .ai_processor import PipelineAIProcessor, ExtractionResult
from .validator import DataValidator, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class BatchItem:
    """Single item in batch."""
    id: str
    image_path: str
    user_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    ocr_result: Optional[OCRResult] = None
    extraction: Optional[ExtractionResult] = None
    validation: Optional[ValidationResult] = None
    status: str = "pending"  # pending, processing, completed, failed
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class BatchResult:
    """Batch processing result."""
    batch_id: str
    items: List[BatchItem]
    started_at: datetime
    completed_at: Optional[datetime] = None
    total: int = 0
    successful: int = 0
    failed: int = 0
    processing_time_ms: float = 0.0


class BatchProcessor:
    """Process multiple homework images in batch."""
    
    def __init__(
        self,
        ocr_pipeline: OCRPipeline,
        ai_processor: Optional[PipelineAIProcessor] = None,
        validator: Optional[DataValidator] = None,
        max_workers: int = 4,
    ):
        self.ocr = ocr_pipeline
        self.ai = ai_processor
        self.validator = validator or DataValidator()
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def process_batch(
        self,
        items: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> BatchResult:
        """Process batch of homework images."""
        import uuid
        import time
        
        start_time = time.time()
        batch_id = str(uuid.uuid4())
        
        # Create batch items
        batch_items = [
            BatchItem(
                id=item.get("id") or str(uuid.uuid4()),
                image_path=item["image_path"],
                user_id=item["user_id"],
                metadata=item.get("metadata", {}),
            )
            for item in items
        ]
        
        result = BatchResult(
            batch_id=batch_id,
            items=batch_items,
            started_at=datetime.utcnow(),
            total=len(batch_items),
        )
        
        # Process items with semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def process_with_limit(item: BatchItem):
            async with semaphore:
                await self._process_item(item)
                if progress_callback:
                    completed = sum(1 for i in batch_items if i.status != "pending")
                    progress_callback(completed, len(batch_items))
        
        # Process all items
        tasks = [process_with_limit(item) for item in batch_items]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculate results
        result.successful = sum(1 for item in batch_items if item.status == "completed")
        result.failed = sum(1 for item in batch_items if item.status == "failed")
        result.completed_at = datetime.utcnow()
        result.processing_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"Batch {batch_id} complete: {result.successful}/{result.total} successful"
        )
        
        return result
    
    async def _process_item(self, item: BatchItem):
        """Process single batch item."""
        item.status = "processing"
        item.started_at = datetime.utcnow()
        
        try:
            # OCR
            item.ocr_result = await self.ocr.process(item.image_path)
            
            # AI extraction
            if self.ai:
                item.extraction = await self.ai.extract_homework(
                    item.ocr_result.text,
                    context=item.metadata,
                )
                
                # Validation
                extraction_dict = {
                    "subject": item.extraction.subject,
                    "title": item.extraction.title,
                    "description": item.extraction.description,
                    "due_date": item.extraction.due_date,
                    "confidence": item.extraction.confidence,
                }
                item.validation = self.validator.validate(
                    extraction_dict,
                    item.ocr_result.text,
                )
            
            item.status = "completed"
            
        except Exception as e:
            logger.error(f"Failed to process item {item.id}: {e}")
            item.status = "failed"
            item.error = str(e)
        
        finally:
            item.completed_at = datetime.utcnow()
    
    def get_batch_summary(self, result: BatchResult) -> Dict[str, Any]:
        """Generate human-readable batch summary."""
        return {
            "batch_id": result.batch_id,
            "total_processed": result.total,
            "successful": result.successful,
            "failed": result.failed,
            "success_rate": f"{(result.successful / result.total * 100):.1f}%" if result.total > 0 else "N/A",
            "processing_time_sec": round(result.processing_time_ms / 1000, 2),
            "items_per_second": round(
                result.total / (result.processing_time_ms / 1000), 2
            ) if result.processing_time_ms > 0 else 0,
        }
    
    def retry_failed(
        self,
        result: BatchResult,
    ) -> List[BatchItem]:
        """Get failed items for retry."""
        return [item for item in result.items if item.status == "failed"]
