"""
Stage 2: Specification Inheritance

Inherits base model specifications and applies model-specific overrides.
This stage takes the matched base model from Stage 1 and creates a complete
specification set by inheriting common specifications and applying model-specific
customizations.
"""
from typing import Any, Dict

from src.models.domain import (
    PipelineConfig,
    PipelineContext,
    ProcessingStage,
)
from src.pipeline.stages.base_stage import BasePipelineStage


class SpecificationInheritanceStage(BasePipelineStage):
    """Inherits specifications from matched base model"""

    def __init__(self, config: PipelineConfig):
        super().__init__(ProcessingStage.SPECIFICATION_INHERITANCE, config)

    async def _execute_stage(self, context: PipelineContext) -> Dict[str, Any]:
        """
        Execute specification inheritance logic.
        
        Args:
            context: Pipeline context with matched base model from Stage 1
            
        Returns:
            Dictionary with inherited specifications and metadata
        """
        try:
            if not context.matched_base_model:
                return {
                    "success": False,
                    "error": "No base model found to inherit specifications from",
                    "inherited_specs": {},
                    "confidence": 0.0,
                }

            base_model = context.matched_base_model
            price_entry = context.price_entry

            # Start with base model specifications - combine all spec fields
            inherited_specs = {}
            inherited_specs.update(base_model.engine_specs)
            inherited_specs.update(base_model.suspension)
            inherited_specs.update(base_model.dimensions)
            inherited_specs.update(base_model.features)
            
            # Apply brand-specific inheritance rules
            inherited_specs = self._apply_brand_inheritance(
                inherited_specs, price_entry.brand
            )
            
            # Apply year-specific updates
            inherited_specs = self._apply_year_updates(
                inherited_specs, price_entry.model_year
            )
            
            # Apply price-tier specific features
            inherited_specs = self._apply_price_tier_features(
                inherited_specs, price_entry.price, price_entry.brand
            )
            
            # Calculate inheritance confidence
            inheritance_confidence = self._calculate_inheritance_confidence(
                base_model, inherited_specs
            )
            
            # Update context with inherited specifications
            context.inherited_specs = inherited_specs
            context.current_confidence = inheritance_confidence
            
            return {
                "success": True,
                "inherited_specs": inherited_specs,
                "confidence": inheritance_confidence,
                "inheritance_rules_applied": len([
                    rule for rule in ["brand", "year", "price_tier"] 
                    if rule in inherited_specs
                ]),
                "base_model_id": base_model.base_model_id,
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Specification inheritance failed: {str(e)}",
                "inherited_specs": {},
                "confidence": 0.0,
            }

    def _apply_brand_inheritance(
        self, specs: Dict[str, Any], brand: str
    ) -> Dict[str, Any]:
        """Apply brand-specific inheritance rules"""
        brand_rules = {
            "Ski-Doo": {
                "suspension": "tMotion",
                "drive_system": "QRS",
                "throttle": "electronic",
            },
            "Polaris": {
                "suspension": "Pro-Ride",
                "drive_system": "Team",
                "throttle": "digital",
            },
            "Arctic Cat": {
                "suspension": "ARS II",
                "drive_system": "TEAM",
                "throttle": "EFI",
            },
            "Yamaha": {
                "suspension": "Dual Shock",
                "drive_system": "YVXC",
                "throttle": "EFI",
            },
        }
        
        if brand in brand_rules:
            brand_specs = brand_rules[brand]
            for key, value in brand_specs.items():
                if key not in specs:  # Only add if not already specified
                    specs[key] = value
                    
        return specs

    def _apply_year_updates(
        self, specs: Dict[str, Any], model_year: int
    ) -> Dict[str, Any]:
        """Apply year-specific technology updates"""
        # Modern features for recent years
        if model_year >= 2023:
            specs.setdefault("display", "digital_gauge")
            specs.setdefault("connectivity", "bluetooth")
            
        if model_year >= 2024:
            specs.setdefault("starting", "electric_start")
            specs.setdefault("warranty", "3_year_extended")
            
        # Legacy adjustments for older models
        if model_year <= 2020:
            specs.pop("connectivity", None)  # Remove if present
            if specs.get("display") == "digital_gauge":
                specs["display"] = "analog_gauge"
                
        return specs

    def _apply_price_tier_features(
        self, specs: Dict[str, Any], price: float, brand: str
    ) -> Dict[str, Any]:
        """Apply features based on price tier"""
        # Premium tier features (high-end models)
        if price >= 18000:
            specs.setdefault("heated_grips", True)
            specs.setdefault("reverse", "electric")
            specs.setdefault("suspension_adjustment", "electronic")
            
        # Mid-tier features  
        elif price >= 12000:
            specs.setdefault("heated_grips", True)
            specs.setdefault("reverse", "manual")
            specs.setdefault("suspension_adjustment", "manual")
            
        # Entry-level tier
        else:
            specs.setdefault("heated_grips", False)
            specs.setdefault("reverse", False)
            specs.setdefault("suspension_adjustment", "fixed")
            
        return specs

    def _calculate_inheritance_confidence(
        self, base_model: Any, inherited_specs: Dict[str, Any]
    ) -> float:
        """Calculate confidence in inheritance accuracy"""
        base_confidence = base_model.inheritance_confidence
        
        # Number of specifications inherited
        specs_count = len(inherited_specs)
        
        # Confidence boost based on specification completeness
        completeness_bonus = min(0.2, specs_count * 0.02)
        
        # Penalty if very few specs inherited
        if specs_count < 5:
            completeness_bonus = -0.1
            
        final_confidence = min(0.95, base_confidence + completeness_bonus)
        return max(0.0, final_confidence)
