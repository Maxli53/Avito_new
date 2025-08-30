"""
Stage 4: Spring Options Enhancement

Detects and processes spring-specific options and modifications.
This stage analyzes customizations and model specifications to identify
spring-related options like track upgrades, suspension modifications,
and seasonal accessories.
"""
import re
from typing import Any, Dict, List

from src.models.domain import (
    PipelineConfig,
    PipelineContext,
    ProcessingStage,
    SpringOption,
    SpringOptionType,
)
from src.pipeline.stages.base_stage import BasePipelineStage


class SpringOptionsEnhancementStage(BasePipelineStage):
    """Detects and enhances spring-specific options and modifications"""

    def __init__(self, config: PipelineConfig):
        super().__init__(ProcessingStage.SPRING_OPTIONS_ENHANCEMENT, config)
        self._initialize_spring_patterns()

    def _initialize_spring_patterns(self):
        """Initialize patterns for spring option detection"""
        self.track_upgrade_patterns = {
            r"COBRA|CAMSO": {
                "type": SpringOptionType.TRACK_UPGRADE,
                "description": "Cobra track upgrade",
                "confidence": 0.9,
            },
            r"RIPSAW": {
                "type": SpringOptionType.TRACK_UPGRADE,
                "description": "Ripsaw aggressive track",
                "confidence": 0.85,
            },
            r"POWER_CLAW": {
                "type": SpringOptionType.TRACK_UPGRADE,
                "description": "Power Claw deep snow track",
                "confidence": 0.8,
            },
        }
        
        self.suspension_upgrades = {
            r"AIR_RIDE|AIR": {
                "type": SpringOptionType.SUSPENSION_UPGRADE,
                "description": "Air ride suspension upgrade",
                "confidence": 0.9,
            },
            r"WALKER_EVANS": {
                "type": SpringOptionType.SUSPENSION_UPGRADE,
                "description": "Walker Evans shock upgrade",
                "confidence": 0.85,
            },
            r"FOX": {
                "type": SpringOptionType.SUSPENSION_UPGRADE,
                "description": "Fox Racing shock upgrade",
                "confidence": 0.8,
            },
        }
        
        self.accessory_patterns = {
            r"HEATED.*SEAT": {
                "type": SpringOptionType.COMFORT_UPGRADE,
                "description": "Heated seat option",
                "confidence": 0.9,
            },
            r"WINDSHIELD": {
                "type": SpringOptionType.WEATHER_PROTECTION,
                "description": "Windshield upgrade",
                "confidence": 0.8,
            },
            r"STORAGE|TUNNEL_BAG": {
                "type": SpringOptionType.STORAGE_UPGRADE,
                "description": "Storage upgrade",
                "confidence": 0.7,
            },
        }

    async def _execute_stage(self, context: PipelineContext) -> Dict[str, Any]:
        """
        Execute spring options detection and enhancement.
        
        Args:
            context: Pipeline context with customizations from Stage 3
            
        Returns:
            Dictionary with detected spring options and confidence
        """
        try:
            price_entry = context.price_entry
            customizations = context.customizations
            
            # Detect spring options from model code
            spring_options = self._detect_spring_options_from_code(
                price_entry.model_code
            )
            
            # Analyze customizations for spring options
            customization_options = self._analyze_customizations_for_spring_options(
                customizations
            )
            
            # Detect seasonal/usage-specific options
            seasonal_options = self._detect_seasonal_options(
                price_entry, customizations
            )
            
            # Merge all spring options
            all_spring_options = spring_options + customization_options + seasonal_options
            
            # Remove duplicates and rank by confidence
            final_spring_options = self._deduplicate_and_rank_options(all_spring_options)
            
            # Calculate stage confidence
            spring_options_confidence = self._calculate_spring_options_confidence(
                final_spring_options, customizations
            )
            
            # Update context
            context.spring_options = final_spring_options
            context.current_confidence = min(
                context.current_confidence, spring_options_confidence
            )
            
            return {
                "success": True,
                "spring_options": [opt.model_dump() for opt in final_spring_options],
                "confidence": spring_options_confidence,
                "options_count": len(final_spring_options),
                "track_upgrades": len([opt for opt in final_spring_options 
                                    if opt.option_type == SpringOptionType.TRACK_UPGRADE]),
                "suspension_upgrades": len([opt for opt in final_spring_options 
                                         if opt.option_type == SpringOptionType.SUSPENSION_UPGRADE]),
                "comfort_upgrades": len([opt for opt in final_spring_options 
                                       if opt.option_type == SpringOptionType.COMFORT_UPGRADE]),
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Spring options enhancement failed: {str(e)}",
                "spring_options": [],
                "confidence": 0.0,
            }

    def _detect_spring_options_from_code(self, model_code: str) -> List[SpringOption]:
        """Detect spring options directly from model code patterns"""
        options = []
        code_upper = model_code.upper()
        
        # Check track upgrade patterns
        for pattern, config in self.track_upgrade_patterns.items():
            if re.search(pattern, code_upper):
                options.append(SpringOption(
                    option_type=config["type"],
                    description=config["description"],
                    confidence=config["confidence"],
                    detection_method="model_code_pattern",
                    source_text=model_code,
                ))
                
        # Check suspension upgrade patterns
        for pattern, config in self.suspension_upgrades.items():
            if re.search(pattern, code_upper):
                options.append(SpringOption(
                    option_type=config["type"],
                    description=config["description"],
                    confidence=config["confidence"],
                    detection_method="model_code_pattern",
                    source_text=model_code,
                ))
                
        # Check accessory patterns
        for pattern, config in self.accessory_patterns.items():
            if re.search(pattern, code_upper):
                options.append(SpringOption(
                    option_type=config["type"],
                    description=config["description"],
                    confidence=config["confidence"],
                    detection_method="model_code_pattern",
                    source_text=model_code,
                ))
                
        return options

    def _analyze_customizations_for_spring_options(
        self, customizations: Dict[str, Any]
    ) -> List[SpringOption]:
        """Analyze customizations to infer spring options"""
        options = []
        
        # Track-related customizations suggest track options
        if customizations.get("track_type") == "mountain":
            options.append(SpringOption(
                option_type=SpringOptionType.TRACK_UPGRADE,
                description="Mountain track configuration",
                confidence=0.7,
                detection_method="customization_analysis",
                technical_details={"track_type": customizations.get("track_type")},
            ))
            
        # Suspension-related customizations
        if customizations.get("suspension_adjustment") == "electronic":
            options.append(SpringOption(
                option_type=SpringOptionType.SUSPENSION_UPGRADE,
                description="Electronic suspension adjustment",
                confidence=0.8,
                detection_method="customization_analysis",
                technical_details={"adjustment_type": "electronic"},
            ))
            
        # Premium features suggest comfort upgrades
        if customizations.get("features_level") == "premium":
            options.append(SpringOption(
                option_type=SpringOptionType.COMFORT_UPGRADE,
                description="Premium comfort package",
                confidence=0.6,
                detection_method="customization_analysis",
                technical_details={"package_level": "premium"},
            ))
            
        return options

    def _detect_seasonal_options(
        self, price_entry: Any, customizations: Dict[str, Any]
    ) -> List[SpringOption]:
        """Detect seasonal/usage-specific options"""
        options = []
        
        # High-performance models likely have performance options
        if customizations.get("performance_level") == "extreme":
            options.append(SpringOption(
                option_type=SpringOptionType.PERFORMANCE_UPGRADE,
                description="Extreme performance package",
                confidence=0.7,
                detection_method="seasonal_analysis",
                technical_details={"performance_tier": "extreme"},
            ))
            
        # Mountain/deep snow categories suggest winter options
        if customizations.get("target_use") == "deep_snow":
            options.append(SpringOption(
                option_type=SpringOptionType.WEATHER_PROTECTION,
                description="Deep snow configuration",
                confidence=0.8,
                detection_method="seasonal_analysis",
                technical_details={"snow_condition": "deep"},
            ))
            
        # Premium price tier suggests luxury options
        if float(price_entry.price) >= 18000:
            options.append(SpringOption(
                option_type=SpringOptionType.COMFORT_UPGRADE,
                description="Luxury comfort features",
                confidence=0.6,
                detection_method="price_tier_analysis",
                technical_details={"price_tier": "premium"},
            ))
            
        return options

    def _deduplicate_and_rank_options(
        self, options: List[SpringOption]
    ) -> List[SpringOption]:
        """Remove duplicates and rank options by confidence"""
        # Group by description to remove duplicates
        unique_options = {}
        
        for option in options:
            key = (option.option_type, option.description.lower())
            if key not in unique_options or option.confidence > unique_options[key].confidence:
                unique_options[key] = option
                
        # Sort by confidence (highest first)
        sorted_options = sorted(
            unique_options.values(),
            key=lambda x: x.confidence,
            reverse=True
        )
        
        return sorted_options

    def _calculate_spring_options_confidence(
        self, spring_options: List[SpringOption], customizations: Dict[str, Any]
    ) -> float:
        """Calculate overall confidence for spring options detection"""
        if not spring_options:
            return 0.5  # Neutral confidence if no options detected
            
        # Average confidence of detected options
        avg_option_confidence = sum(opt.confidence for opt in spring_options) / len(spring_options)
        
        # Boost confidence based on number of customizations
        customization_boost = min(0.2, len(customizations) * 0.02)
        
        # Boost confidence if multiple option types detected
        option_types = len(set(opt.option_type for opt in spring_options))
        type_diversity_boost = min(0.1, option_types * 0.03)
        
        final_confidence = min(0.95, avg_option_confidence + customization_boost + type_diversity_boost)
        return max(0.1, final_confidence)
