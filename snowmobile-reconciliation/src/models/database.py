"""
SQLAlchemy database models for PostgreSQL with JSONB support.

Implements the database schema following Universal Development Standards
with proper indexing, constraints, and audit trails.
"""
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.models.domain import ConfidenceLevel, ProcessingStage, SpringOptionType

Base = declarative_base()


class ProductTable(Base):
    """Main products table with complete specifications and audit trail"""

    __tablename__ = "products"

    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_code = Column(String(50), nullable=False, index=True)
    base_model_id = Column(String(100), nullable=False, index=True)

    # Basic product information
    brand = Column(String(50), nullable=False, index=True)
    model_name = Column(String(200), nullable=False)
    model_year = Column(Integer, nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="EUR")

    # Complete specifications as JSONB for flexibility and performance
    specifications = Column(JSONB, nullable=False, default={})
    spring_options = Column(JSONB, nullable=False, default=[])
    pipeline_results = Column(JSONB, nullable=False, default=[])

    # Confidence scoring
    overall_confidence = Column(Numeric(3, 2), nullable=False, default=0.0, index=True)
    confidence_level = Column(
        Enum(ConfidenceLevel), nullable=False, default=ConfidenceLevel.LOW, index=True
    )

    # Processing metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_by = Column(String(100), nullable=False, default="system")
    processing_version = Column(String(20), default="1.0")

    # Source tracking
    source_file = Column(String(500))
    source_page = Column(Integer)
    extraction_confidence = Column(Numeric(3, 2))

    # Relationships
    audit_trails = relationship("AuditTrailTable", back_populates="product")

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "model_code", "model_year", "brand", name="uq_product_identity"
        ),
        Index("idx_products_confidence_created", "confidence_level", "created_at"),
        Index("idx_products_brand_year", "brand", "model_year"),
        Index(
            "idx_products_specifications_gin", "specifications", postgresql_using="gin"
        ),
        Index(
            "idx_products_spring_options_gin", "spring_options", postgresql_using="gin"
        ),
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, model_code='{self.model_code}', brand='{self.brand}')>"


