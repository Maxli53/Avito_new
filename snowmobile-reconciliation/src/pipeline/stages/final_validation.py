"""
Stage 5: Final Validation

Performs comprehensive validation and quality checks on the complete product specification.
This final stage validates all pipeline results, checks for consistency,
and generates the final product specification with confidence scores.
"""
from decimal import Decimal
from typing import Any, Dict, List

from src.models.domain import (
    ConfidenceLevel,
    PipelineConfig,
    PipelineContext,
    ProcessingStage,
    ProductSpecification,
)
from src.pipeline.stages.base_stage import BasePipelineStage


class FinalValidationStage(BasePipelineStage):
    """Performs final validation and generates complete product specification"""

    def __init__(self, config: PipelineConfig):
        super().__init__(ProcessingStage.FINAL_VALIDATION, config)

    async def _execute_stage(self, context: PipelineContext) -> Dict[str, Any]:
        """
        Execute final validation and product specification generation.
        
        Args:
            context: Pipeline context with all processing results
            
        Returns:
            Dictionary with final product specification and validation results
        """
        try:
            # Perform validation checks
            validation_results = self._perform_validation_checks(context)
            
            if not validation_results["is_valid"]:
                return {
                    "success": False,
                    "error": f"Validation failed: {validation_results['errors']}",
                    "validation_results": validation_results,
                    "confidence": 0.0,
                }
            
            # Generate final product specification
            product_spec = self._generate_final_product_specification(context)
            
            # Calculate final confidence
            final_confidence = self._calculate_final_confidence(
                context, validation_results
            )
            
            # Update final confidence in product spec
            product_spec.overall_confidence = final_confidence
            
            return {
                "success": True,
                "product_specification": product_spec.model_dump(),
                "confidence": final_confidence,
                "validation_results": validation_results,
                "specifications_count": len(product_spec.specifications),
                "spring_options_count": len(product_spec.spring_options),
                "pipeline_stages_completed": len(product_spec.pipeline_results),
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Final validation failed: {str(e)}",
                "confidence": 0.0,
            }

    def _perform_validation_checks(self, context: PipelineContext) -> Dict[str, Any]:
        """Perform comprehensive validation checks"""
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "checks_performed": [],
            "quality_score": 0.0,
        }
        
        # Check 1: Required data completeness
        completeness_check = self._check_data_completeness(context)
        validation_results["checks_performed"].append("data_completeness")
        if not completeness_check["passed"]:
            validation_results["is_valid"] = False
            validation_results["errors"].extend(completeness_check["errors"])
        validation_results["warnings"].extend(completeness_check["warnings"])
        
        # Check 2: Specification consistency
        consistency_check = self._check_specification_consistency(context)
        validation_results["checks_performed"].append("specification_consistency")
        if not consistency_check["passed"]:
            validation_results["errors"].extend(consistency_check["errors"])
        validation_results["warnings"].extend(consistency_check["warnings"])
        
        # Check 3: Price reasonableness
        price_check = self._check_price_reasonableness(context)
        validation_results["checks_performed"].append("price_reasonableness")
        validation_results["warnings"].extend(price_check["warnings"])
        
        # Check 4: Spring options compatibility
        options_check = self._check_spring_options_compatibility(context)
        validation_results["checks_performed"].append("spring_options_compatibility")
        validation_results["warnings"].extend(options_check["warnings"])
        
        # Calculate overall quality score
        validation_results["quality_score"] = self._calculate_quality_score(
            completeness_check, consistency_check, price_check, options_check
        )
        
        return validation_results

    def _check_data_completeness(self, context: PipelineContext) -> Dict[str, Any]:
        """Check if required data is complete and valid"""
        result = {"passed": True, "errors": [], "warnings": []}
        
        # Check price entry completeness
        price_entry = context.price_entry
        if not price_entry.model_code:
            result["errors"].append("Missing model code")
            result["passed"] = False
            
        if not price_entry.brand:
            result["errors"].append("Missing brand")
            result["passed"] = False
            
        if price_entry.price <= 0:
            result["errors"].append("Invalid price")
            result["passed"] = False
            
        # Check base model matching
        if not context.matched_base_model:
            result["warnings"].append("No base model matched")
        
        # Check specifications
        if len(context.inherited_specs) < 3:
            result["warnings"].append("Very few specifications inherited")
            
        return result

    def _check_specification_consistency(self, context: PipelineContext) -> Dict[str, Any]:
        """Check internal consistency of specifications"""
        result = {"passed": True, "errors": [], "warnings": []}
        
        specs = {**context.inherited_specs, **context.customizations}
        
        # Check engine/displacement consistency
        if "displacement" in specs and "engine_type" in specs:
            displacement = specs["displacement"]
            engine_type = specs["engine_type"]
            
            # Large displacement should be 4-stroke
            if "1000cc" in displacement and engine_type != "4-stroke":
                result["warnings"].append("Large displacement with 2-stroke engine seems unusual")
                
            # Small displacement should be 2-stroke for snowmobiles
            if "600cc" in displacement and engine_type != "2-stroke":
                result["warnings"].append("Small displacement with 4-stroke engine seems unusual")
        
        # Check track/suspension consistency
        if specs.get("track_type") == "mountain" and "suspension" in specs:
            if "air" not in specs["suspension"].lower():
                result["warnings"].append("Mountain track without air suspension seems unusual")
        
        # Check price tier consistency
        price = float(context.price_entry.price)
        if price > 20000:
            if not specs.get("heated_grips", False):
                result["warnings"].append("High-priced model without heated grips")
            if specs.get("reverse", False) != "electric":
                result["warnings"].append("High-priced model without electric reverse")
        
        return result

    def _check_price_reasonableness(self, context: PipelineContext) -> Dict[str, Any]:
        """Check if price is reasonable for the specifications"""
        result = {"warnings": []}
        
        price = float(context.price_entry.price)
        specs = {**context.inherited_specs, **context.customizations}
        
        # Price ranges by brand (rough estimates)
        brand_price_ranges = {
            "Ski-Doo": {"min": 8000, "max": 25000},
            "Polaris": {"min": 7500, "max": 23000},
            "Arctic Cat": {"min": 7000, "max": 22000},
            "Yamaha": {"min": 8000, "max": 24000},
        }
        
        brand = context.price_entry.brand
        if brand in brand_price_ranges:
            range_info = brand_price_ranges[brand]
            if price < range_info["min"]:
                result["warnings"].append(f"Price seems low for {brand} ({price})")
            elif price > range_info["max"]:
                result["warnings"].append(f"Price seems high for {brand} ({price})")
        
        # Check price vs features
        premium_features = ["turbo", "electronic", "air", "heated"]
        feature_count = sum(
            1 for feature in premium_features 
            if any(feature in str(v).lower() for v in specs.values())
        )
        
        if feature_count >= 3 and price < 15000:
            result["warnings"].append("Many premium features but relatively low price")
        elif feature_count == 0 and price > 18000:
            result["warnings"].append("High price but few premium features detected")
        
        return result

    def _check_spring_options_compatibility(self, context: PipelineContext) -> Dict[str, Any]:
        """Check compatibility of spring options"""
        result = {"warnings": []}
        
        options = context.spring_options
        if not options:
            return result
        
        # Check for conflicting track options
        track_options = [opt for opt in options if "track" in opt.option_type.value.lower()]
        if len(track_options) > 1:
            result["warnings"].append("Multiple track options detected - may be conflicting")
        
        # Check suspension compatibility
        suspension_options = [opt for opt in options if "suspension" in opt.option_type.value.lower()]
        if len(suspension_options) > 1:
            result["warnings"].append("Multiple suspension options detected")
        
        return result

    def _calculate_quality_score(self, *check_results) -> float:
        """Calculate overall quality score from validation checks"""
        total_checks = len(check_results)
        error_count = sum(len(check.get("errors", [])) for check in check_results)
        warning_count = sum(len(check.get("warnings", [])) for check in check_results)
        
        # Start with perfect score
        score = 1.0
        
        # Deduct for errors (more severe)
        score -= (error_count * 0.2)
        
        # Deduct for warnings (less severe)  
        score -= (warning_count * 0.05)
        
        return max(0.0, min(1.0, score))

    def _generate_final_product_specification(
        self, context: PipelineContext
    ) -> ProductSpecification:
        """Generate the final complete product specification"""
        price_entry = context.price_entry
        
        # Merge all specifications
        final_specs = {
            **context.inherited_specs,
            **context.customizations,
        }
        
        # Create product specification
        product_spec = ProductSpecification(
            model_code=price_entry.model_code,
            base_model_id=context.matched_base_model.base_model_id if context.matched_base_model else "UNKNOWN",
            brand=price_entry.brand,
            model_name=f"{price_entry.brand} {price_entry.model_code}",
            model_year=price_entry.model_year,
            price=Decimal(str(price_entry.price)),
            specifications=final_specs,
            spring_options=context.spring_options,
            pipeline_results=context.stage_results,
            overall_confidence=context.current_confidence,  # Will be updated in main function
        )
        
        return product_spec

    def _calculate_final_confidence(
        self, context: PipelineContext, validation_results: Dict[str, Any]
    ) -> float:
        """Calculate final confidence score"""
        # Start with current pipeline confidence
        base_confidence = context.current_confidence
        
        # Adjust based on validation quality
        quality_adjustment = (validation_results["quality_score"] - 0.7) * 0.2
        
        # Penalty for errors
        error_penalty = len(validation_results["errors"]) * 0.1
        
        # Minor penalty for warnings
        warning_penalty = len(validation_results["warnings"]) * 0.02
        
        # Bonus for completeness
        specs_count = len(context.inherited_specs) + len(context.customizations)
        completeness_bonus = min(0.1, specs_count * 0.01)
        
        final_confidence = base_confidence + quality_adjustment + completeness_bonus - error_penalty - warning_penalty
        
        return max(0.0, min(0.95, final_confidence))
