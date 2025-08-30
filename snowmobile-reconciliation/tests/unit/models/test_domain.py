"""
Unit tests for domain models following Universal Development Standards.

Tests all Pydantic models for validation, serialization, and business logic.
Achieves >80% test coverage requirement.
"""
import json
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.models.domain import (
    AuditTrail,
    BaseModelSpecification,
    ClaudeConfig,
    ConfidenceLevel,
    PipelineConfig,
    PipelineStageResult,
    PriceEntry,
    ProcessingError,
    ProcessingRequest,
    ProcessingStage,
    ProductSpecification,
    SpringOption,
    SpringOptionType,
)


class TestPriceEntry:
    """Test PriceEntry model validation and serialization"""

    def test_valid_price_entry(self):
        """Test creating valid price entry"""
        price_entry = PriceEntry(
            model_code="LTTA",
            brand="Ski-Doo",
            price=Decimal("25000.00"),
            model_year=2024,
            source_file="price_list_2024.pdf",
            page_number=1,
            extraction_confidence=0.95,
        )

        assert price_entry.model_code == "LTTA"
        assert price_entry.brand == "Ski-Doo"
        assert price_entry.price == Decimal("25000.00")
        assert price_entry.currency == "EUR"  # Default
        assert price_entry.market == "FI"  # Default

    def test_price_entry_validation(self):
        """Test price entry field validation"""
        # Test negative price validation
        with pytest.raises(ValidationError) as exc_info:
            PriceEntry(
                model_code="LTTA",
                brand="Ski-Doo",
                price=Decimal("-1000.00"),  # Invalid negative price
                model_year=2024,
                source_file="test.pdf",
                page_number=1,
                extraction_confidence=0.95,
            )

        assert "Input should be greater than or equal to 0" in str(exc_info.value)

    def test_price_entry_year_validation(self):
        """Test model year validation"""
        # Test invalid model year (too early)
        with pytest.raises(ValidationError):
            PriceEntry(
                model_code="LTTA",
                brand="Ski-Doo",
                price=Decimal("25000.00"),
                model_year=2019,  # Too early
                source_file="test.pdf",
                page_number=1,
                extraction_confidence=0.95,
            )

        # Test invalid model year (too late)
        with pytest.raises(ValidationError):
            PriceEntry(
                model_code="LTTA",
                brand="Ski-Doo",
                price=Decimal("25000.00"),
                model_year=2031,  # Too late
                source_file="test.pdf",
                page_number=1,
                extraction_confidence=0.95,
            )

    def test_price_entry_serialization(self):
        """Test price entry JSON serialization"""
        price_entry = PriceEntry(
            model_code="LTTA",
            brand="Ski-Doo",
            price=Decimal("25000.00"),
            model_year=2024,
            source_file="test.pdf",
            page_number=1,
            extraction_confidence=0.95,
        )

        # Test dict serialization
        data = price_entry.model_dump()
        assert data["model_code"] == "LTTA"
        assert data["price"] == Decimal("25000.00")

        # Test JSON serialization
        json_str = price_entry.model_dump_json()
        parsed_data = json.loads(json_str)
        assert parsed_data["model_code"] == "LTTA"
        assert float(parsed_data["price"]) == 25000.0


class TestBaseModelSpecification:
    """Test BaseModelSpecification model"""

    def test_valid_base_model(self):
        """Test creating valid base model specification"""
        base_model = BaseModelSpecification(
            base_model_id="MXZ_TRAIL_600",
            model_name="MXZ Trail 600 EFI",
            brand="Ski-Doo",
            model_year=2024,
            category="Trail",
            engine_specs={
                "displacement": "600cc",
                "type": "2-stroke",
                "fuel_injection": "EFI",
            },
            source_catalog="ski_doo_2024_catalog.pdf",
            extraction_quality=0.92,
        )

        assert base_model.base_model_id == "MXZ_TRAIL_600"
        assert base_model.brand == "Ski-Doo"
        assert base_model.engine_specs["displacement"] == "600cc"

    def test_base_model_id_validation(self):
        """Test base model ID validation"""
        # Test empty base model ID
        with pytest.raises(ValidationError) as exc_info:
            BaseModelSpecification(
                base_model_id="",  # Empty
                model_name="Test Model",
                brand="Ski-Doo",
                model_year=2024,
                category="Trail",
                source_catalog="test.pdf",
                extraction_quality=0.9,
            )

        assert "Base model ID must be at least 2 characters" in str(exc_info.value)

    def test_base_model_id_normalization(self):
        """Test base model ID gets normalized to uppercase"""
        base_model = BaseModelSpecification(
            base_model_id="mxz_trail_600",  # Lowercase
            model_name="MXZ Trail 600",
            brand="Ski-Doo",
            model_year=2024,
            category="Trail",
            source_catalog="test.pdf",
            extraction_quality=0.9,
        )

        assert base_model.base_model_id == "MXZ_TRAIL_600"  # Should be uppercase


