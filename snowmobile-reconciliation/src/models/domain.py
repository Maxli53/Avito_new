"""
Core domain models for snowmobile product reconciliation system.

All business data structures using Pydantic for validation and serialization.
Follows Universal Development Standards - NO dataclasses allowed.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, validator


class ProcessingStage(str, Enum):
    """5-stage inheritance pipeline stages"""

    BASE_MODEL_MATCHING = "base_model_matching"
    SPECIFICATION_INHERITANCE = "specification_inheritance"
    CUSTOMIZATION_PROCESSING = "customization_processing"
    SPRING_OPTIONS_ENHANCEMENT = "spring_options_enhancement"
    FINAL_VALIDATION = "final_validation"


class ConfidenceLevel(str, Enum):
    """Confidence levels for automated processing"""

    HIGH = "high"  # ≥0.9 - Auto-accept
    MEDIUM = "medium"  # 0.7-0.89 - Review recommended
    LOW = "low"  # <0.7 - Manual review required


class SpringOptionType(str, Enum):
    """Types of spring option modifications"""

    TRACK_UPGRADE = "track_upgrade"
    COLOR_CHANGE = "color_change"
    SUSPENSION_UPGRADE = "suspension_upgrade"
    FEATURE_ADDITION = "feature_addition"


# ============================================================================
# Price List Models (Input from PDFs)
# ============================================================================


class PriceEntry(BaseModel):
    """Raw price entry extracted from Finnish price lists"""

    model_code: str = Field(
        ..., description="Model code from price list (e.g., 'LTTA')"
    )
    brand: str = Field(..., description="Brand (Ski-Doo, Lynx, Sea-Doo)")
    model_name: Optional[str] = Field(None, description="Model name if available")
    price: Decimal = Field(..., ge=0, description="Price in original currency")
    currency: str = Field(default="EUR", description="Price currency")
    market: str = Field(default="FI", description="Market code (FI, SE, NO, DK)")
    model_year: int = Field(..., ge=2020, le=2030, description="Model year")

    # Processing metadata
    source_file: str = Field(..., description="Source PDF filename")
    page_number: int = Field(..., ge=1, description="Page number in PDF")
    extraction_confidence: float = Field(
        ge=0.0, le=1.0, description="PDF extraction quality"
    )

    class Config:
        str_strip_whitespace = True
        validate_assignment = True


# ============================================================================
# Base Model Catalog Models
# ============================================================================


class BaseModelSpecification(BaseModel):
    """Complete base model specifications from product catalogs"""

    base_model_id: str = Field(..., description="Base model identifier")
    model_name: str = Field(..., description="Full model name")
    brand: str = Field(..., description="Brand")
    model_year: int = Field(..., description="Model year")
    category: str = Field(..., description="Product category (Trail, Crossover, etc.)")

    # Technical specifications (JSONB in database)
    engine_specs: dict[str, Any] = Field(default_factory=dict)
    dimensions: dict[str, Any] = Field(default_factory=dict)
    suspension: dict[str, Any] = Field(default_factory=dict)
    features: dict[str, Any] = Field(default_factory=dict)
    available_colors: list[str] = Field(default_factory=list)
    track_options: list[dict[str, Any]] = Field(default_factory=list)

    # Processing metadata
    source_catalog: str = Field(..., description="Source catalog file")
    extraction_quality: float = Field(
        ge=0.0, le=1.0, description="Catalog extraction quality"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("base_model_id")
    @classmethod
    def validate_base_model_id(cls, v: str) -> str:
        """Ensure base model ID follows naming convention"""
        if not v or len(v) < 2:
            raise ValueError("Base model ID must be at least 2 characters")
        return v.upper().strip()


# ============================================================================
# Pipeline Processing Models
# ============================================================================


class PipelineContext(BaseModel):
    """Context passed between pipeline stages"""

    # Current processing data
    price_entry: PriceEntry = Field(..., description="Entry being processed")
    matched_base_model: Optional["BaseModelSpecification"] = Field(
        None, description="Base model matched in stage 1"
    )
    inherited_specs: dict[str, Any] = Field(
        default_factory=dict, description="Inherited specifications"
    )
    customizations: dict[str, Any] = Field(
        default_factory=dict, description="Applied customizations"
    )
    spring_options: list["SpringOption"] = Field(
        default_factory=list, description="Detected spring options"
    )

    # Processing metadata
    processing_id: UUID = Field(default_factory=uuid4)
    stage_results: list["PipelineStageResult"] = Field(default_factory=list)
    current_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class PipelineStageResult(BaseModel):
    """Result from individual pipeline stage processing"""

    stage: ProcessingStage
    success: bool = Field(..., description="Stage completed successfully")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Stage confidence")
    processing_time_ms: int = Field(ge=0, description="Processing time in milliseconds")

    # Stage-specific data
    stage_data: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    # Claude API usage (if applicable)
    claude_tokens_used: Optional[int] = Field(None, ge=0)
    claude_api_cost: Optional[Decimal] = Field(None, ge=0)


class SpringOption(BaseModel):
    """Detected spring option modification"""

    option_type: SpringOptionType
    description: str = Field(..., description="Human-readable description")
    technical_details: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, description="Detection confidence")

    # Detection metadata
    detection_method: str = Field(..., description="How option was detected")
    source_text: Optional[str] = Field(None, description="Source text if text-based")
    claude_reasoning: Optional[str] = Field(None, description="Claude's analysis")


class ProductSpecification(BaseModel):
    """Complete product specification after pipeline processing"""

    # Identifiers
    product_id: UUID = Field(default_factory=uuid4)
    model_code: str = Field(..., description="Original model code from price list")
    base_model_id: str = Field(..., description="Matched base model")

    # Basic product info
    brand: str = Field(..., description="Product brand")
    model_name: str = Field(..., description="Full model name")
    model_year: int = Field(..., description="Model year")
    price: Decimal = Field(..., ge=0, description="Final price")
    currency: str = Field(default="EUR")

    # Complete specifications (inherited + customized)
    specifications: dict[str, Any] = Field(default_factory=dict)
    spring_options: list[SpringOption] = Field(default_factory=list)

    # Processing audit trail
    pipeline_results: list[PipelineStageResult] = Field(default_factory=list)
    overall_confidence: float = Field(
        ge=0.0, le=1.0, description="Final confidence score"
    )
    confidence_level: Optional[ConfidenceLevel] = Field(
        None, description="Confidence classification"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_by: str = Field(default="system", description="Processing system/user")

    @field_validator("confidence_level", mode="before")
    @classmethod
    def set_confidence_level(
        cls, v: Optional[ConfidenceLevel]
    ) -> Optional[ConfidenceLevel]:
        """Auto-determine confidence level from overall confidence score"""
        return v  # Will be set in model_post_init
    
    def model_post_init(self, __context) -> None:
        """Auto-calculate confidence level after model initialization"""
        if self.confidence_level is None:
            if self.overall_confidence >= 0.9:
                self.confidence_level = ConfidenceLevel.HIGH
            elif self.overall_confidence >= 0.7:
                self.confidence_level = ConfidenceLevel.MEDIUM
            else:
                self.confidence_level = ConfidenceLevel.LOW


# ============================================================================
# Processing Configuration Models
# ============================================================================


class ClaudeConfig(BaseModel):
    """Claude API configuration for pipeline processing"""

    model: str = Field(
        default="claude-3-haiku-20240307", description="Claude model to use"
    )
    max_tokens: int = Field(default=4000, ge=100, le=8000)
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    batch_size: int = Field(default=5, ge=1, le=10, description="Products per API call")
    timeout_seconds: int = Field(default=30, ge=5, le=120)
    max_retries: int = Field(default=3, ge=0, le=5)


class PipelineConfig(BaseModel):
    """Overall pipeline processing configuration"""

    # Processing thresholds
    auto_accept_threshold: float = Field(default=0.9, ge=0.5, le=1.0)
    manual_review_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    # Performance settings
    max_concurrent_processing: int = Field(default=10, ge=1, le=50)
    enable_parallel_stages: bool = Field(default=True)

    # Feature flags
    enable_spring_options: bool = Field(default=True)
    enable_claude_fallback: bool = Field(default=True)
    enable_confidence_tuning: bool = Field(default=True)

    # API configurations
    claude_config: ClaudeConfig = Field(default_factory=ClaudeConfig)


# ============================================================================
# API Response Models
# ============================================================================


class ProcessingRequest(BaseModel):
    """Request to process price list entries through pipeline"""

    price_entries: list[PriceEntry] = Field(..., min_items=1, max_items=1000)
    config_override: Optional[PipelineConfig] = Field(
        None, description="Override default config"
    )
    priority: int = Field(default=5, ge=1, le=10, description="Processing priority")
    callback_url: Optional[str] = Field(
        None, description="Webhook for completion notification"
    )


class ProcessingResponse(BaseModel):
    """Response from pipeline processing"""

    request_id: UUID = Field(default_factory=uuid4)
    status: str = Field(..., description="Processing status")
    products_processed: int = Field(ge=0)
    products_successful: int = Field(ge=0)
    products_failed: int = Field(ge=0)

    # Results
    products: list[ProductSpecification] = Field(default_factory=list)
    processing_errors: list[str] = Field(default_factory=list)

    # Performance metrics
    total_processing_time_ms: int = Field(ge=0)
    claude_tokens_total: int = Field(ge=0)
    claude_cost_total: Decimal = Field(ge=0)

    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Database Models (for SQLAlchemy integration)
# ============================================================================


class AuditTrail(BaseModel):
    """Audit trail entry for processing transparency"""

    audit_id: UUID = Field(default_factory=uuid4)
    product_id: UUID = Field(..., description="Related product ID")
    stage: ProcessingStage = Field(..., description="Pipeline stage")
    action: str = Field(..., description="Action performed")

    # Data changes
    before_data: Optional[dict[str, Any]] = Field(
        None, description="Data before change"
    )
    after_data: Optional[dict[str, Any]] = Field(None, description="Data after change")
    confidence_change: Optional[float] = Field(
        None, description="Confidence score change"
    )

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_node: str = Field(
        default="unknown", description="Processing node/worker"
    )
    user_id: Optional[str] = Field(None, description="User if manual action")


# ============================================================================
# Error and Exception Models
# ============================================================================


class ProcessingError(BaseModel):
    """Structured error information for processing failures"""

    error_type: str = Field(..., description="Error type/category")
    error_message: str = Field(..., description="Human-readable error message")
    error_code: str = Field(..., description="System error code")

    # Context
    stage: Optional[ProcessingStage] = Field(
        None, description="Pipeline stage where error occurred"
    )
    model_code: Optional[str] = Field(None, description="Model code being processed")
    technical_details: dict[str, Any] = Field(default_factory=dict)

    # Recovery suggestions
    recovery_suggestion: Optional[str] = Field(
        None, description="Suggested recovery action"
    )
    retry_recommended: bool = Field(
        default=False, description="Whether retry might succeed"
    )

    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Export for easy importing
# ============================================================================

__all__ = [
    # Enums
    "ProcessingStage",
    "ConfidenceLevel",
    "SpringOptionType",
    # Core models
    "PriceEntry",
    "BaseModelSpecification",
    "ProductSpecification",
    "SpringOption",
    # Pipeline models
    "PipelineStageResult",
    "PipelineConfig",
    "ClaudeConfig",
    # API models
    "ProcessingRequest",
    "ProcessingResponse",
    # Support models
    "AuditTrail",
    "ProcessingError",
]
