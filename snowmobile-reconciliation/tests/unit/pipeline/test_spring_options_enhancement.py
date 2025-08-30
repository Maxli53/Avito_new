"""Tests for Spring Options Enhancement Stage (Stage 4)"""
import pytest
from decimal import Decimal

from src.models.domain import (
    PipelineConfig,
    PipelineContext,
    PriceEntry,
    SpringOptionType,
)
from src.pipeline.stages.spring_options_enhancement import SpringOptionsEnhancementStage


class TestSpringOptionsEnhancementStage:
    """Test spring options detection and enhancement"""

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
        """Create spring options enhancement stage"""
        return SpringOptionsEnhancementStage(config)

    @pytest.fixture
    def context_with_customizations(self):
        """Create context with customizations from previous stages"""
        price_entry = PriceEntry(
            model_code="MXZ_TRAIL_COBRA_800",
            brand="Ski-Doo",
            price=Decimal("18000.00"),
            model_year=2024,
            source_file="test.pdf",
            page_number=1,
            extraction_confidence=0.9,
        )
        
        context = PipelineContext(
            price_entry=price_entry,
            customizations={
                "track_type": "mountain",
                "suspension_adjustment": "electronic",
                "performance_level": "extreme",
                "features_level": "premium",
            },
        )
        
        return context

    @pytest.mark.asyncio
    async def test_track_upgrade_detection_from_code(self, stage, context_with_customizations):
        """Test track upgrade detection from model code"""
        result = await stage._execute_stage(context_with_customizations)
        
        assert result["success"] is True
        assert result["track_upgrades"] >= 1
        
        spring_options = result["spring_options"]
        track_option = next(
            (opt for opt in spring_options 
             if opt["option_type"] == SpringOptionType.TRACK_UPGRADE.value),
            None
        )
        
        assert track_option is not None
        assert "cobra" in track_option["description"].lower()
        assert track_option["confidence"] >= 0.8

    @pytest.mark.asyncio
    async def test_suspension_upgrade_from_customizations(self, stage, context_with_customizations):
        """Test suspension upgrade detection from customizations"""
        result = await stage._execute_stage(context_with_customizations)
        
        assert result["suspension_upgrades"] >= 1
        
        spring_options = result["spring_options"]
        suspension_option = next(
            (opt for opt in spring_options 
             if opt["option_type"] == SpringOptionType.SUSPENSION_UPGRADE.value),
            None
        )
        
        assert suspension_option is not None
        assert "electronic" in suspension_option["description"].lower()

    @pytest.mark.asyncio
    async def test_comfort_upgrade_detection(self, stage, context_with_customizations):
        """Test comfort upgrade detection"""
        result = await stage._execute_stage(context_with_customizations)
        
        assert result["comfort_upgrades"] >= 1
        
        spring_options = result["spring_options"]
        comfort_options = [
            opt for opt in spring_options 
            if opt["option_type"] == SpringOptionType.COMFORT_UPGRADE.value
        ]
        
        assert len(comfort_options) >= 1

    @pytest.mark.asyncio
    async def test_performance_package_detection(self, stage, context_with_customizations):
        """Test performance package detection"""
        result = await stage._execute_stage(context_with_customizations)
        
        spring_options = result["spring_options"]
        performance_option = next(
            (opt for opt in spring_options 
             if opt["option_type"] == SpringOptionType.PERFORMANCE_UPGRADE.value),
            None
        )
        
        assert performance_option is not None
        assert "extreme" in performance_option["description"].lower()

    @pytest.mark.asyncio
    async def test_seasonal_options_deep_snow(self, stage):
        """Test deep snow seasonal options"""
        price_entry = PriceEntry(
            model_code="SUMMIT_850_MOUNTAIN",
            brand="Ski-Doo",
            price=Decimal("20000.00"),
            model_year=2024,
            source_file="test.pdf",
            page_number=1,
            extraction_confidence=0.9,
        )
        
        context = PipelineContext(
            price_entry=price_entry,
            customizations={
                "target_use": "deep_snow",
                "track_type": "mountain",
            },
        )
        
        result = await stage._execute_stage(context)
        
        spring_options = result["spring_options"]
        weather_option = next(
            (opt for opt in spring_options 
             if opt["option_type"] == SpringOptionType.WEATHER_PROTECTION.value),
            None
        )
        
        assert weather_option is not None
        assert "deep snow" in weather_option["description"].lower()

    @pytest.mark.asyncio
    async def test_multiple_option_types(self, stage):
        """Test detection of multiple spring option types"""
        price_entry = PriceEntry(
            model_code="MXZ_RENEGADE_RIPSAW_AIR_HEATED",
            brand="Ski-Doo",
            price=Decimal("22000.00"),
            model_year=2024,
            source_file="test.pdf",
            page_number=1,
            extraction_confidence=0.9,
        )
        
        context = PipelineContext(
            price_entry=price_entry,
            customizations={
                "features_level": "premium",
                "performance_level": "extreme",
            },
        )
        
        result = await stage._execute_stage(context)
        
        # Should detect multiple types
        assert result["track_upgrades"] >= 1  # RIPSAW
        assert result["suspension_upgrades"] >= 1  # AIR
        assert result["comfort_upgrades"] >= 2  # HEATED + premium features

    @pytest.mark.asyncio
    async def test_option_deduplication(self, stage):
        """Test that duplicate options are removed"""
        price_entry = PriceEntry(
            model_code="PREMIUM_COMFORT_LUXURY",
            brand="Ski-Doo",
            price=Decimal("25000.00"),  # Triggers luxury comfort
            model_year=2024,
            source_file="test.pdf",
            page_number=1,
            extraction_confidence=0.9,
        )
        
        context = PipelineContext(
            price_entry=price_entry,
            customizations={
                "features_level": "premium",  # Also triggers comfort upgrade
            },
        )
        
        result = await stage._execute_stage(context)
        
        # Should deduplicate similar comfort options
        comfort_options = [
            opt for opt in result["spring_options"]
            if opt["option_type"] == SpringOptionType.COMFORT_UPGRADE.value
        ]
        
        # Should not have too many duplicate comfort options
        assert len(comfort_options) <= 3

    @pytest.mark.asyncio
    async def test_confidence_calculation_with_options(self, stage, context_with_customizations):
        """Test confidence calculation based on detected options"""
        result = await stage._execute_stage(context_with_customizations)
        
        confidence = result["confidence"]
        options_count = result["options_count"]
        
        # Should have good confidence with multiple options
        assert confidence > 0.6
        assert options_count >= 3

    @pytest.mark.asyncio
    async def test_no_options_detected(self, stage):
        """Test handling when no spring options are detected"""
        price_entry = PriceEntry(
            model_code="BASIC_MODEL",
            brand="Generic",
            price=Decimal("10000.00"),
            model_year=2020,
            source_file="test.pdf",
            page_number=1,
            extraction_confidence=0.9,
        )
        
        context = PipelineContext(
            price_entry=price_entry,
            customizations={},
        )
        
        result = await stage._execute_stage(context)
        
        assert result["success"] is True
        assert result["options_count"] == 0
        assert result["confidence"] == 0.5  # Neutral confidence

    @pytest.mark.asyncio
    async def test_accessory_pattern_detection(self, stage):
        """Test detection of accessory patterns"""
        price_entry = PriceEntry(
            model_code="TOURING_WINDSHIELD_STORAGE",
            brand="Ski-Doo",
            price=Decimal("16000.00"),
            model_year=2024,
            source_file="test.pdf",
            page_number=1,
            extraction_confidence=0.9,
        )
        
        context = PipelineContext(price_entry=price_entry, customizations={})
        
        result = await stage._execute_stage(context)
        
        spring_options = result["spring_options"]
        
        # Should detect windshield and storage
        weather_options = [
            opt for opt in spring_options
            if opt["option_type"] == SpringOptionType.WEATHER_PROTECTION.value
        ]
        storage_options = [
            opt for opt in spring_options
            if opt["option_type"] == SpringOptionType.STORAGE_UPGRADE.value
        ]
        
        assert len(weather_options) >= 1  # Windshield
        assert len(storage_options) >= 1   # Storage