class TestSpringOption:
    """Test SpringOption model"""

    def test_valid_spring_option(self):
        """Test creating valid spring option"""
        spring_option = SpringOption(
            option_type=SpringOptionType.TRACK_UPGRADE,
            description="137x15x1.25 Cobra track upgrade",
            technical_details={
                "track_length": "137",
                "track_width": "15",
                "lug_height": "1.25",
                "pattern": "Cobra",
            },
            confidence=0.85,
            detection_method="specification_comparison",
        )

        assert spring_option.option_type == SpringOptionType.TRACK_UPGRADE
        assert spring_option.confidence == 0.85
        assert "Cobra" in spring_option.description

    def test_spring_option_confidence_validation(self):
        """Test confidence score validation"""
        # Test valid confidence
        spring_option = SpringOption(
            option_type=SpringOptionType.COLOR_CHANGE,
            description="Color change to Red",
            confidence=0.75,
            detection_method="model_code_analysis",
        )
        assert spring_option.confidence == 0.75

        # Test confidence clamping (values outside 0-1 should be clamped)
        with pytest.raises(ValidationError):
            SpringOption(
                option_type=SpringOptionType.COLOR_CHANGE,
                description="Color change",
                confidence=1.5,  # Invalid - too high
                detection_method="test",
            )


class TestProductSpecification:
    """Test ProductSpecification model"""

    def test_valid_product_specification(self):
        """Test creating complete product specification"""
        product = ProductSpecification(
            model_code="LTTA",
            base_model_id="MXZ_TRAIL_600",
            brand="Ski-Doo",
            model_name="MXZ Trail 600 EFI",
            model_year=2024,
            price=Decimal("25000.00"),
            specifications={
                "engine": {"displacement": "600cc"},
                "track": {"length": "137", "width": "15"},
            },
            spring_options=[
                SpringOption(
                    option_type=SpringOptionType.TRACK_UPGRADE,
                    description="Track upgrade",
                    confidence=0.8,
                    detection_method="specification_comparison",
                )
            ],
            overall_confidence=0.85,
        )

        assert product.model_code == "LTTA"
        assert product.overall_confidence == 0.85
        assert len(product.spring_options) == 1
        assert product.confidence_level == ConfidenceLevel.MEDIUM  # 0.7-0.89

    def test_confidence_level_auto_calculation(self):
        """Test automatic confidence level calculation"""
        # Test HIGH confidence
        product_high = ProductSpecification(
            model_code="TEST",
            base_model_id="TEST_MODEL",
            brand="Test",
            model_name="Test Model",
            model_year=2024,
            price=Decimal("1000.00"),
            overall_confidence=0.95,  # Should be HIGH
        )
        assert product_high.confidence_level == ConfidenceLevel.HIGH

        # Test MEDIUM confidence
        product_medium = ProductSpecification(
            model_code="TEST",
            base_model_id="TEST_MODEL",
            brand="Test",
            model_name="Test Model",
            model_year=2024,
            price=Decimal("1000.00"),
            overall_confidence=0.75,  # Should be MEDIUM
        )
        assert product_medium.confidence_level == ConfidenceLevel.MEDIUM

        # Test LOW confidence
        product_low = ProductSpecification(
            model_code="TEST",
            base_model_id="TEST_MODEL",
            brand="Test",
            model_name="Test Model",
            model_year=2024,
            price=Decimal("1000.00"),
            overall_confidence=0.5,  # Should be LOW
        )
        assert product_low.confidence_level == ConfidenceLevel.LOW


