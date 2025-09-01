"""
5-Stage Inheritance Pipeline Controller

Implements the complete product reconciliation pipeline following
the established methodology and Universal Development Standards.
"""
import time
from typing import Optional

import structlog
from pydantic import BaseModel, ConfigDict

from src.models.domain import (
    ConfidenceLevel,
    PipelineConfig,
    PipelineStageResult,
    PriceEntry,
    ProcessingError,
    ProcessingStage,
    ProductSpecification,
    SpringOption,
)
from src.pipeline.stages.base_model_matching import BaseModelMatchingStage
from src.pipeline.stages.customization_processing import CustomizationProcessingStage
from src.pipeline.stages.final_validation import FinalValidationStage
from src.pipeline.stages.specification_inheritance import SpecificationInheritanceStage
from src.pipeline.stages.spring_options_enhancement import SpringOptionsEnhancementStage
from src.pipeline.validation.multi_layer_validator import MultiLayerValidator
from src.repositories.product_repository import ProductRepository

logger = structlog.get_logger(__name__)


class PipelineResult(BaseModel):
    """Complete pipeline processing result"""

    success: bool
    products_processed: int
    products_successful: int
    products_failed: int
    products: list[ProductSpecification]
    errors: list[ProcessingError]
    total_processing_time_ms: int
    claude_tokens_used: int = 0
    claude_cost_total: float = 0.0


