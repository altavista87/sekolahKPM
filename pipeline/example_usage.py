"""Example usage of the OCR + AI Pipeline."""

import asyncio
from pathlib import Path

from .config import PipelineConfig
from .ocr import OCRPipeline
from .ai_processor import PipelineAIProcessor
from .validator import DataValidator
from .image_manager import ImageManager
from .batch import BatchProcessor
from .curriculum import CurriculumMapper


async def single_image_example():
    """Example: Process a single homework image."""
    
    print("=" * 60)
    print("Example 1: Single Image Processing")
    print("=" * 60)
    
    # Initialize components
    config = PipelineConfig.from_env()
    ocr = OCRPipeline(config.__dict__)
    ai = PipelineAIProcessor(
        api_key="your-openai-api-key",
        model=config.openai_model,
    )
    validator = DataValidator(min_confidence=0.6)
    
    # Process image
    image_path = "./samples/homework_math.jpg"
    
    print(f"\nProcessing: {image_path}")
    print("-" * 40)
    
    # Step 1: OCR
    ocr_result = await ocr.process(image_path)
    print(f"OCR Text (first 200 chars):")
    print(f"  {ocr_result.text[:200]}...")
    print(f"  Confidence: {ocr_result.confidence:.2%}")
    print(f"  Engine: {ocr_result.engine}")
    print(f"  Processing time: {ocr_result.processing_time_ms:.0f}ms")
    
    # Step 2: AI Extraction
    extraction = await ai.extract_homework(ocr_result.text)
    print(f"\nExtracted Information:")
    print(f"  Subject: {extraction.subject}")
    print(f"  Title: {extraction.title}")
    print(f"  Due Date: {extraction.due_date}")
    print(f"  Priority: {extraction.priority}")
    print(f"  Estimated Time: {extraction.estimated_time_minutes} minutes")
    print(f"  Keywords: {', '.join(extraction.keywords)}")
    
    # Step 3: Validation
    extraction_dict = {
        "subject": extraction.subject,
        "title": extraction.title,
        "description": extraction.description,
        "due_date": extraction.due_date,
        "confidence": extraction.confidence,
    }
    validation = validator.validate(extraction_dict, ocr_result.text)
    
    print(f"\nValidation Result:")
    print(f"  Valid: {validation.valid}")
    print(f"  Confidence Score: {validation.confidence_score:.2%}")
    
    if validation.issues:
        print(f"  Issues:")
        for issue in validation.issues:
            print(f"    - {issue.field}: {issue.message} ({issue.severity})")
    
    if validation.suggestions:
        print(f"  Suggestions:")
        for suggestion in validation.suggestions:
            print(f"    - {suggestion}")


async def batch_processing_example():
    """Example: Batch process multiple images."""
    
    print("\n" + "=" * 60)
    print("Example 2: Batch Processing")
    print("=" * 60)
    
    # Initialize components
    config = PipelineConfig.from_env()
    ocr = OCRPipeline(config.__dict__)
    ai = PipelineAIProcessor(api_key="your-openai-api-key")
    
    batch_processor = BatchProcessor(
        ocr_pipeline=ocr,
        ai_processor=ai,
        max_workers=4,
    )
    
    # Prepare batch items
    items = [
        {"image_path": "./samples/hw1.jpg", "user_id": "user_001"},
        {"image_path": "./samples/hw2.jpg", "user_id": "user_001"},
        {"image_path": "./samples/hw3.jpg", "user_id": "user_002"},
    ]
    
    print(f"\nProcessing {len(items)} images...")
    print("-" * 40)
    
    # Progress callback
    def on_progress(current, total):
        print(f"  Progress: {current}/{total} ({current/total*100:.0f}%)")
    
    # Process batch
    result = await batch_processor.process_batch(items, on_progress)
    
    # Print summary
    summary = batch_processor.get_batch_summary(result)
    print(f"\nBatch Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # Print individual results
    print(f"\nIndividual Results:")
    for item in result.items:
        status_icon = "✅" if item.status == "completed" else "❌"
        print(f"  {status_icon} {item.id}: {item.status}")
        if item.extraction:
            print(f"      Subject: {item.extraction.subject}")
            print(f"      Title: {item.extraction.title}")


async def curriculum_mapping_example():
    """Example: Curriculum mapping."""
    
    print("\n" + "=" * 60)
    print("Example 3: Curriculum Mapping")
    print("=" * 60)
    
    mapper = CurriculumMapper()
    
    # Example homework
    homework = {
        "subject": "mathematics",
        "title": "Multiplication Practice",
        "description": "Complete exercises on multiplying 2-digit numbers",
        "keywords": ["multiply", "times", "2-digit", "calculation"],
    }
    
    print(f"\nMapping homework to curriculum...")
    print(f"  Subject: {homework['subject']}")
    print(f"  Title: {homework['title']}")
    print("-" * 40)
    
    # Map to curriculum
    matches = mapper.map_homework(
        homework["subject"],
        homework["title"],
        homework["description"],
        homework["keywords"],
    )
    
    print(f"\nMatched Topics ({len(matches)} found):")
    for i, match in enumerate(matches[:3], 1):
        print(f"\n  {i}. {match['topic_name']}")
        print(f"     Grade: {match['grade']}")
        print(f"     Match Score: {match['match_score']:.2%}")
        print(f"     Learning Objectives:")
        for obj in match['learning_objectives'][:2]:
            print(f"       - {obj}")
    
    # Get related topics
    if matches:
        related = mapper.suggest_related_topics(matches[0]['topic_id'])
        print(f"\nRelated Topics:")
        for topic in related:
            print(f"  - {topic['name']} ({topic['grade']})")


async def image_management_example():
    """Example: Image management."""
    
    print("\n" + "=" * 60)
    print("Example 4: Image Management")
    print("=" * 60)
    
    # Initialize image manager
    manager = ImageManager(
        upload_dir="./uploads",
        temp_dir="./tmp",
    )
    
    # Simulate file upload
    print(f"\nSimulating file upload...")
    print("-" * 40)
    
    # In real usage, this would be actual file data
    sample_data = b"fake image data" * 100
    
    try:
        result = manager.save_upload(
            file_data=sample_data,
            original_filename="homework.jpg",
            user_id="user_001",
        )
        
        print(f"File saved:")
        for key, value in result.items():
            print(f"  {key}: {value}")
        
        # Create thumbnail
        thumbnail = manager.create_thumbnail(result['filepath'], size=(200, 200))
        print(f"\nThumbnail created: {thumbnail}")
        
        # Get storage stats
        stats = manager.get_storage_stats()
        print(f"\nStorage Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    except ValueError as e:
        print(f"Upload error: {e}")


async def main():
    """Run all examples."""
    
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "EduSync Pipeline Examples" + " " * 16 + "║")
    print("╚" + "═" * 58 + "╝")
    
    # Run examples
    # await single_image_example()
    # await batch_processing_example()
    # await curriculum_mapping_example()
    # await image_management_example()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
