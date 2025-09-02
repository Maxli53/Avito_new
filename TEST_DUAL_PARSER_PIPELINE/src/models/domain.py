from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import UUID


class ProcessingStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    EXTRACTED = "extracted"
    MATCHED = "matched"
    COMPLETED = "completed"
    FAILED = "failed"


class ValidationStatus(Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    PUBLISHED = "published"
    REQUIRES_REVIEW = "requires_review"


class JobType(Enum):
    PRICE_EXTRACTION = "price_extraction"
    CATALOG_EXTRACTION = "catalog_extraction"
    PRODUCT_GENERATION = "product_generation"
    BATCH_PROCESSING = "batch_processing"


class JobStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PriceList:
    id: UUID
    filename: str
    brand: str
    market: str
    model_year: int
    total_entries: int = 0
    processed_entries: int = 0
    failed_entries: int = 0
    status: ProcessingStatus = ProcessingStatus.PENDING
    uploaded_at: datetime = None
    processed_at: Optional[datetime] = None


@dataclass
class Catalog:
    id: UUID
    filename: str
    brand: str
    model_year: int
    document_type: str = "product_spec_book"
    language: Optional[str] = None
    total_pages: Optional[int] = None
    total_models_extracted: int = 0
    status: ProcessingStatus = ProcessingStatus.PENDING
    uploaded_at: datetime = None
    processed_at: Optional[datetime] = None


@dataclass
class PriceEntry:
    id: UUID
    price_list_id: UUID
    model_code: str
    malli: str  # Model name in Finnish
    paketti: Optional[str]  # Package in Finnish
    moottori: Optional[str]  # Engine in Finnish
    telamatto: Optional[str]  # Track in Finnish
    kaynnistin: Optional[str]  # Starter in Finnish
    mittaristo: Optional[str]  # Instruments in Finnish
    kevatoptiot: Optional[str]  # Spring options in Finnish
    vari: Optional[str]  # Color in Finnish
    price: Decimal
    currency: str
    market: str
    brand: str
    model_year: int
    catalog_lookup_key: str
    status: ProcessingStatus = ProcessingStatus.EXTRACTED
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.catalog_lookup_key is None:
            self.catalog_lookup_key = self._generate_lookup_key()

    def _generate_lookup_key(self) -> str:
        """Generate deterministic lookup key for catalog matching"""
        paketti_part = self.paketti or ""
        model_part = f"{self.malli}_{paketti_part}".replace(" ", "_")
        return f"{self.brand}_{model_part}_{self.model_year}"


@dataclass
class BaseModel:
    id: UUID
    catalog_id: UUID
    lookup_key: str
    brand: str
    model_family: str
    model_year: int
    engine_options: Optional[Dict[str, Any]] = None
    track_options: Optional[Dict[str, Any]] = None
    suspension_options: Optional[Dict[str, Any]] = None
    starter_options: Optional[Dict[str, Any]] = None
    dimensions: Optional[Dict[str, Any]] = None
    features: Optional[List[str]] = None
    full_specifications: Optional[Dict[str, Any]] = None
    marketing_description: Optional[str] = None
    source_pages: Optional[List[int]] = None
    extraction_confidence: Optional[Decimal] = None
    completeness_score: Optional[Decimal] = None
    created_at: datetime = None
    updated_at: datetime = None


@dataclass
class Product:
    id: UUID
    sku: str
    model_code: str
    brand: str
    model_family: str
    model_year: int
    market: str
    price: Decimal
    currency: str
    price_entry_id: UUID
    base_model_id: UUID
    resolved_specifications: Dict[str, Any]
    inheritance_adjustments: Optional[Dict[str, Any]] = None
    selected_variations: Optional[Dict[str, Any]] = None
    html_content: Optional[str] = None
    html_generated_at: Optional[datetime] = None
    confidence_score: Optional[Decimal] = None
    validation_status: ValidationStatus = ValidationStatus.PENDING
    auto_approved: bool = False
    claude_api_calls: int = 0
    claude_processing_ms: Optional[int] = None
    total_cost_usd: Optional[Decimal] = None
    created_at: datetime = None
    updated_at: datetime = None
    published_at: Optional[datetime] = None


@dataclass
class SpringOption:
    id: UUID
    option_name: str
    brand: Optional[str] = None
    specifications_changes: Optional[Dict[str, Any]] = None
    times_seen: int = 1
    confidence_score: Optional[Decimal] = None
    validated_by_claude: bool = False
    validated_by_human: bool = False
    created_at: datetime = None


@dataclass
class ProcessingJob:
    id: UUID
    job_type: JobType
    price_list_id: Optional[UUID] = None
    catalog_id: Optional[UUID] = None
    status: JobStatus = JobStatus.QUEUED
    progress_percentage: int = 0
    total_items: Optional[int] = None
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    created_at: datetime = None


@dataclass
class InheritanceResult:
    """Result from Claude intelligent inheritance process"""
    specifications: Dict[str, Any]
    html_content: str
    inheritance_adjustments: Dict[str, Any]
    selected_variations: Dict[str, Any]
    confidence_score: Decimal
    reasoning: str
    api_calls_used: int
    processing_time_ms: int
    cost_usd: Decimal


@dataclass
class ExtractionResult:
    """Result from PDF extraction process"""
    success: bool
    entries_extracted: int
    entries_failed: int
    error_message: Optional[str] = None
    confidence_score: Optional[Decimal] = None
    processing_time_ms: Optional[int] = None


@dataclass
class MatchingResult:
    """Result from deterministic matching process"""
    price_entry_id: UUID
    base_model_id: Optional[UUID]
    matched: bool
    confidence_score: Decimal
    match_method: str  # "deterministic", "fuzzy", "manual"
    error_message: Optional[str] = None