class InheritancePipeline:
    """
    Main pipeline controller implementing 5-stage inheritance processing.

    Pipeline Stages:
    1. Base Model Matching - Find catalog base model for price entry
    2. Specification Inheritance - Inherit complete specifications
    3. Customization Processing - Apply price list customizations
    4. Spring Options Enhancement - Detect and apply spring modifications
    5. Final Validation - Multi-layer validation and confidence scoring
    """

    def __init__(
        self,
        config: PipelineConfig,
        product_repository: ProductRepository,
        validator: MultiLayerValidator,
    ) -> None:
        self.config = config
        self.product_repository = product_repository
        self.validator = validator
        self.logger = logger.bind(component="inheritance_pipeline")

        # Initialize pipeline stages
        self.stages = {
            ProcessingStage.BASE_MODEL_MATCHING: BaseModelMatchingStage(config),
            ProcessingStage.SPECIFICATION_INHERITANCE: SpecificationInheritanceStage(
                config
            ),
            ProcessingStage.CUSTOMIZATION_PROCESSING: CustomizationProcessingStage(
                config
            ),
            ProcessingStage.SPRING_OPTIONS_ENHANCEMENT: SpringOptionsEnhancementStage(
                config
            ),
            ProcessingStage.FINAL_VALIDATION: FinalValidationStage(config, validator),
        }

        self.logger.info("Pipeline initialized with all stages")

    async def process_price_entries(
        self, price_entries: list[PriceEntry]
    ) -> PipelineResult:
        """
        Process multiple price entries through complete 5-stage pipeline.

        Args:
            price_entries: List of price entries to process

        Returns:
            Complete pipeline result with all products and errors
        """
        start_time = time.time()

        self.logger.info(
            "Starting pipeline processing",
            entry_count=len(price_entries),
            pipeline_stages=len(self.stages),
        )

        successful_products: list[ProductSpecification] = []
        processing_errors: list[ProcessingError] = []
        total_claude_tokens = 0
        total_claude_cost = 0.0

        for price_entry in price_entries:
            try:
                result = await self._process_single_entry(price_entry)

                if result.success:
                    successful_products.append(result.product)
                    total_claude_tokens += result.claude_tokens_used
                    total_claude_cost += result.claude_cost
                else:
                    processing_errors.extend(result.errors)

            except Exception as e:
                self.logger.error(
                    "Unexpected error processing price entry",
                    model_code=price_entry.model_code,
                    error=str(e),
                )

                error = ProcessingError(
                    error_type="pipeline_error",
                    error_message=f"Pipeline processing failed: {e}",
                    error_code="PIPELINE_001",
                    model_code=price_entry.model_code,
                    technical_details={"exception": str(e)},
                    recovery_suggestion="Check logs and retry processing",
                    retry_recommended=True,
                )
                processing_errors.append(error)

        total_time_ms = int((time.time() - start_time) * 1000)

        result = PipelineResult(
            success=len(processing_errors) == 0,
            products_processed=len(price_entries),
            products_successful=len(successful_products),
            products_failed=len(processing_errors),
            products=successful_products,
            errors=processing_errors,
            total_processing_time_ms=total_time_ms,
            claude_tokens_used=total_claude_tokens,
            claude_cost_total=total_claude_cost,
        )

        self.logger.info(
            "Pipeline processing completed",
            total_entries=len(price_entries),
            successful=len(successful_products),
            failed=len(processing_errors),
            processing_time_ms=total_time_ms,
        )

        return result

    async def _process_single_entry(
        self, price_entry: PriceEntry
    ) -> "SingleEntryResult":
        """Process single price entry through all pipeline stages"""

        entry_logger = self.logger.bind(
            model_code=price_entry.model_code, brand=price_entry.brand
        )

        entry_logger.info("Starting single entry processing")

        # Initialize pipeline context
        pipeline_context = PipelineContext(
            price_entry=price_entry,
            stage_results=[],
            current_product=None,
            claude_tokens_used=0,
            claude_cost=0.0,
        )

        # Process through each stage sequentially
        for stage_name, stage in self.stages.items():
            stage_start_time = time.time()

            try:
                entry_logger.info(f"Processing stage: {stage_name}")

                stage_result = await stage.process(pipeline_context)
                stage_result.processing_time_ms = int(
                    (time.time() - stage_start_time) * 1000
                )

                # Add to pipeline context
                pipeline_context.stage_results.append(stage_result)
                pipeline_context.claude_tokens_used += (
                    stage_result.claude_tokens_used or 0
                )
                pipeline_context.claude_cost += stage_result.claude_api_cost or 0.0

                # Check if stage failed
                if not stage_result.success:
                    entry_logger.error(
                        f"Stage {stage_name} failed",
                        errors=stage_result.errors,
                        warnings=stage_result.warnings,
                    )

                    # Create processing error
                    error = ProcessingError(
                        error_type="stage_failure",
                        error_message=f"Stage {stage_name} failed: {'; '.join(stage_result.errors)}",
                        error_code=f"STAGE_{stage_name.upper()}",
                        stage=stage_name,
                        model_code=price_entry.model_code,
                        technical_details=stage_result.stage_data,
                        recovery_suggestion=f"Review {stage_name} configuration and input data",
                        retry_recommended=True,
                    )

                    return SingleEntryResult(
                        success=False,
                        product=None,
                        errors=[error],
                        claude_tokens_used=pipeline_context.claude_tokens_used,
                        claude_cost=pipeline_context.claude_cost,
                    )

                entry_logger.info(
                    f"Stage {stage_name} completed successfully",
                    confidence=stage_result.confidence_score,
                    processing_time_ms=stage_result.processing_time_ms,
                )

            except Exception as e:
                entry_logger.error(
                    f"Unexpected error in stage {stage_name}", error=str(e)
                )

                error = ProcessingError(
                    error_type="stage_exception",
                    error_message=f"Stage {stage_name} threw exception: {e}",
                    error_code=f"STAGE_EX_{stage_name.upper()}",
                    stage=stage_name,
                    model_code=price_entry.model_code,
                    technical_details={"exception": str(e)},
                    recovery_suggestion="Check stage implementation and dependencies",
                    retry_recommended=False,
                )

                return SingleEntryResult(
                    success=False,
                    product=None,
                    errors=[error],
                    claude_tokens_used=pipeline_context.claude_tokens_used,
                    claude_cost=pipeline_context.claude_cost,
                )

        # All stages completed successfully - create final product
        final_product = self._create_final_product(pipeline_context)

        entry_logger.info(
            "Entry processing completed successfully",
            product_id=final_product.product_id,
            overall_confidence=final_product.overall_confidence,
            confidence_level=final_product.confidence_level,
        )

        return SingleEntryResult(
            success=True,
            product=final_product,
            errors=[],
            claude_tokens_used=pipeline_context.claude_tokens_used,
            claude_cost=pipeline_context.claude_cost,
        )

    def _create_final_product(self, context: "PipelineContext") -> ProductSpecification:
        """Create final product specification from pipeline context"""

        # Calculate overall confidence as weighted average of stage confidences
        stage_weights = {
            ProcessingStage.BASE_MODEL_MATCHING: 0.3,
            ProcessingStage.SPECIFICATION_INHERITANCE: 0.2,
            ProcessingStage.CUSTOMIZATION_PROCESSING: 0.2,
            ProcessingStage.SPRING_OPTIONS_ENHANCEMENT: 0.1,
            ProcessingStage.FINAL_VALIDATION: 0.2,
        }

        overall_confidence = 0.0
        for result in context.stage_results:
            weight = stage_weights.get(result.stage, 0.0)
            overall_confidence += result.confidence_score * weight

        # Determine confidence level
        if overall_confidence >= self.config.auto_accept_threshold:
            confidence_level = ConfidenceLevel.HIGH
        elif overall_confidence >= self.config.manual_review_threshold:
            confidence_level = ConfidenceLevel.MEDIUM
        else:
            confidence_level = ConfidenceLevel.LOW

        # Extract data from stage results
        base_model_data = self._get_stage_data(
            context, ProcessingStage.BASE_MODEL_MATCHING
        )
        specifications = self._get_stage_data(
            context, ProcessingStage.SPECIFICATION_INHERITANCE
        )
        customizations = self._get_stage_data(
            context, ProcessingStage.CUSTOMIZATION_PROCESSING
        )
        spring_options_data = self._get_stage_data(
            context, ProcessingStage.SPRING_OPTIONS_ENHANCEMENT
        )

        # Build spring options list
        spring_options = []
        if spring_options_data and spring_options_data.get("detected_options"):
            for option_data in spring_options_data["detected_options"]:
                spring_options.append(SpringOption(**option_data))

        return ProductSpecification(
            model_code=context.price_entry.model_code,
            base_model_id=base_model_data.get("matched_base_model_id", "unknown"),
            brand=context.price_entry.brand,
            model_name=base_model_data.get(
                "model_name", context.price_entry.model_name or "Unknown"
            ),
            model_year=context.price_entry.model_year,
            price=context.price_entry.price,
            currency=context.price_entry.currency,
            specifications=specifications or {},
            spring_options=spring_options,
            pipeline_results=context.stage_results,
            overall_confidence=overall_confidence,
            confidence_level=confidence_level,
        )

    def _get_stage_data(
        self, context: "PipelineContext", stage: ProcessingStage
    ) -> dict:
        """Extract stage data from pipeline context"""
        for result in context.stage_results:
            if result.stage == stage:
                return result.stage_data
        return {}


class PipelineContext(BaseModel):
    """Context passed between pipeline stages"""

    price_entry: PriceEntry
    stage_results: list[PipelineStageResult]
    current_product: Optional[ProductSpecification] = None
    claude_tokens_used: int = 0
    claude_cost: float = 0.0

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SingleEntryResult(BaseModel):
    """Result of processing single price entry"""

    success: bool
    product: Optional[ProductSpecification] = None
    errors: list[ProcessingError]
    claude_tokens_used: int = 0
    claude_cost: float = 0.0