class TestPipelineStageResult:
    """Test PipelineStageResult model"""

    def test_valid_stage_result(self):
        """Test creating valid pipeline stage result"""
        stage_result = PipelineStageResult(
            stage=ProcessingStage.BASE_MODEL_MATCHING,
            success=True,
            confidence_score=0.88,
            processing_time_ms=150,
            stage_data={
                "matched_base_model": "MXZ_TRAIL_600",
                "matching_method": "structured",
            },
            warnings=["Minor formatting issue in model code"],
            claude_tokens_used=245,
            claude_api_cost=Decimal("0.0012"),
        )

        assert stage_result.stage == ProcessingStage.BASE_MODEL_MATCHING
        assert stage_result.success is True
        assert stage_result.confidence_score == 0.88
        assert stage_result.processing_time_ms == 150
        assert len(stage_result.warnings) == 1


class TestProcessingRequest:
    """Test ProcessingRequest model"""

    def test_valid_processing_request(self):
        """Test creating valid processing request"""
        price_entries = [
            PriceEntry(
                model_code="LTTA",
                brand="Ski-Doo",
                price=Decimal("25000.00"),
                model_year=2024,
                source_file="test.pdf",
                page_number=1,
                extraction_confidence=0.95,
            )
        ]

        request = ProcessingRequest(price_entries=price_entries, priority=7)

        assert len(request.price_entries) == 1
        assert request.priority == 7
        assert request.callback_url is None

    def test_processing_request_limits(self):
        """Test processing request validation limits"""
        # Test empty price entries
        with pytest.raises(ValidationError):
            ProcessingRequest(price_entries=[])  # Empty list

        # Test priority validation
        with pytest.raises(ValidationError):
            ProcessingRequest(
                price_entries=[
                    PriceEntry(
                        model_code="TEST",
                        brand="Test",
                        price=Decimal("1000.00"),
                        model_year=2024,
                        source_file="test.pdf",
                        page_number=1,
                        extraction_confidence=0.9,
                    )
                ],
                priority=11,  # Invalid - too high
            )


class TestProcessingError:
    """Test ProcessingError model"""

    def test_valid_processing_error(self):
        """Test creating valid processing error"""
        error = ProcessingError(
            error_type="validation_error",
            error_message="Invalid model code format",
            error_code="VAL_001",
            stage=ProcessingStage.BASE_MODEL_MATCHING,
            model_code="INVALID_CODE",
            technical_details={"attempted_patterns": ["LTTA", "MVTL"]},
            recovery_suggestion="Check model code format and try again",
            retry_recommended=True,
        )

        assert error.error_type == "validation_error"
        assert error.error_code == "VAL_001"
        assert error.retry_recommended is True
        assert isinstance(error.timestamp, datetime)


class TestClaudeConfig:
    """Test ClaudeConfig model validation"""

    def test_valid_claude_config(self):
        """Test creating valid Claude configuration"""
        config = ClaudeConfig(
            model="claude-3-haiku-20240307",
            max_tokens=4000,
            temperature=0.1,
            batch_size=5,
            timeout_seconds=30,
        )

        assert config.model == "claude-3-haiku-20240307"
        assert config.max_tokens == 4000
        assert config.temperature == 0.1

    def test_claude_config_validation(self):
        """Test Claude config field validation"""
        # Test invalid temperature
        with pytest.raises(ValidationError):
            ClaudeConfig(temperature=1.5)  # Too high

        # Test invalid batch size
        with pytest.raises(ValidationError):
            ClaudeConfig(batch_size=0)  # Too low


