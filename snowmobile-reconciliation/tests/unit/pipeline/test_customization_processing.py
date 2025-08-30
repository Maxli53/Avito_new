"""Tests for Customization Processing Stage (Stage 3)"""
import pytest
from decimal import Decimal

from src.models.domain import (
    PipelineConfig,
    PipelineContext,
    PriceEntry,
)
from src.pipeline.stages.customization_processing import CustomizationProcessingStage


class TestCustomizationProcessingStage:
    """Test customization detection and processing"""

    @pytest.fixture
    def config(self):
        """Create test pipeline configuration"""
        return PipelineConfig(
            claude_api_key="test-key",
            max_retries=3,
            timeout_seconds=30,
        )

    @pytest.fixture
    def stage(self, config):
        """Create customization processing stage"""
        return CustomizationProcessingStage(config)

    @pytest.fixture
    def context_with_inherited_specs(self):
        """Create context with inherited specifications"""
        price_entry = PriceEntry(
            model_code="MXZ_TRAIL_800_EFI",
            brand="Ski-Doo",
            price=Decimal("16000.00"),
            model_year=2024,
            source_file="test.pdf",
            page_number=1,
            extraction_confidence=0.9,
        )
        
        context = PipelineContext(
            price_entry=price_entry,
            inherited_specs={
                "suspension": "tMotion",
                "drive_system": "QRS",
                "display": "digital_gauge",
            },
        )
        
        return context

    @pytest.mark.asyncio
    async def test_engine_detection_from_code(self, stage, context_with_inherited_specs):
        """Test engine specification detection from model code"""
        result = await stage._execute_stage(context_with_inherited_specs)
        
        assert result["success"] is True
        customizations = result["customizations"]
        
        # Should detect 800cc engine from model code
        assert customizations.get("displacement") == "800cc"
        assert customizations.get("engine_type") == "2-stroke"

    @pytest.mark.asyncio
    async def test_track_type_detection(self, stage, context_with_inherited_specs):
        """Test track type detection from model code"""
        result = await stage._execute_stage(context_with_inherited_specs)
        customizations = result["customizations"]
        
        # Should detect trail track from "TRAIL" in model code
        assert customizations.get("track_type") == "trail"
        assert customizations.get("track_length") == "137"

    @pytest.mark.asyncio
    async def test_fuel_system_detection(self, stage, context_with_inherited_specs):
        """Test fuel system detection from EFI in model code"""
        result = await stage._execute_stage(context_with_inherited_specs)
        customizations = result["customizations"]
        
        # Should detect EFI from model code
        assert customizations.get("fuel_system") == "electronic_fuel_injection"

    @pytest.mark.asyncio
    async def test_variant_detection_skidoo(self, stage):
        """Test Ski-Doo variant detection"""
        price_entry = PriceEntry(
            model_code="MXZ_RENEGADE_850_ETEC",
            brand="Ski-Doo",
            price=Decimal("18000.00"),
            model_year=2024,
            source_file="test.pdf",
            page_number=1,
            extraction_confidence=0.9,
        )
        
        context = PipelineContext(
            price_entry=price_entry,
            inherited_specs={},
        )
        
        result = await stage._execute_stage(context)
        customizations = result["customizations"]
        
        # Should detect Renegade variant (checked first now)
        assert customizations.get("model_line") == "Renegade"
        assert customizations.get("category") == "crossover"
        # target_use gets overridden by performance level detection later
        assert customizations.get("target_use") in ["versatile", "high_performance"]

    @pytest.mark.asyncio
    async def test_variant_detection_polaris(self, stage):
        """Test Polaris variant detection"""
        price_entry = PriceEntry(
            model_code="ASSAULT_800_SWITCHBACK",
            brand="Polaris",
            price=Decimal("17000.00"),
            model_year=2024,
            source_file="test.pdf",
            page_number=1,
            extraction_confidence=0.9,
        )
        
        context = PipelineContext(
            price_entry=price_entry,
            inherited_specs={},
        )
        
        result = await stage._execute_stage(context)
        customizations = result["customizations"]
        
        # Should detect both model lines
        assert "model_line" in customizations
        assert customizations.get("category") == "mountain"

    @pytest.mark.asyncio
    async def test_premium_variant_detection(self, stage):
        """Test premium variant detection"""
        price_entry = PriceEntry(
            model_code="MXZ_X_LIMITED_900",
            brand="Ski-Doo",
            price=Decimal("22000.00"),
            model_year=2024,
            source_file="test.pdf",
            page_number=1,
            extraction_confidence=0.9,
        )
        
        context = PipelineContext(
            price_entry=price_entry,
            inherited_specs={},
        )
        
        result = await stage._execute_stage(context)
        customizations = result["customizations"]
        
        # Should detect premium features
        assert customizations.get("trim_level") == "limited"
        assert customizations.get("features_level") == "premium"
        assert customizations.get("performance_level") == "extreme"

    @pytest.mark.asyncio
    async def test_confidence_calculation(self, stage, context_with_inherited_specs):
        """Test customization confidence calculation"""
        result = await stage._execute_stage(context_with_inherited_specs)
        
        confidence = result["confidence"]
        customization_count = result["customization_count"]
        
        # Should have reasonable confidence with multiple customizations
        assert confidence > 0.6
        assert customization_count >= 3
        assert result["engine_detected"] is True
        assert result["track_detected"] is True

    @pytest.mark.asyncio
    async def test_specification_difference_analysis(self, stage):
        """Test analysis of specification differences"""
        price_entry = PriceEntry(
            model_code="TEST_600_EFI",
            brand="Test Brand",
            price=Decimal("15000.00"),
            model_year=2024,
            source_file="test.pdf",
            page_number=1,
            extraction_confidence=0.9,
        )
        
        context = PipelineContext(
            price_entry=price_entry,
            inherited_specs={
                "engine_type": "4-stroke",  # Will be overridden
                "existing_feature": "value",
            },
        )
        
        result = await stage._execute_stage(context)
        customizations = result["customizations"]
        
        # Should detect customization override
        assert customizations.get("engine_type") == "2-stroke"  # Detected from 600
        assert "engine_type_customized" in customizations
        assert customizations.get("engine_type_original") == "4-stroke"

    @pytest.mark.asyncio
    async def test_complex_model_code_confidence_boost(self, stage):
        """Test confidence boost for complex model codes"""
        price_entry = PriceEntry(
            model_code="MXZ_RENEGADE_X_850_ETEC_TURBO",
            brand="Ski-Doo",
            price=Decimal("25000.00"),
            model_year=2024,
            source_file="test.pdf",
            page_number=1,
            extraction_confidence=0.9,
        )
        
        context = PipelineContext(price_entry=price_entry, inherited_specs={})
        
        result = await stage._execute_stage(context)
        
        # Complex model codes should boost confidence
        assert result["confidence"] > 0.8
        assert len(result["customizations"]) >= 5  # Many features detected