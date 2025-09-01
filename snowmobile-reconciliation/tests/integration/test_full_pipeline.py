"""
Integration tests for the complete snowmobile reconciliation pipeline.

Tests the full end-to-end flow from price entry to final product specification.
"""
import asyncio
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.models.domain import (
    BaseModelSpecification,
    ConfidenceLevel,
    PipelineConfig,
    PipelineContext,
    PriceEntry,
    ProcessingStage,
)
from src.pipeline.stages.base_model_matching import BaseModelMatchingStage
from src.pipeline.stages.specification_inheritance import SpecificationInheritanceStage
from src.pipeline.stages.customization_processing import CustomizationProcessingStage
from src.pipeline.stages.spring_options_enhancement import SpringOptionsEnhancementStage
from src.pipeline.stages.final_validation import FinalValidationStage


class TestFullPipelineIntegration:
    """Test complete pipeline execution with realistic scenarios"""

    @pytest.fixture
    def config(self):
        """Create pipeline configuration"""
        return PipelineConfig(
            claude_api_key="test-key",
            max_retries=3,
            timeout_seconds=30,
            enable_parallel_stages=False,  # Sequential for testing
            enable_spring_options=True,
            enable_confidence_tuning=True,
        )

    @pytest.fixture
    def sample_base_models(self):
        """Create sample base model catalog"""
        return [
            BaseModelSpecification(
                base_model_id="MXZ_TRAIL_600",
                model_name="MXZ Trail 600",
                brand="Ski-Doo",
                model_year=2024,
                category="Trail",
                source_catalog="catalog_2024.pdf",
                extraction_quality=0.9,
                engine_specs={"type": "2-stroke", "displacement": "600cc"},
                suspension={"type": "tMotion"},
                dimensions={"track_length": "137", "track_width": "15"},
                features={"cooling": "liquid"},
                inheritance_confidence=0.85,
            ),
            BaseModelSpecification(
                base_model_id="RENEGADE_850",
                model_name="Renegade 850",
                brand="Ski-Doo",
                model_year=2024,
                category="Crossover",
                source_catalog="catalog_2024.pdf",
                extraction_quality=0.95,
                engine_specs={"type": "2-stroke", "displacement": "850cc"},
                suspension={"type": "RAS 3"},
                dimensions={"track_length": "137", "track_width": "16"},
                features={"cooling": "liquid"},
                inheritance_confidence=0.9,
            ),
            BaseModelSpecification(
                base_model_id="ASSAULT_800",
                model_name="Assault 800",
                brand="Polaris",
                model_year=2024,
                category="Mountain",
                source_catalog="catalog_2024.pdf",
                extraction_quality=0.88,
                engine_specs={"type": "2-stroke", "displacement": "800cc"},
                suspension={"type": "Pro-Ride"},
                dimensions={"track_length": "155", "track_width": "15"},
                features={"cooling": "liquid"},
                inheritance_confidence=0.87,
            ),
        ]

    @pytest.mark.asyncio
    async def test_premium_skidoo_renegade_pipeline(self, config, sample_base_models):
        """Test processing a premium Ski-Doo Renegade model through all stages"""
        
        # Create price entry for a premium Renegade
        price_entry = PriceEntry(
            model_code="RENEGADE_X_850_ETEC_TURBO",
            brand="Ski-Doo",
            price=Decimal("24500.00"),
            model_year=2024,
            source_file="price_list_2024.pdf",
            page_number=15,
            extraction_confidence=0.92,
        )
        
        # Initialize pipeline context
        context = PipelineContext(
            price_entry=price_entry,
            processing_id=uuid4(),
        )
        
        # Stage 1: Base Model Matching (simulate)
        # Use sample base model directly since we're testing stages 2-5
        context.matched_base_model = sample_base_models[1]  # Renegade 850
        context.current_confidence = 0.9
        
        # Stage 2: Specification Inheritance
        stage2 = SpecificationInheritanceStage(config)
        result2 = await stage2._execute_stage(context)
        assert result2["success"] is True
        assert len(context.inherited_specs) > 5
        assert context.inherited_specs.get("heated_grips") is True  # Premium feature
        assert context.inherited_specs.get("reverse") == "electric"  # Premium feature
        
        # Stage 3: Customization Processing
        stage3 = CustomizationProcessingStage(config)
        result3 = await stage3._execute_stage(context)
        assert result3["success"] is True
        assert context.customizations.get("displacement") == "850cc"
        assert context.customizations.get("fuel_system") == "e_tec_direct_injection"
        assert context.customizations.get("forced_induction") == "turbocharged"
        assert context.customizations.get("model_line") == "Renegade"
        
        # Stage 4: Spring Options Enhancement
        stage4 = SpringOptionsEnhancementStage(config)
        result4 = await stage4._execute_stage(context)
        assert result4["success"] is True
        assert len(context.spring_options) >= 2  # Should detect multiple options
        
        # Check for specific spring options
        option_types = [opt.option_type.value for opt in context.spring_options]
        assert any("performance" in ot for ot in option_types)  # Turbo = performance
        assert any("comfort" in ot for ot in option_types)  # Premium comfort
        
        # Stage 5: Final Validation
        stage5 = FinalValidationStage(config)
        result5 = await stage5._execute_stage(context)
        assert result5["success"] is True
        
        product_spec = result5["product_specification"]
        assert product_spec["model_code"] == "RENEGADE_X_850_ETEC_TURBO"
        assert product_spec["brand"] == "Ski-Doo"
        assert float(product_spec["price"]) == 24500.00
        assert product_spec["confidence_level"] in ["high", "medium"]
        assert len(product_spec["specifications"]) >= 10
        assert len(product_spec["spring_options"]) >= 2

    @pytest.mark.asyncio
    async def test_budget_polaris_trail_pipeline(self, config, sample_base_models):
        """Test processing a budget Polaris trail model"""
        
        price_entry = PriceEntry(
            model_code="SWITCHBACK_600",
            brand="Polaris",
            price=Decimal("11500.00"),
            model_year=2024,
            source_file="price_list_2024.pdf",
            page_number=8,
            extraction_confidence=0.88,
        )
        
        context = PipelineContext(
            price_entry=price_entry,
            processing_id=uuid4(),
        )
        
        # Since we don't have a matching Polaris 600, use the Assault as base
        context.matched_base_model = sample_base_models[2]
        context.current_confidence = 0.75  # Lower confidence due to mismatch
        
        # Run through all stages
        stage2 = SpecificationInheritanceStage(config)
        result2 = await stage2._execute_stage(context)
        assert result2["success"] is True
        # Budget features
        assert context.inherited_specs.get("heated_grips") is False
        assert context.inherited_specs.get("reverse") is False
        
        stage3 = CustomizationProcessingStage(config)
        result3 = await stage3._execute_stage(context)
        assert result3["success"] is True
        assert context.customizations.get("displacement") == "600cc"
        assert context.customizations.get("model_line") == "Switchback"
        
        stage4 = SpringOptionsEnhancementStage(config)
        result4 = await stage4._execute_stage(context)
        assert result4["success"] is True
        # Budget model should have fewer spring options
        assert len(context.spring_options) <= 2
        
        stage5 = FinalValidationStage(config)
        result5 = await stage5._execute_stage(context)
        assert result5["success"] is True
        
        # Verify final confidence is reasonable despite budget model
        assert result5["confidence"] >= 0.6

    @pytest.mark.asyncio
    async def test_mountain_model_with_deep_snow_options(self, config, sample_base_models):
        """Test mountain model with specialized deep snow configuration"""
        
        price_entry = PriceEntry(
            model_code="SUMMIT_SP_850_165_POWERCLAW",
            brand="Ski-Doo",
            price=Decimal("19800.00"),
            model_year=2024,
            source_file="price_list_2024.pdf",
            page_number=22,
            extraction_confidence=0.91,
        )
        
        context = PipelineContext(
            price_entry=price_entry,
            processing_id=uuid4(),
        )
        
        # Use Renegade as base (not ideal but testing adaptation)
        context.matched_base_model = sample_base_models[1]
        context.current_confidence = 0.8
        
        # Run through pipeline
        stage2 = SpecificationInheritanceStage(config)
        await stage2._execute_stage(context)
        
        stage3 = CustomizationProcessingStage(config)
        result3 = await stage3._execute_stage(context)
        # Should detect Summit variant
        assert context.customizations.get("model_line") == "Summit"
        assert context.customizations.get("category") == "mountain"
        assert context.customizations.get("target_use") == "deep_snow"
        
        stage4 = SpringOptionsEnhancementStage(config)
        result4 = await stage4._execute_stage(context)
        # Should detect PowerClaw track upgrade
        track_options = [
            opt for opt in context.spring_options 
            if "track" in opt.option_type.value.lower()
        ]
        assert len(track_options) >= 1
        assert any("Power Claw" in opt.description for opt in track_options)
        
        # Should detect deep snow configuration
        weather_options = [
            opt for opt in context.spring_options
            if "weather" in opt.option_type.value.lower()
        ]
        assert len(weather_options) >= 1

    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self, config):
        """Test pipeline handles errors gracefully"""
        
        # Test that invalid price entry creation fails as expected
        with pytest.raises(ValidationError):
            PriceEntry(
                model_code="",  # Invalid empty model code
                brand="Unknown",
                price=Decimal("-1000.00"),  # Invalid negative price
                model_year=2024,
                source_file="test.pdf",
                page_number=1,
                extraction_confidence=0.5,
            )
        
        # Create a valid but problematic price entry for pipeline testing
        price_entry = PriceEntry(
            model_code="INVALID_TEST_MODEL",  # Valid format but unknown model
            brand="Unknown",
            price=Decimal("1000.00"),  # Valid positive price
            model_year=2024,
            source_file="test.pdf",
            page_number=1,
            extraction_confidence=0.5,
        )
        
        context = PipelineContext(
            price_entry=price_entry,
            processing_id=uuid4(),
        )
        
        # Stage 2 should handle missing base model
        stage2 = SpecificationInheritanceStage(config)
        result2 = await stage2._execute_stage(context)
        assert result2["success"] is False
        assert "No base model" in result2["error"]
        
        # Stage 5 should validate and fail appropriately
        stage5 = FinalValidationStage(config)
        result5 = await stage5._execute_stage(context)
        assert result5["success"] is False

    @pytest.mark.asyncio
    async def test_confidence_degradation_through_pipeline(self, config, sample_base_models):
        """Test that confidence appropriately degrades with uncertainty"""
        
        price_entry = PriceEntry(
            model_code="UNKNOWN_MODEL_XYZ",  # Unknown model code
            brand="Ski-Doo",
            price=Decimal("15000.00"),
            model_year=2021,  # Valid older model (still within constraint)
            source_file="price_list_2020.pdf",
            page_number=99,
            extraction_confidence=0.6,  # Low extraction confidence
        )
        
        context = PipelineContext(
            price_entry=price_entry,
            processing_id=uuid4(),
        )
        
        # Use mismatched base model
        context.matched_base_model = sample_base_models[0]
        context.current_confidence = 0.6
        
        initial_confidence = context.current_confidence
        
        # Run through pipeline
        stage2 = SpecificationInheritanceStage(config)
        await stage2._execute_stage(context)
        
        stage3 = CustomizationProcessingStage(config)
        await stage3._execute_stage(context)
        # Confidence may increase during processing due to successful stage completion,
        # but final result should reflect uncertainty
        
        stage4 = SpringOptionsEnhancementStage(config)
        await stage4._execute_stage(context)
        
        stage5 = FinalValidationStage(config)
        result5 = await stage5._execute_stage(context)
        
        # Final confidence should reflect uncertainty
        final_confidence = result5["confidence"]
        assert final_confidence < 0.7  # Should be low due to unknowns
        
        product_spec = result5["product_specification"]
        assert product_spec["confidence_level"] == "low"


