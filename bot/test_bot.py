"""Tests for Telegram Bot module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from bot.models import User, Homework, UserRole, HomeworkStatus
from bot.utils import parse_date, format_date, sanitize_filename
from bot.ocr_engine import OCREngine, OCResult
from bot.ai_processor import AIProcessor, AIExtractionResult


class TestModels:
    """Test model classes."""
    
    def test_user_creation(self):
        """Test user model creation."""
        user = User(
            telegram_id=123456,
            name="Test User",
            role=UserRole.PARENT,
        )
        assert user.telegram_id == 123456
        assert user.name == "Test User"
        assert user.role == UserRole.PARENT
    
    def test_homework_overdue(self):
        """Test homework overdue detection."""
        from datetime import timedelta
        
        # Overdue homework
        overdue = Homework(
            due_date=datetime.utcnow() - timedelta(days=1),
            status=HomeworkStatus.PENDING,
        )
        assert overdue.is_overdue() is True
        
        # Not overdue
        future = Homework(
            due_date=datetime.utcnow() + timedelta(days=1),
            status=HomeworkStatus.PENDING,
        )
        assert future.is_overdue() is False
        
        # Completed homework
        completed = Homework(
            due_date=datetime.utcnow() - timedelta(days=1),
            status=HomeworkStatus.COMPLETED,
        )
        assert completed.is_overdue() is False


class TestUtils:
    """Test utility functions."""
    
    def test_parse_date_tomorrow(self):
        """Test parsing 'tomorrow'."""
        result = parse_date("submit homework tomorrow")
        assert result is not None
        from datetime import timedelta
        expected = datetime.now().date() + timedelta(days=1)
        assert result.date() == expected
    
    def test_parse_date_numeric(self):
        """Test parsing numeric date."""
        result = parse_date("due on 25/12/2024")
        assert result is not None
        assert result.day == 25
        assert result.month == 12
        assert result.year == 2024
    
    def test_format_date(self):
        """Test date formatting."""
        dt = datetime(2024, 12, 25, 10, 30)
        
        en_result = format_date(dt, "en")
        assert "25" in en_result
        assert "December" in en_result
        
        zh_result = format_date(dt, "zh")
        assert "2024年" in zh_result
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        assert sanitize_filename("test/file.jpg") == "file.jpg"
        assert sanitize_filename("test<file>.jpg") == "test_file_.jpg"
        assert sanitize_filename("a" * 200 + ".jpg") == "a" * 96 + ".jpg"


class TestOCREngine:
    """Test OCR Engine."""
    
    @pytest.fixture
    def ocr_engine(self):
        """Create OCR engine fixture."""
        return OCREngine(
            use_easyocr=False,  # Skip for tests
            use_tesseract=False,
        )
    
    def test_ocr_initialization(self, ocr_engine):
        """Test OCR engine initialization."""
        assert ocr_engine is not None
        assert ocr_engine.ocr_language == "eng+chi_sim+chi_tra+msa"
    
    def test_detect_language(self, ocr_engine):
        """Test language detection."""
        assert ocr_engine._detect_language("Hello world") == "en"
        assert ocr_engine._detect_language("你好世界") == "zh"
        assert ocr_engine._detect_language("Halo dunia") == "ms"
    
    def test_merge_results(self, ocr_engine):
        """Test result merging."""
        results = [
            {"text": "Hello", "confidence": 0.9, "boxes": []},
            {"text": "World", "confidence": 0.8, "boxes": []},
        ]
        merged = ocr_engine._merge_results(results)
        assert "confidence" in merged
        assert merged["confidence"] == 0.9  # Best confidence


class TestAIProcessor:
    """Test AI Processor."""
    
    @pytest.fixture
    def ai_processor(self):
        """Create AI processor fixture."""
        return AIProcessor(
            api_key="test-key",
            model="gpt-4",
        )
    
    def test_system_prompts(self, ai_processor):
        """Test system prompt generation."""
        en_prompt = ai_processor._get_system_prompt("en")
        assert "Extract" in en_prompt
        
        zh_prompt = ai_processor._get_system_prompt("zh")
        assert "提取" in zh_prompt
        
        ms_prompt = ai_processor._get_system_prompt("ms")
        assert "Ekstrak" in ms_prompt
    
    def test_fallback_result(self, ai_processor):
        """Test fallback result generation."""
        ocr_text = "Sample homework text"
        result = ai_processor._fallback_result(ocr_text)
        
        assert isinstance(result, AIExtractionResult)
        assert result.description == ocr_text[:500]
        assert result.confidence == 0.5
    
    def test_validate_homework_data(self, ai_processor):
        """Test homework data validation."""
        # Valid result
        valid_result = AIExtractionResult(
            subject="Math",
            title="Algebra",
            description="Solve equations",
            due_date="2024-12-25",
            priority=3,
            keywords=["algebra"],
            estimated_time_minutes=30,
            materials_needed=["calculator"],
            confidence=0.9,
            raw_response={},
        )
        validation = ai_processor.validate_homework_data(valid_result)
        assert validation["valid"] is True
        assert len(validation["issues"]) == 0
        
        # Invalid result
        invalid_result = AIExtractionResult(
            subject="",
            title="",
            description="",
            due_date=None,
            priority=3,
            keywords=[],
            estimated_time_minutes=None,
            materials_needed=[],
            confidence=0.4,
            raw_response={},
        )
        validation = ai_processor.validate_homework_data(invalid_result)
        assert validation["valid"] is False
        assert len(validation["issues"]) > 0


class TestHandlers:
    """Test bot handlers."""
    
    @pytest.fixture
    def mock_update(self):
        """Create mock update."""
        update = Mock()
        update.effective_user.id = 123456
        update.effective_user.first_name = "Test"
        update.effective_message = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create mock context."""
        context = Mock()
        context.user_data = {}
        return context
    
    @pytest.mark.asyncio
    async def test_help_command(self, mock_update, mock_context):
        """Test help command."""
        from bot.handlers import ParentHandler
        from bot.ocr_engine import OCREngine
        
        handler = ParentHandler(OCREngine(use_easyocr=False, use_tesseract=False))
        
        # Mock send_message
        handler.send_message = AsyncMock()
        
        # Call help command (need to access via parent handler or create instance)
        # This is a simplified test - real tests would need more setup
        assert handler is not None


class TestIntegration:
    """Integration tests."""
    
    @pytest.mark.integration
    def test_full_homework_flow(self):
        """Test complete homework submission flow."""
        # This would test the full flow from photo to saved homework
        pass
    
    @pytest.mark.integration
    def test_reminder_scheduling(self):
        """Test reminder scheduling."""
        # This would test reminder creation and triggering
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
