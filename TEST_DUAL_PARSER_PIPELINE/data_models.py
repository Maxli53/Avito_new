from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

@dataclass
class VehicleSpecifications:
    """Data class for vehicle technical specifications"""
    engine: Optional[str] = None
    engine_family: Optional[str] = None
    displacement_cc: Optional[int] = None
    fuel_system: Optional[str] = None
    track_length_in: Optional[int] = None
    track_length_mm: Optional[int] = None
    track_width_mm: Optional[int] = None
    track_profile_in: Optional[float] = None
    suspension_front: Optional[str] = None
    suspension_rear: Optional[str] = None
    display_type: Optional[str] = None
    display_size: Optional[str] = None
    starter_system: Optional[str] = None
    heating_elements: List[str] = field(default_factory=list)

@dataclass
class MarketingContent:
    """Data class for marketing and promotional content"""
    tagline: Optional[str] = None
    key_benefits: List[str] = field(default_factory=list)
    target_audience: Optional[str] = None
    unique_selling_points: List[str] = field(default_factory=list)
    package_highlights: List[str] = field(default_factory=list)
    features_overview: List[str] = field(default_factory=list)

@dataclass
class ProductImage:
    """Data class for product image information"""
    id: str = field(default_factory=lambda: str(uuid4()))
    vehicle_id: Optional[str] = None
    vehicle_name: Optional[str] = None
    image_filename: Optional[str] = None
    image_path: Optional[str] = None
    page_number: Optional[int] = None
    image_index: int = 0
    width: Optional[int] = None
    height: Optional[int] = None
    image_type: str = "UNKNOWN"  # MAIN_PRODUCT/COLOR_VARIANT/DETAIL/TECHNICAL
    dominant_colors: List[Dict[str, Any]] = field(default_factory=list)
    features_visible: List[str] = field(default_factory=list)
    quality_score: Optional[float] = None
    extraction_timestamp: Optional[datetime] = None
    source_catalog: Optional[str] = None
    extraction_method: str = "automated"

@dataclass
class ColorOption:
    """Data class for vehicle color options"""
    name: str
    hex_code: Optional[str] = None
    availability: List[str] = field(default_factory=list)  # Which models/packages
    spring_only: bool = False
    engine_restrictions: List[str] = field(default_factory=list)
    track_restrictions: List[str] = field(default_factory=list)

@dataclass
class SpringOption:
    """Data class for spring option specifications"""
    color_name: Optional[str] = None
    engine_restriction: Optional[str] = None
    track_length: Optional[str] = None
    description: str = ""
    applies_to_models: List[str] = field(default_factory=list)

@dataclass
class MatchingResult:
    """Data class for matching results between price list and catalog"""
    tier_1_exact_match: bool = False
    tier_1_confidence: float = 0.0
    tier_2_normalized_match: bool = False
    tier_2_confidence: float = 0.0
    tier_2_transformations: Dict[str, Any] = field(default_factory=dict)
    tier_3_fuzzy_match: bool = False
    tier_3_confidence: float = 0.0
    tier_3_algorithms: Dict[str, Any] = field(default_factory=dict)
    final_matching_method: str = ""
    overall_confidence: float = 0.0
    requires_human_review: bool = False
    data_quality_issues: List[str] = field(default_factory=list)
    spring_options_detected: int = 0
    specification_conflicts: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CatalogVehicle:
    """Main data class for catalog vehicle information"""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    model_family: str = ""
    base_model_name: str = ""
    package_name: Optional[str] = None
    page_number: int = 0
    
    # Technical data
    specifications: VehicleSpecifications = field(default_factory=VehicleSpecifications)
    
    # Marketing data
    marketing: MarketingContent = field(default_factory=MarketingContent)
    
    # Visual data
    product_images: List[ProductImage] = field(default_factory=list)
    available_colors: List[ColorOption] = field(default_factory=list)
    spring_options: List[SpringOption] = field(default_factory=list)
    
    # Matching data
    matching_method: Optional[str] = None
    matching_confidence: Optional[float] = None
    confidence_description: Optional[str] = None
    price_list_model_code: Optional[str] = None
    
    # Processing metadata
    extraction_timestamp: Optional[datetime] = None
    source_catalog_name: Optional[str] = None
    source_catalog_page: Optional[int] = None
    extraction_method: str = "automated"
    parser_version: str = "3.0.0"

