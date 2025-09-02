"""
Core Data Models for Avito Pipeline
Defines the fundamental data structures used throughout the pipeline stages
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum


class PipelineStage(Enum):
    """Pipeline stage enumeration"""
    EXTRACTION = "extraction"
    MATCHING = "matching"
    VALIDATION = "validation"
    GENERATION = "generation"
    UPLOAD = "upload"


class MatchType(Enum):
    """Type of matching performed"""
    EXACT = "exact"
    BERT_SEMANTIC = "bert_semantic"
    FUZZY = "fuzzy"
    CLAUDE_INHERITANCE = "claude_inheritance"


class ValidationLevel(Enum):
    """Validation severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ProductData:
    """
    Core product data structure extracted from price lists
    
    Attributes:
        model_code: Unique product identifier (e.g., 'TJTH', 'FVTA')
        brand: Manufacturer brand ('LYNX', 'SKI-DOO')
        year: Model year
        malli: Finnish model name
        paketti: Package/trim level
        moottori: Engine specification
        telamatto: Track specification
        kaynnistin: Starter type
        mittaristo: Gauge/display specification
        vari: Color specification
        price: Price in original currency
        currency: Price currency ('EUR', 'RUB')
        market: Target market ('FINLAND', 'RUSSIA')
        extraction_metadata: Metadata about extraction process
    """
    
    model_code: str
    brand: str
    year: int
    malli: Optional[str] = None
    paketti: Optional[str] = None
    moottori: Optional[str] = None
    telamatto: Optional[str] = None
    kaynnistin: Optional[str] = None
    mittaristo: Optional[str] = None
    vari: Optional[str] = None
    price: Optional[float] = None
    currency: str = 'EUR'
    market: str = 'FINLAND'
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize data after initialization"""
        if not self.model_code or len(self.model_code) != 4:
            raise ValueError(f"model_code must be 4 characters, got: {self.model_code}")
        
        if self.year and (self.year < 2015 or self.year > 2030):
            raise ValueError(f"Invalid year: {self.year}")
        
        # Normalize brand name
        if self.brand:
            self.brand = self.brand.upper().replace('SKI-DOO', 'SKI-DOO')
    
    @property
    def full_model_name(self) -> str:
        """Generate full model name for display"""
        parts = [self.brand]
        if self.malli:
            parts.append(self.malli)
        if self.paketti:
            parts.append(self.paketti)
        return ' '.join(parts)
    
    @property
    def display_price(self) -> str:
        """Format price for display"""
        if self.price:
            if self.currency == 'EUR':
                return f"{self.price:,.2f}€"
            elif self.currency == 'RUB':
                return f"{self.price:,.0f}₽"
        return "Price not available"


@dataclass
class CatalogData:
    """
    Catalog specification data from product specification books
    
    Attributes:
        model_family: Base model family name
        specifications: Technical specifications
        features: Product features list
        available_engines: Available engine options
        available_tracks: Available track configurations
        marketing_data: Marketing information
        images: Product images metadata
        extraction_metadata: Metadata about extraction process
    """
    
    model_family: str
    specifications: Dict[str, Any] = field(default_factory=dict)
    features: List[str] = field(default_factory=list)
    available_engines: List[str] = field(default_factory=list)
    available_tracks: List[str] = field(default_factory=list)
    marketing_data: Dict[str, Any] = field(default_factory=dict)
    images: List[Dict[str, Any]] = field(default_factory=list)
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def matches_product(self, product: ProductData) -> bool:
        """Check if this catalog entry matches a product"""
        if not product.malli:
            return False
        
        return (
            product.malli.upper() in self.model_family.upper() or
            self.model_family.upper() in product.malli.upper()
        )


@dataclass 
class ValidationResult:
    """
    Result of validation process
    
    Attributes:
        success: Whether validation passed
        errors: List of error messages
        warnings: List of warning messages
        suggestions: List of improvement suggestions
        confidence: Confidence score (0.0 - 1.0)
        metadata: Additional validation metadata
    """
    
    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, message: str, level: ValidationLevel = ValidationLevel.ERROR):
        """Add validation error"""
        if level == ValidationLevel.ERROR:
            self.errors.append(message)
            self.success = False
        elif level == ValidationLevel.WARNING:
            self.warnings.append(message)
        
    def add_suggestion(self, message: str):
        """Add improvement suggestion"""
        self.suggestions.append(message)
    
    @property
    def has_issues(self) -> bool:
        """Check if validation has any issues"""
        return bool(self.errors or self.warnings)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'success': self.success,
            'errors': self.errors,
            'warnings': self.warnings,
            'suggestions': self.suggestions,
            'confidence': self.confidence,
            'metadata': self.metadata
        }


@dataclass
class MatchResult:
    """
    Result of matching process between price list and catalog data
    
    Attributes:
        product_data: Source product data
        catalog_data: Matched catalog data (if found)
        match_type: Type of matching used
        confidence_score: Matching confidence (0.0 - 1.0)
        matched: Whether matching was successful
        match_details: Detailed matching information
        processing_time: Time taken for matching
    """
    
    product_data: ProductData
    catalog_data: Optional[CatalogData] = None
    match_type: MatchType = MatchType.EXACT
    confidence_score: float = 0.0
    matched: bool = False
    match_details: Dict[str, Any] = field(default_factory=dict)
    processing_time: Optional[float] = None
    
    def __post_init__(self):
        """Set matched flag based on catalog_data presence"""
        self.matched = self.catalog_data is not None
    
    @property
    def confidence_level(self) -> str:
        """Get confidence level as string"""
        if self.confidence_score >= 0.9:
            return "HIGH"
        elif self.confidence_score >= 0.7:
            return "MEDIUM" 
        elif self.confidence_score >= 0.5:
            return "LOW"
        else:
            return "VERY_LOW"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'product_code': self.product_data.model_code,
            'matched': self.matched,
            'match_type': self.match_type.value,
            'confidence_score': self.confidence_score,
            'confidence_level': self.confidence_level,
            'match_details': self.match_details,
            'processing_time': self.processing_time
        }


@dataclass
class PipelineStats:
    """
    Pipeline execution statistics
    
    Attributes:
        stage: Pipeline stage
        total_processed: Total items processed
        successful: Successfully processed items
        failed: Failed items
        processing_time: Total processing time
        start_time: Processing start time
        end_time: Processing end time
        metadata: Additional statistics
    """
    
    stage: PipelineStage
    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    processing_time: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_processed == 0:
            return 0.0
        return (self.successful / self.total_processed) * 100
    
    @property 
    def failure_rate(self) -> float:
        """Calculate failure rate percentage"""
        return 100.0 - self.success_rate
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'stage': self.stage.value,
            'total_processed': self.total_processed,
            'successful': self.successful,
            'failed': self.failed,
            'success_rate': self.success_rate,
            'processing_time': self.processing_time,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'metadata': self.metadata
        }


@dataclass
class AvitoXMLData:
    """
    Data structure for Avito XML generation
    
    Attributes:
        id: Unique product ID
        title: Product title
        category: Avito category
        vehicle_type: Vehicle type
        price: Price in rubles
        description: Product description
        images: List of image URLs
        address: Location address
        model: BRP model name
        make: Manufacturer
        technical_specs: Technical specifications dict
        metadata: Additional XML metadata
    """
    
    id: str
    title: str
    category: str = 'Мотоциклы и мототехника'
    vehicle_type: str = 'Снегоходы'
    price: Optional[int] = None
    description: Optional[str] = None
    images: List[str] = field(default_factory=list)
    address: str = 'Санкт-Петербург'
    model: Optional[str] = None
    make: str = 'BRP'
    technical_specs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate_required_fields(self) -> ValidationResult:
        """Validate required Avito fields"""
        result = ValidationResult(success=True)
        
        required_fields = ['id', 'title', 'category', 'vehicle_type', 'price', 'description', 'images']
        
        for field in required_fields:
            value = getattr(self, field, None)
            if not value:
                result.add_error(f"Required field '{field}' is missing or empty")
        
        # Validate price range
        if self.price and (self.price < 100000 or self.price > 10000000):
            result.add_error(f"Price {self.price} is outside valid range (100,000 - 10,000,000 RUB)")
        
        # Validate images
        if not self.images:
            result.add_error("At least one image URL is required")
        
        return result