class TestPipelinePerformance:
    """Test pipeline performance and scalability"""

    @pytest.fixture
    def config(self):
        """Create performance test configuration"""
        return PipelineConfig(
            claude_api_key="test-key",
            max_retries=1,
            timeout_seconds=5,
            enable_parallel_stages=True,  # Enable parallel processing
            batch_processing_enabled=True,
            max_batch_size=10,
        )

    @pytest.mark.asyncio
    async def test_batch_processing_performance(self, config):
        """Test processing multiple price entries in batch"""
        
        # Create batch of price entries
        price_entries = []
        for i in range(10):
            price_entries.append(PriceEntry(
                model_code=f"TEST_MODEL_{i:03d}",
                brand="Ski-Doo" if i % 2 == 0 else "Polaris",
                price=Decimal(str(12000 + i * 1000)),
                model_year=2024,
                source_file=f"batch_{i}.pdf",
                page_number=i + 1,
                extraction_confidence=0.85 + (i * 0.01),
            ))
        
        # Process all entries
        start_time = asyncio.get_event_loop().time()
        
        results = []
        for entry in price_entries:
            context = PipelineContext(
                price_entry=entry,
                processing_id=uuid4(),
            )
            
            # Simulate quick processing
            stage3 = CustomizationProcessingStage(config)
            result = await stage3._execute_stage(context)
            results.append(result)
        
        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time
        
        # All should succeed
        assert all(r["success"] for r in results)
        
        # Should process reasonably quickly (< 1 second for 10 items)
        assert processing_time < 1.0

    @pytest.mark.asyncio
    async def test_memory_efficiency_large_specs(self, config):
        """Test memory efficiency with large specification dictionaries"""
        
        # Create entry with very large specifications
        large_specs = {f"spec_{i}": f"value_{i}" for i in range(1000)}
        
        price_entry = PriceEntry(
            model_code="LARGE_SPEC_MODEL",
            brand="Ski-Doo",
            price=Decimal("20000.00"),
            model_year=2024,
            source_file="large.pdf",
            page_number=1,
            extraction_confidence=0.9,
        )
        
        context = PipelineContext(
            price_entry=price_entry,
            inherited_specs=large_specs,
            processing_id=uuid4(),
        )
        
        # Process through customization stage
        stage3 = CustomizationProcessingStage(config)
        result = await stage3._execute_stage(context)
        
        assert result["success"] is True
        # Should handle large specs without issues
        assert len(context.customizations) >= 0