@dataclass
class PriceListEntry:
    """Data class for Finnish price list entries"""
    id: str = field(default_factory=lambda: str(uuid4()))
    model_code: str = ""
    malli: str = ""  # Finnish model name
    paketti: Optional[str] = None  # Finnish package name
    moottori: Optional[str] = None  # Engine specification
    telamatto: Optional[str] = None  # Track specification
    kaynnistin: Optional[str] = None  # Starting system
    mittaristo: Optional[str] = None  # Instrumentation
    kevatoptiot: Optional[str] = None  # Spring options
    vari: Optional[str] = None  # Color
    price: Optional[float] = None
    currency: str = "EUR"
    
    # Normalized fields for matching
    normalized_model_name: Optional[str] = None
    normalized_package_name: Optional[str] = None
    normalized_engine_spec: Optional[str] = None
    
    # Processing stage
    dual_parser_stage: str = "pending"
    stage_completion_flags: Dict[str, Any] = field(default_factory=dict)
    
    # Spring options
    spring_options_raw: Optional[str] = None
    spring_options_parsed: List[SpringOption] = field(default_factory=list)

@dataclass
class ModelCodeMapping:
    """Data class for Finnish-English model code mappings"""
    id: str = field(default_factory=lambda: str(uuid4()))
    model_code: str = ""  # 4-character Finnish code
    malli: str = ""  # Finnish model name
    paketti: Optional[str] = None  # Finnish package name
    english_model_name: str = ""  # English catalog equivalent
    english_package_name: Optional[str] = None  # English package equivalent
    base_model_id: str = ""  # Reference to catalog entry
    matching_method: str = ""  # exact/normalized/fuzzy/manual
    matching_confidence: float = 0.0
    matching_algorithm_version: str = "1.0"
    created_by: str = "system"
    verification_status: str = "pending"  # pending/verified/disputed
    manual_override: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class PackageDefinition:
    """Data class for package definitions and characteristics"""
    id: str = field(default_factory=lambda: str(uuid4()))
    brand: str = ""
    model_family: str = ""
    package_name: str = ""
    package_code: Optional[str] = None
    model_year: int = 0
    package_type: str = ""  # trim_level/accessory_package/engine_variant
    base_model_indicator: bool = False
    
    # Package modifications from base
    engine_modifications: Dict[str, Any] = field(default_factory=dict)
    suspension_modifications: Dict[str, Any] = field(default_factory=dict)
    track_modifications: Dict[str, Any] = field(default_factory=dict)
    feature_additions: Dict[str, Any] = field(default_factory=dict)
    
    # Language equivalents
    english_equivalents: List[str] = field(default_factory=list)
    finnish_variants: List[str] = field(default_factory=list)
    
    # Quality metadata
    confidence_score: float = 0.85
    human_verified: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class DualParserConfig:
    """Configuration class for dual parser operations"""
    exact_match_threshold: float = 0.95
    normalized_match_threshold: float = 0.85
    fuzzy_match_threshold: float = 0.7
    auto_accept_threshold: float = 0.9
    normalization_rules: Dict[str, Any] = field(default_factory=dict)
    claude_api_config: Dict[str, Any] = field(default_factory=dict)
    image_processing_enabled: bool = False
    max_processing_time_seconds: int = 300

    @classmethod
    def from_database(cls, db_path: str) -> 'DualParserConfig':
        """Load configuration from database"""
        import sqlite3
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT config_key, config_value FROM dual_parser_configuration")
            config_data = dict(cursor.fetchall())
            
            import json
            config = cls()
            
            if 'exact_match_threshold' in config_data:
                config.exact_match_threshold = float(config_data['exact_match_threshold'])
            if 'normalized_match_threshold' in config_data:
                config.normalized_match_threshold = float(config_data['normalized_match_threshold'])
            if 'fuzzy_match_threshold' in config_data:
                config.fuzzy_match_threshold = float(config_data['fuzzy_match_threshold'])
            if 'auto_accept_threshold' in config_data:
                config.auto_accept_threshold = float(config_data['auto_accept_threshold'])
            if 'normalization_rules' in config_data:
                config.normalization_rules = json.loads(config_data['normalization_rules'])
            
            return config
            
        except Exception as e:
            print(f"Error loading config from database: {e}")
            return cls()  # Return default config
        finally:
            conn.close()