class BaseModelTable(Base):
    """Catalog base models with complete specifications"""

    __tablename__ = "base_models"

    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    base_model_id = Column(String(100), nullable=False, unique=True, index=True)

    # Basic model information
    model_name = Column(String(200), nullable=False)
    brand = Column(String(50), nullable=False, index=True)
    model_year = Column(Integer, nullable=False, index=True)
    category = Column(
        String(50), nullable=False, index=True
    )  # Trail, Crossover, Summit, etc.

    # Technical specifications stored as JSONB
    engine_specs = Column(JSONB, nullable=False, default={})
    dimensions = Column(JSONB, nullable=False, default={})
    suspension = Column(JSONB, nullable=False, default={})
    features = Column(JSONB, nullable=False, default={})
    available_colors = Column(JSONB, nullable=False, default=[])
    track_options = Column(JSONB, nullable=False, default=[])

    # Catalog metadata
    source_catalog = Column(String(500), nullable=False)
    extraction_quality = Column(Numeric(3, 2), nullable=False, default=0.0)
    last_updated = Column(DateTime(timezone=True), nullable=False, default=func.now())

    # Full-text search support
    search_vector = Column(String, nullable=True)  # Computed search vector

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("base_model_id", "model_year", name="uq_base_model_year"),
        Index("idx_base_models_brand_year_category", "brand", "model_year", "category"),
        Index(
            "idx_base_models_engine_specs_gin", "engine_specs", postgresql_using="gin"
        ),
        Index("idx_base_models_features_gin", "features", postgresql_using="gin"),
        Index("idx_base_models_search_gin", "search_vector", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<BaseModel(id='{self.base_model_id}', name='{self.model_name}', brand='{self.brand}')>"


class AuditTrailTable(Base):
    """Complete audit trail for processing transparency"""

    __tablename__ = "audit_trails"

    # Primary key
    audit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Related product
    product_id = Column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )

    # Processing stage information
    stage = Column(Enum(ProcessingStage), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)

    # Data changes tracking
    before_data = Column(JSONB)
    after_data = Column(JSONB)
    confidence_change = Column(Numeric(3, 2))

    # Metadata
    timestamp = Column(
        DateTime(timezone=True), nullable=False, default=func.now(), index=True
    )
    processing_node = Column(String(100), nullable=False, default="unknown")
    user_id = Column(String(100))

    # Performance tracking
    processing_time_ms = Column(Integer)
    memory_usage_mb = Column(Numeric(8, 2))

    # API usage tracking
    claude_tokens_used = Column(Integer, default=0)
    claude_api_cost = Column(Numeric(8, 4), default=0.0)

    # Relationships
    product = relationship("ProductTable", back_populates="audit_trails")

    # Constraints and indexes
    __table_args__ = (
        Index("idx_audit_trails_product_stage", "product_id", "stage"),
        Index("idx_audit_trails_timestamp", "timestamp"),
        Index("idx_audit_trails_action", "action"),
        Index(
            "idx_audit_trails_before_data_gin", "before_data", postgresql_using="gin"
        ),
        Index("idx_audit_trails_after_data_gin", "after_data", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<AuditTrail(product_id={self.product_id}, stage={self.stage}, action='{self.action}')>"


class ProcessingBatchTable(Base):
    """Batch processing tracking for monitoring and recovery"""

    __tablename__ = "processing_batches"

    # Primary key
    batch_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Batch information
    batch_name = Column(String(200), nullable=False)
    source_file = Column(String(500), nullable=False)
    total_entries = Column(Integer, nullable=False, default=0)

    # Processing status
    status = Column(String(50), nullable=False, default="pending", index=True)
    started_at = Column(DateTime(timezone=True), default=func.now())
    completed_at = Column(DateTime(timezone=True))

    # Results tracking
    successful_entries = Column(Integer, nullable=False, default=0)
    failed_entries = Column(Integer, nullable=False, default=0)
    skipped_entries = Column(Integer, nullable=False, default=0)

    # Performance metrics
    total_processing_time_ms = Column(BigInteger, default=0)
    average_processing_time_ms = Column(Integer, default=0)
    peak_memory_usage_mb = Column(Numeric(8, 2))

    # API usage tracking
    total_claude_tokens = Column(BigInteger, default=0)
    total_claude_cost = Column(Numeric(10, 4), default=0.0)

    # Error tracking
    error_summary = Column(JSONB, default={})

    # Configuration used
    pipeline_config = Column(JSONB, default={})

    # Constraints and indexes
    __table_args__ = (
        Index("idx_processing_batches_status_started", "status", "started_at"),
        Index("idx_processing_batches_source_file", "source_file"),
        Index("idx_processing_batches_completed", "completed_at"),
    )

    def __repr__(self) -> str:
        return f"<ProcessingBatch(id={self.batch_id}, name='{self.batch_name}', status='{self.status}')>"


class SpringOptionTable(Base):
    """Specialized table for spring options analysis and tracking"""

    __tablename__ = "spring_options"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Related product
    product_id = Column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )

    # Spring option details
    option_type = Column(Enum(SpringOptionType), nullable=False, index=True)
    description = Column(Text, nullable=False)
    technical_details = Column(JSONB, nullable=False, default={})

    # Detection metadata
    detection_method = Column(String(100), nullable=False, index=True)
    confidence = Column(Numeric(3, 2), nullable=False, default=0.0)
    source_text = Column(Text)
    claude_reasoning = Column(Text)

    # Validation status
    human_verified = Column(Boolean, default=False, index=True)
    verified_by = Column(String(100))
    verified_at = Column(DateTime(timezone=True))
    verification_notes = Column(Text)

    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    product = relationship("ProductTable")

    # Constraints and indexes
    __table_args__ = (
        Index("idx_spring_options_product_type", "product_id", "option_type"),
        Index("idx_spring_options_detection_method", "detection_method"),
        Index("idx_spring_options_confidence", "confidence"),
        Index("idx_spring_options_verified", "human_verified"),
        Index(
            "idx_spring_options_technical_details_gin",
            "technical_details",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        return f"<SpringOption(product_id={self.product_id}, type={self.option_type}, confidence={self.confidence})>"


class SystemConfigTable(Base):
    """System configuration and feature flags"""

    __tablename__ = "system_config"

    # Primary key
    config_key = Column(String(100), primary_key=True)

    # Configuration value
    config_value = Column(JSONB, nullable=False)
    value_type = Column(
        String(50), nullable=False
    )  # string, integer, float, boolean, json

    # Metadata
    description = Column(Text)
    category = Column(String(50), nullable=False, default="general", index=True)
    is_sensitive = Column(Boolean, nullable=False, default=False)

    # Change tracking
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(100))

    # Validation
    validation_schema = Column(JSONB)  # JSON schema for value validation

    # Constraints and indexes
    __table_args__ = (
        Index("idx_system_config_category", "category"),
        Index("idx_system_config_updated", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<SystemConfig(key='{self.config_key}', category='{self.category}')>"


class PerformanceMetricsTable(Base):
    """Performance metrics tracking for monitoring and optimization"""

    __tablename__ = "performance_metrics"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Metric identification
    metric_name = Column(String(100), nullable=False, index=True)
    metric_category = Column(String(50), nullable=False, index=True)

    # Metric value and context
    metric_value = Column(Numeric(12, 4), nullable=False)
    metric_unit = Column(String(20), nullable=False)
    context_data = Column(JSONB, default={})

    # Processing context
    pipeline_stage = Column(Enum(ProcessingStage), index=True)
    batch_id = Column(
        UUID(as_uuid=True), ForeignKey("processing_batches.batch_id"), index=True
    )
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), index=True)

    # Timestamp
    recorded_at = Column(
        DateTime(timezone=True), nullable=False, default=func.now(), index=True
    )

    # System context
    processing_node = Column(String(100), nullable=False, default="unknown")
    system_load = Column(Numeric(5, 2))
    memory_available_mb = Column(BigInteger)

    # Constraints and indexes
    __table_args__ = (
        Index("idx_performance_metrics_name_recorded", "metric_name", "recorded_at"),
        Index(
            "idx_performance_metrics_category_stage",
            "metric_category",
            "pipeline_stage",
        ),
        Index(
            "idx_performance_metrics_context_gin",
            "context_data",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        return f"<PerformanceMetric(name='{self.metric_name}', value={self.metric_value}, unit='{self.metric_unit}')>"


# Database utility functions


def create_indexes(engine) -> None:
    """Create additional indexes for performance optimization"""
    with engine.connect() as conn:
        # Full-text search indexes
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_products_fulltext
            ON products USING gin(to_tsvector('english', model_name || ' ' || model_code))
        """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_base_models_fulltext
            ON base_models USING gin(to_tsvector('english', model_name || ' ' || base_model_id))
        """
        )

        # Partial indexes for active data
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_products_active_high_confidence
            ON products (created_at)
            WHERE confidence_level = 'high' AND created_at > NOW() - INTERVAL '30 days'
        """
        )

        # Composite indexes for common queries
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_products_brand_year_confidence
            ON products (brand, model_year, confidence_level, overall_confidence DESC)
        """
        )


def create_functions(engine) -> None:
    """Create PostgreSQL functions for advanced queries"""
    with engine.connect() as conn:
        # Function for calculating confidence score distribution
        conn.execute(
            """
            CREATE OR REPLACE FUNCTION get_confidence_distribution(brand_filter TEXT DEFAULT NULL)
            RETURNS TABLE(confidence_range TEXT, product_count BIGINT)
            AS $$
            BEGIN
                RETURN QUERY
                SELECT
                    CASE
                        WHEN overall_confidence >= 0.9 THEN 'high (>=0.9)'
                        WHEN overall_confidence >= 0.7 THEN 'medium (0.7-0.89)'
                        ELSE 'low (<0.7)'
                    END as confidence_range,
                    COUNT(*) as product_count
                FROM products
                WHERE (brand_filter IS NULL OR brand = brand_filter)
                GROUP BY confidence_range
                ORDER BY confidence_range;
            END;
            $$ LANGUAGE plpgsql;
        """
        )

        # Function for spring options analysis
        conn.execute(
            """
            CREATE OR REPLACE FUNCTION get_spring_options_stats()
            RETURNS TABLE(option_type TEXT, total_count BIGINT, verified_count BIGINT, avg_confidence NUMERIC)
            AS $$
            BEGIN
                RETURN QUERY
                SELECT
                    so.option_type::TEXT,
                    COUNT(*) as total_count,
                    COUNT(*) FILTER (WHERE so.human_verified = true) as verified_count,
                    AVG(so.confidence) as avg_confidence
                FROM spring_options so
                GROUP BY so.option_type
                ORDER BY total_count DESC;
            END;
            $$ LANGUAGE plpgsql;
        """
        )


# Export all models for easy importing
__all__ = [
    "Base",
    "ProductTable",
    "BaseModelTable",
    "AuditTrailTable",
    "ProcessingBatchTable",
    "SpringOptionTable",
    "SystemConfigTable",
    "PerformanceMetricsTable",
    "create_indexes",
    "create_functions",
]
