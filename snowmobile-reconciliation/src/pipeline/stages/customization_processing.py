"""
Stage 3: Customization Processing

Analyzes model codes and specifications to detect customizations and variants.
This stage examines the price entry against inherited specifications to identify
model-specific customizations, options, and variant differences.
"""
import re
from typing import Any, Dict, List

from src.models.domain import (
    PipelineConfig,
    PipelineContext,
    ProcessingStage,
)
from src.pipeline.stages.base_stage import BasePipelineStage


class CustomizationProcessingStage(BasePipelineStage):
    """Detects and processes model customizations and variants"""

    def __init__(self, config: PipelineConfig):
        super().__init__(ProcessingStage.CUSTOMIZATION_PROCESSING, config)
        self._initialize_customization_patterns()

    def _initialize_customization_patterns(self):
        """Initialize regex patterns for customization detection"""
        self.engine_patterns = {
            r"600": {"displacement": "600cc", "engine_type": "2-stroke"},
            r"800": {"displacement": "800cc", "engine_type": "2-stroke"},
            r"850": {"displacement": "850cc", "engine_type": "2-stroke"},
            r"900": {"displacement": "900cc", "engine_type": "4-stroke"},
            r"1000": {"displacement": "1000cc", "engine_type": "4-stroke"},
        }
        
        self.track_patterns = {
            r"ST|SPORT": {"track_type": "sport", "track_length": "129"},
            r"TRAIL": {"track_type": "trail", "track_length": "137"},
            r"TOURING": {"track_type": "touring", "track_length": "146"},
            r"MOUNTAIN|MTN": {"track_type": "mountain", "track_length": "155"},
        }
        
        self.feature_patterns = {
            r"EFI": {"fuel_system": "electronic_fuel_injection"},
            r"ETEC": {"fuel_system": "e_tec_direct_injection"},
            r"TURBO": {"forced_induction": "turbocharged"},
            r"ELECTRIC": {"starting": "electric_start"},
            r"REVERSE|REV": {"reverse": "manual_reverse"},
        }

    async def _execute_stage(self, context: PipelineContext) -> Dict[str, Any]:
        """
        Execute customization detection and processing.
        
        Args:
            context: Pipeline context with inherited specifications
            
        Returns:
            Dictionary with detected customizations and confidence
        """
        try:
            price_entry = context.price_entry
            inherited_specs = context.inherited_specs
            
            # Extract customizations from model code
            customizations = self._detect_customizations_from_code(
                price_entry.model_code
            )
            
            # Analyze specification differences
            spec_customizations = self._analyze_specification_differences(
                inherited_specs, customizations
            )
            
            # Detect variant information
            variant_info = self._detect_variant_information(
                price_entry.model_code, price_entry.brand
            )
            
            # Merge all customizations
            final_customizations = {
                **customizations,
                **spec_customizations,
                **variant_info,
            }
            
            # Calculate customization confidence
            customization_confidence = self._calculate_customization_confidence(
                final_customizations, price_entry.model_code
            )
            
            # Update context
            context.customizations = final_customizations
            context.current_confidence = min(
                context.current_confidence, customization_confidence
            )
            
            return {
                "success": True,
                "customizations": final_customizations,
                "confidence": customization_confidence,
                "customization_count": len(final_customizations),
                "variant_detected": len(variant_info) > 0,
                "engine_detected": any("engine" in key for key in final_customizations),
                "track_detected": any("track" in key for key in final_customizations),
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Customization processing failed: {str(e)}",
                "customizations": {},
                "confidence": 0.0,
            }

    def _detect_customizations_from_code(self, model_code: str) -> Dict[str, Any]:
        """Extract customizations from model code patterns"""
        customizations = {}
        code_upper = model_code.upper()
        
        # Detect engine specifications
        for pattern, engine_specs in self.engine_patterns.items():
            if re.search(pattern, code_upper):
                customizations.update(engine_specs)
                break
                
        # Detect track specifications
        for pattern, track_specs in self.track_patterns.items():
            if re.search(pattern, code_upper):
                customizations.update(track_specs)
                break
                
        # Detect feature specifications
        for pattern, feature_specs in self.feature_patterns.items():
            if re.search(pattern, code_upper):
                customizations.update(feature_specs)
                
        return customizations

    def _analyze_specification_differences(
        self, inherited_specs: Dict[str, Any], code_customizations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze differences between inherited specs and detected customizations"""
        spec_customizations = {}
        
        # Override inherited specs with code-detected customizations
        for key, value in code_customizations.items():
            if key in inherited_specs and inherited_specs[key] != value:
                # Mark as customized from base
                spec_customizations[f"{key}_customized"] = True
                spec_customizations[f"{key}_original"] = inherited_specs[key]
                spec_customizations[key] = value
            elif key not in inherited_specs:
                # New specification not in base
                spec_customizations[key] = value
                
        return spec_customizations

    def _detect_variant_information(self, model_code: str, brand: str) -> Dict[str, Any]:
        """Detect variant-specific information"""
        variant_info = {}
        code_upper = model_code.upper()
        
        # Brand-specific variant patterns (check more specific patterns first)
        if brand == "Ski-Doo":
            if re.search(r"RENEGADE", code_upper):
                variant_info.update({
                    "model_line": "Renegade",
                    "category": "crossover",
                    "target_use": "versatile"
                })
            elif re.search(r"SUMMIT", code_upper):
                variant_info.update({
                    "model_line": "Summit",
                    "category": "mountain",
                    "target_use": "deep_snow"
                })
            elif re.search(r"MXZ", code_upper):
                variant_info.update({
                    "model_line": "MXZ",
                    "category": "performance",
                    "target_use": "trail_performance"
                })
                
        elif brand == "Polaris":
            if re.search(r"ASSAULT", code_upper):
                variant_info.update({
                    "model_line": "Assault",
                    "category": "mountain",
                    "target_use": "deep_snow"
                })
            elif re.search(r"SWITCHBACK", code_upper):
                variant_info.update({
                    "model_line": "Switchback",
                    "category": "trail",
                    "target_use": "trail_riding"
                })
                
        # Common variant indicators
        if re.search(r"LT|LIMITED", code_upper):
            variant_info["trim_level"] = "limited"
            variant_info["features_level"] = "premium"
            
        if re.search(r"X|EXTREME", code_upper):
            variant_info["performance_level"] = "extreme"
            variant_info["target_use"] = "high_performance"
            
        return variant_info

    def _calculate_customization_confidence(
        self, customizations: Dict[str, Any], model_code: str
    ) -> float:
        """Calculate confidence in customization detection"""
        base_confidence = 0.7
        
        # Boost confidence based on number of detected customizations
        customization_count = len(customizations)
        if customization_count >= 5:
            confidence_boost = 0.2
        elif customization_count >= 3:
            confidence_boost = 0.1
        elif customization_count >= 1:
            confidence_boost = 0.05
        else:
            confidence_boost = -0.2  # Low confidence if no customizations found
            
        # Boost confidence if engine and track detected (key specifications)
        if any("engine" in key for key in customizations) and \
           any("track" in key for key in customizations):
            confidence_boost += 0.1
            
        # Model code complexity indicates more specific model
        if len(model_code) >= 8:  # Complex model codes are usually more specific
            confidence_boost += 0.05
            
        final_confidence = min(0.95, base_confidence + confidence_boost)
        return max(0.1, final_confidence)