class TestPipelineConfig:
    """Test PipelineConfig model"""

    def test_valid_pipeline_config(self):
        """Test creating valid pipeline configuration"""
        config = PipelineConfig(
            auto_accept_threshold=0.9,
            manual_review_threshold=0.7,
            max_concurrent_processing=10,
            enable_spring_options=True,
            claude_config=ClaudeConfig(),
        )

        assert config.auto_accept_threshold == 0.9
        assert config.manual_review_threshold == 0.7
        assert config.enable_spring_options is True
        assert isinstance(config.claude_config, ClaudeConfig)

    def test_pipeline_config_defaults(self):
        """Test pipeline config default values"""
        config = PipelineConfig()

        assert config.auto_accept_threshold == 0.9
        assert config.manual_review_threshold == 0.7
        assert config.enable_spring_options is True
        assert config.enable_claude_fallback is True


# Integration tests for model interactions
class TestModelInteractions:
    """Test how models work together"""

    def test_product_with_complete_pipeline_results(self):
        """Test product with complete pipeline stage results"""
        stage_results = [
            PipelineStageResult(
                stage=ProcessingStage.BASE_MODEL_MATCHING,
                success=True,
                confidence_score=0.9,
                processing_time_ms=100,
                stage_data={"matched_model": "TEST_MODEL"},
            ),
            PipelineStageResult(
                stage=ProcessingStage.SPECIFICATION_INHERITANCE,
                success=True,
                confidence_score=0.85,
                processing_time_ms=150,
                stage_data={"inherited_specs": {"engine": "600cc"}},
            ),
        ]

        product = ProductSpecification(
            model_code="TEST",
            base_model_id="TEST_MODEL",
            brand="Test",
            model_name="Test Model",
            model_year=2024,
            price=Decimal("1000.00"),
            pipeline_results=stage_results,
            overall_confidence=0.875,  # Average of stage confidences
        )

        assert len(product.pipeline_results) == 2
        assert product.confidence_level == ConfidenceLevel.MEDIUM

        # Verify we can serialize and deserialize
        json_data = product.model_dump_json()
        reconstructed = ProductSpecification.model_validate_json(json_data)

        assert reconstructed.model_code == product.model_code
        assert len(reconstructed.pipeline_results) == 2

    def test_audit_trail_creation(self):
        """Test audit trail model creation"""
        product_id = uuid4()

        audit = AuditTrail(
            product_id=product_id,
            stage=ProcessingStage.BASE_MODEL_MATCHING,
            action="model_matched",
            before_data={"confidence": 0.0},
            after_data={"confidence": 0.9, "matched_model": "TEST_MODEL"},
            confidence_change=0.9,
        )

        assert audit.product_id == product_id
        assert audit.stage == ProcessingStage.BASE_MODEL_MATCHING
        assert audit.confidence_change == 0.9
        assert isinstance(audit.timestamp, datetime)


# Performance and edge case tests
class TestModelPerformance:
    """Test model performance and edge cases"""

    def test_large_specifications_serialization(self):
        """Test handling large specification dictionaries"""
        large_specs = {f"spec_{i}": f"value_{i}" for i in range(1000)}

        product = ProductSpecification(
            model_code="LARGE_TEST",
            base_model_id="LARGE_MODEL",
            brand="Test",
            model_name="Large Test Model",
            model_year=2024,
            price=Decimal("1000.00"),
            specifications=large_specs,
            overall_confidence=0.8,
        )

        # Should handle large specs without issues
        assert len(product.specifications) == 1000

        # Should serialize/deserialize correctly
        json_data = product.model_dump_json()
        reconstructed = ProductSpecification.model_validate_json(json_data)
        assert len(reconstructed.specifications) == 1000

    def test_unicode_handling(self):
        """Test Unicode character handling in model fields"""
        product = ProductSpecification(
            model_code="TËST_ÛNICØDE",
            base_model_id="TËST_MÖDEL",
            brand="Tëst Bränd",
            model_name="Tëst Mödel with Ünicøde",
            model_year=2024,
            price=Decimal("1000.00"),
            overall_confidence=0.8,
        )

        assert "Ü" in product.model_name
        assert "Ë" in product.model_code

        # Should serialize correctly
        json_data = product.model_dump_json()
        reconstructed = ProductSpecification.model_validate_json(json_data)
        assert reconstructed.model_name == product.model_name
