"""Tests for Specification Inheritance Stage (Stage 2)"""
import pytest
from decimal import Decimal
from uuid import uuid4

from src.models.domain import (
    BaseModelSpecification,
    PipelineConfig,
    PipelineContext,
    PriceEntry,
    ProcessingStage,
)
from src.pipeline.stages.specification_inheritance import SpecificationInheritanceStage


class TestSpecificationInheritanceStage:
    """Test specification inheritance logic"""

    @pytest.fixture
    def config(self):
        """Create test pipeline configuration"""
        return PipelineConfig(
            claude_api_key="test-key",
            max_retries=3,
            timeout_seconds=30,
        )

    @pytest.fixture
    def base_model(self):
        """Create test base model specification"""
        return BaseModelSpecification(
            base_model_id="MXZ_TRAIL_600",
            model_name="MXZ Trail 600",
            brand="Ski-Doo",
            model_year=2024,
            category="Trail",
            source_catalog="test_catalog.pdf",
            extraction_quality=0.9,
            specifications={
                "engine": {"type": "2-stroke", "displacement": "600cc"},
                "suspension": "tMotion",
                "track": {"length": "137", "width": "15"},
            },
            inheritance_confidence=0.85,
        )

    @pytest.fixture
    def price_entry(self):
        """Create test price entry"""
        return PriceEntry(
            model_code="MXZ_TRAIL_600_EFI",
            brand="Ski-Doo",
            price=Decimal("15000.00"),
            model_year=2024,
            source_file="test.pdf",
            page_number=1,
            extraction_confidence=0.9,
        )

    @pytest.fixture
    def context(self, price_entry, base_model):
        """Create test pipeline context"""
        return PipelineContext(
            price_entry=price_entry,
            matched_base_model=base_model,
        )

    @pytest.fixture
    def stage(self, config):
        """Create specification inheritance stage"""
        return SpecificationInheritanceStage(config)

    @pytest.mark.asyncio
    async def test_successful_inheritance(self, stage, context):
        """Test successful specification inheritance"""
        result = await stage._execute_stage(context)

        assert result["success"] is True
        assert "inherited_specs" in result
        assert result["confidence"] > 0.7
        assert "base_model_id" in result
        
        # Check that base specifications are inherited
        inherited_specs = result["inherited_specs"]
        assert "engine" in inherited_specs
        assert "suspension" in inherited_specs
        assert "track" in inherited_specs

    @pytest.mark.asyncio
    async def test_brand_specific_inheritance(self, stage, context):
        """Test brand-specific inheritance rules"""
        result = await stage._execute_stage(context)
        inherited_specs = result["inherited_specs"]
        
        # Ski-Doo specific features should be added
        assert inherited_specs.get("drive_system") == "QRS"
        assert inherited_specs.get("throttle") == "electronic"

    @pytest.mark.asyncio
    async def test_year_specific_features(self, stage, context):
        """Test year-specific feature inheritance"""
        # 2024 model should get modern features
        result = await stage._execute_stage(context)
        inherited_specs = result["inherited_specs"]
        
        assert inherited_specs.get("display") == "digital_gauge"
        assert inherited_specs.get("connectivity") == "bluetooth"
        assert inherited_specs.get("starting") == "electric_start"

    @pytest.mark.asyncio
    async def test_price_tier_features(self, stage, context):
        """Test price tier-based feature inheritance"""
        result = await stage._execute_stage(context)
        inherited_specs = result["inherited_specs"]
        
        # Mid-tier pricing should get appropriate features
        assert inherited_specs.get("heated_grips") is True
        assert inherited_specs.get("reverse") == "manual"
        assert inherited_specs.get("suspension_adjustment") == "manual"

    @pytest.mark.asyncio
    async def test_missing_base_model(self, stage, context):
        """Test handling when no base model is matched"""
        context.matched_base_model = None
        
        result = await stage._execute_stage(context)
        
        assert result["success"] is False
        assert "No base model found" in result["error"]
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_confidence_calculation(self, stage, context):
        """Test confidence score calculation"""
        result = await stage._execute_stage(context)
        
        # Should have reasonable confidence
        confidence = result["confidence"]
        assert 0.7 <= confidence <= 0.95
        
        # Context should be updated
        assert context.current_confidence == confidence

    @pytest.mark.asyncio
    async def test_premium_model_inheritance(self, stage, context):
        """Test inheritance for premium models"""
        # Set high price for premium features
        context.price_entry.price = Decimal("20000.00")
        
        result = await stage._execute_stage(context)
        inherited_specs = result["inherited_specs"]
        
        # Premium features should be inherited
        assert inherited_specs.get("heated_grips") is True
        assert inherited_specs.get("reverse") == "electric"
        assert inherited_specs.get("suspension_adjustment") == "electronic"

    @pytest.mark.asyncio
    async def test_legacy_model_inheritance(self, stage, context):
        """Test inheritance for older model years"""
        # Set older model year
        context.price_entry.model_year = 2019
        
        result = await stage._execute_stage(context)
        inherited_specs = result["inherited_specs"]
        
        # Should not have modern connectivity
        assert "connectivity" not in inherited_specs
        assert inherited_specs.get("display") == "analog_gauge"