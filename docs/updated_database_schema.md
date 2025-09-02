-- =============================================================================
-- SNOWMOBILE PRODUCT DATA RECONCILIATION SYSTEM
-- Complete Database Schema - Enhanced Inheritance Pipeline
-- =============================================================================

-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Products Table - Final constructed products with complete specifications
-- -----------------------------------------------------------------------------
CREATE TABLE products (
    -- Primary Keys and Identity
    sku VARCHAR(20) PRIMARY KEY,
    internal_id UUID DEFAULT uuid_generate_v4() NOT NULL,
    
    -- Product Identity
    brand VARCHAR(50) NOT NULL,              -- 'Ski-Doo', 'Lynx', 'Sea-Doo'
    model_year INTEGER NOT NULL CHECK (model_year >= 2020 AND model_year <= 2030),
    model_family VARCHAR(100),               -- 'Rave RE', 'MXZ X-RS', 'Summit X'
    base_model_source VARCHAR(200),          -- Source base model used for inheritance
    platform VARCHAR(50),                   -- 'REV Gen5', 'Radien²', 'SHOT'
    category VARCHAR(50),                    -- 'Trail', 'Deep Snow', 'Crossover'
    
    -- Key Searchable Specifications
    engine_model VARCHAR(100),
    engine_displacement_cc INTEGER CHECK (engine_displacement_cc > 0),
    track_length_mm INTEGER CHECK (track_length_mm > 0),
    track_width_mm INTEGER CHECK (track_width_mm > 0),
    track_profile_mm INTEGER CHECK (track_profile_mm > 0),
    dry_weight_kg INTEGER CHECK (dry_weight_kg > 0),
    
    -- Complete Specifications (JSONB for flexibility)
    full_specifications JSONB NOT NULL DEFAULT '{}',
    marketing_texts JSONB DEFAULT '{}',      -- Multi-language content
    spring_modifications JSONB DEFAULT '{}', -- Applied spring options
    
    -- Quality and Validation
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    validation_status VARCHAR(20) DEFAULT 'pending' CHECK (validation_status IN ('pending', 'passed', 'failed', 'requires_review')),
    auto_accepted BOOLEAN DEFAULT FALSE,
    
    -- Audit and Tracking
    inheritance_audit_trail JSONB DEFAULT '{}', -- Complete processing history
    raw_sources JSONB DEFAULT '[]',         -- Source attribution
    processing_metadata JSONB DEFAULT '{}', -- Pipeline processing details
    
    -- Standard Audit Fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    
    -- Soft Delete Support
    deleted_at TIMESTAMP,
    deleted_by VARCHAR(100)
);

-- -----------------------------------------------------------------------------
-- Base Models Catalog Table - Stores catalog base models for inheritance
-- -----------------------------------------------------------------------------
CREATE TABLE base_models_catalog (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Base Model Identity
    brand VARCHAR(50) NOT NULL,              -- Ski-Doo, Lynx, Sea-Doo
    model_family VARCHAR(100) NOT NULL,      -- "Rave RE", "MXZ X-RS"
    model_year INTEGER NOT NULL CHECK (model_year >= 2020 AND model_year <= 2030),
    lookup_key VARCHAR(200) NOT NULL UNIQUE, -- "Lynx_Rave_RE_2026"
    
    -- Complete Base Specifications
    platform_specs JSONB NOT NULL DEFAULT '{}',      -- Fixed platform details
    engine_options JSONB NOT NULL DEFAULT '{}',      -- Available engines
    track_options JSONB NOT NULL DEFAULT '{}',       -- Available tracks
    suspension_specs JSONB NOT NULL DEFAULT '{}',    -- Suspension details
    feature_options JSONB NOT NULL DEFAULT '{}',     -- Available features
    color_options JSONB NOT NULL DEFAULT '{}',       -- Available colors
    
    -- Standard Specifications
    dimensions JSONB NOT NULL DEFAULT '{}',          -- Length, width, height
    weight_specifications JSONB NOT NULL DEFAULT '{}', -- Weight ranges
    standard_features JSONB NOT NULL DEFAULT '{}',   -- Included features
    
    -- Quality and Validation
    catalog_completeness_score DECIMAL(3,2) DEFAULT 0.00,
    validation_status VARCHAR(20) DEFAULT 'pending',
    
    -- Source Tracking
    catalog_source VARCHAR(255),             -- Source document
    catalog_page INTEGER,                    -- Page in catalog
    extraction_date TIMESTAMP,              -- When extracted
    extraction_confidence DECIMAL(3,2),     -- Extraction quality
    
    -- Standard Audit Fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    
    -- Soft Delete Support
    deleted_at TIMESTAMP,
    deleted_by VARCHAR(100),
    
    -- Business Logic Constraints
    UNIQUE (brand, model_family, model_year)
);

-- -----------------------------------------------------------------------------
-- Price Lists Table - Master table for uploaded price list documents
-- -----------------------------------------------------------------------------
CREATE TABLE price_lists (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Price List Identity
    filename VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) NOT NULL UNIQUE,   -- SHA-256 for deduplication
    market VARCHAR(10) NOT NULL,             -- FI, SE, NO, DK
    brand VARCHAR(50) NOT NULL,              -- Ski-Doo, Lynx, Sea-Doo
    model_year INTEGER NOT NULL CHECK (model_year >= 2020 AND model_year <= 2030),
    currency VARCHAR(3) NOT NULL,            -- EUR, SEK, NOK, DKK
    
    -- Document Processing
    document_type VARCHAR(50) DEFAULT 'price_list',
    document_quality VARCHAR(20) DEFAULT 'unknown' CHECK (document_quality IN ('digital_high', 'digital_medium', 'scanned_good', 'scanned_poor', 'corrupted', 'unknown')),
    parser_used VARCHAR(50),                 -- PyMuPDF, Camelot, Claude_OCR
    extraction_method VARCHAR(50),           -- direct, ocr, hybrid
    
    -- Processing Status
    processing_status VARCHAR(20) DEFAULT 'uploaded' CHECK (processing_status IN ('uploaded', 'processing', 'completed', 'failed', 'requires_review')),
    total_entries INTEGER DEFAULT 0,
    processed_entries INTEGER DEFAULT 0,
    failed_entries INTEGER DEFAULT 0,
    
    -- Metadata
    file_size_bytes BIGINT,
    total_pages INTEGER,
    upload_source VARCHAR(100),              -- manual, api, scheduled
    
    -- Processing Metrics
    processing_start_time TIMESTAMP,
    processing_end_time TIMESTAMP,
    processing_duration_ms INTEGER,
    claude_api_calls INTEGER DEFAULT 0,
    total_cost_usd DECIMAL(10,4) DEFAULT 0.00,
    
    -- Standard Audit Fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    
    -- Soft Delete Support
    deleted_at TIMESTAMP,
    deleted_by VARCHAR(100)
);

-- -----------------------------------------------------------------------------
-- Price Entries Table - Individual entries from price lists
-- -----------------------------------------------------------------------------
CREATE TABLE price_entries (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    price_list_id UUID NOT NULL,
    
    -- Original Price List Data (Finnish format)
    model_code VARCHAR(50) NOT NULL,         -- Tuote-nro: LTTA, MVTL, UJTU
    malli VARCHAR(100),                      -- Rave, MXZ, Summit
    paketti VARCHAR(100),                    -- RE, X-RS, X
    moottori VARCHAR(100),                   -- 600R E-TEC, 850 E-TEC
    telamatto VARCHAR(100),                  -- 129in/3300mm, 137in/3500mm
    kaynnistin VARCHAR(50),                  -- Manual, Electric
    mittaristo VARCHAR(100),                 -- 7.2 in. Digital Display
    kevätoptiot TEXT,                        -- Spring options text
    vari VARCHAR(100),                       -- Color specification
    
    -- Pricing Information
    price_amount DECIMAL(10,2) NOT NULL CHECK (price_amount >= 0),
    currency VARCHAR(3) NOT NULL,            -- EUR, SEK, NOK, DKK
    market VARCHAR(10) NOT NULL,             -- FI, SE, NO, DK
    
    -- Processing Status and Quality
    processed BOOLEAN DEFAULT FALSE,         -- Has been through pipeline
    processing_error TEXT,                   -- Error message if failed
    mapped_product_sku VARCHAR(20),          -- Link to final product
    confidence_score DECIMAL(3,2),          -- Processing confidence
    requires_manual_review BOOLEAN DEFAULT FALSE,
    
    -- Pipeline Processing Tracking
    stage_1_completed BOOLEAN DEFAULT FALSE, -- Base model matching
    stage_2_completed BOOLEAN DEFAULT FALSE, -- Specification inheritance
    stage_3_completed BOOLEAN DEFAULT FALSE, -- Variant selection
    stage_4_completed BOOLEAN DEFAULT FALSE, -- Spring options
    stage_5_completed BOOLEAN DEFAULT FALSE, -- Final validation
    
    -- Metadata
    source_file VARCHAR(255),                -- Original PDF filename
    source_page INTEGER,                     -- Page number in PDF
    extraction_confidence DECIMAL(3,2),     -- PDF extraction quality
    extraction_method VARCHAR(50),          -- Parser method used
    
    -- Processing Metrics
    processing_start_time TIMESTAMP,
    processing_end_time TIMESTAMP,
    processing_duration_ms INTEGER,
    claude_api_calls INTEGER DEFAULT 0,
    
    -- Standard Audit Fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    
    -- Soft Delete Support
    deleted_at TIMESTAMP,
    deleted_by VARCHAR(100),
    
    -- Foreign Key Constraints
    FOREIGN KEY (price_list_id) REFERENCES price_lists(id) ON DELETE CASCADE,
    FOREIGN KEY (mapped_product_sku) REFERENCES products(sku) ON DELETE SET NULL
);

-- -----------------------------------------------------------------------------
-- Model Mappings Table - Tracks inheritance pipeline from codes to products
-- -----------------------------------------------------------------------------
CREATE TABLE model_mappings (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Model Code Processing
    model_code VARCHAR(50) NOT NULL,         -- Original: LTTA, MVTL, UJTU
    catalog_sku VARCHAR(20) NOT NULL,        -- Final product SKU
    base_model_id UUID,                      -- Reference to base model used
    brand VARCHAR(50) NOT NULL,              -- Detected brand
    model_family VARCHAR(100) NOT NULL,      -- Extracted: "Rave RE", "MXZ X-RS"
    
    -- Inheritance Chain Details
    base_model_matched VARCHAR(200) NOT NULL, -- Base model used for inheritance
    processing_method VARCHAR(50) NOT NULL,   -- 'exact_lookup', 'claude_semantic'
    confidence_score DECIMAL(3,2) NOT NULL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    
    -- Pipeline Stage Results (detailed tracking)
    stage_1_result JSONB DEFAULT '{}',       -- Base model matching details
    stage_2_result JSONB DEFAULT '{}',       -- Inheritance details
    stage_3_result JSONB DEFAULT '{}',       -- Variant selection details
    stage_4_result JSONB DEFAULT '{}',       -- Spring options details
    stage_5_result JSONB DEFAULT '{}',       -- Validation details
    
    -- Quality and Decision Tracking
    auto_accepted BOOLEAN DEFAULT FALSE,      -- Confidence ≥0.95
    requires_review BOOLEAN DEFAULT FALSE,    -- System-detected issues
    validation_passed BOOLEAN DEFAULT TRUE,   -- All validations successful
    manual_override BOOLEAN DEFAULT FALSE,    -- Human intervention applied
    override_reason TEXT,                     -- Reason for manual override
    
    -- Performance Metrics
    complete_audit_trail JSONB DEFAULT '{}', -- Full processing audit
    processing_duration_ms INTEGER,          -- Total pipeline time
    claude_api_calls INTEGER DEFAULT 0,      -- API usage tracking
    total_cost_usd DECIMAL(10,4) DEFAULT 0.00, -- Processing cost
    
    -- Standard Audit Fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    
    -- Soft Delete Support
    deleted_at TIMESTAMP,
    deleted_by VARCHAR(100),
    
    -- Foreign Key Constraints
    FOREIGN KEY (catalog_sku) REFERENCES products(sku) ON DELETE CASCADE,
    FOREIGN KEY (base_model_id) REFERENCES base_models_catalog(id) ON DELETE SET NULL,
    
    -- Business Logic Constraints
    UNIQUE (model_code, brand, model_family, model_year)
);

-- -----------------------------------------------------------------------------
-- Spring Options Registry - Knowledge base of spring options
-- -----------------------------------------------------------------------------
CREATE TABLE spring_options_registry (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Spring Option Identity
    brand VARCHAR(50) NOT NULL,
    model_family VARCHAR(100),               -- NULL = applies to all models
    model_year INTEGER CHECK (model_year >= 2020 AND model_year <= 2030), -- NULL = applies to all years
    option_name VARCHAR(200) NOT NULL,       -- "Black edition", "Studded Track"
    option_code VARCHAR(50),                 -- Internal option code if available
    
    -- Option Details
    option_type VARCHAR(50) NOT NULL CHECK (option_type IN ('color', 'track', 'suspension', 'gauge', 'starter', 'feature_package', 'accessory')),
    description TEXT,                        -- Human-readable description
    specifications JSONB NOT NULL DEFAULT '{}', -- Technical modifications
    
    -- Application Rules
    applies_to_models JSONB DEFAULT '[]',    -- Specific model codes if limited
    conflicts_with JSONB DEFAULT '[]',       -- Incompatible options
    requires_options JSONB DEFAULT '[]',     -- Prerequisite options
    
    -- Pricing Impact
    price_modifier_type VARCHAR(20) DEFAULT 'none' CHECK (price_modifier_type IN ('none', 'add', 'multiply', 'replace')),
    price_modifier_value DECIMAL(10,2) DEFAULT 0.00,
    
    -- Quality and Validation
    confidence_score DECIMAL(3,2) DEFAULT 0.95 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    source VARCHAR(255),                     -- Where this was learned
    validated_by_claude BOOLEAN DEFAULT FALSE, -- AI validation status
    validated_by_human BOOLEAN DEFAULT FALSE,  -- Human validation status
    
    -- Usage Tracking
    times_applied INTEGER DEFAULT 0,        -- How often this option is used
    success_rate DECIMAL(3,2) DEFAULT 1.00, -- Success rate when applied
    
    -- Standard Audit Fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    
    -- Soft Delete Support
    deleted_at TIMESTAMP,
    deleted_by VARCHAR(100),
    
    -- Business Logic Constraints
    UNIQUE (brand, option_name, model_year)
);

-- =============================================================================
-- CONFIGURATION AND LEARNING TABLES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Parser Configurations - Intelligent parser configuration management
-- -----------------------------------------------------------------------------
CREATE TABLE parser_configurations (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Configuration Identity
    brand VARCHAR(50) NOT NULL,
    market VARCHAR(10) NOT NULL,             -- FI, SE, NO, DK
    document_type VARCHAR(50) NOT NULL,      -- price_list, catalog, specification
    model_year INTEGER CHECK (model_year >= 2020 AND model_year <= 2030),
    
    -- Parser Selection Rules
    quality_threshold_digital DECIMAL(3,2) DEFAULT 0.95,
    quality_threshold_scanned DECIMAL(3,2) DEFAULT 0.80,
    preferred_parser VARCHAR(50) NOT NULL,   -- PyMuPDF, Camelot, Claude_OCR
    fallback_parsers JSONB DEFAULT '[]',     -- Ordered fallback list
    
    -- Field Mapping Configuration
    field_mappings JSONB NOT NULL DEFAULT '{}', -- Column name mappings
    field_validation_rules JSONB DEFAULT '{}',  -- Field validation patterns
    extraction_patterns JSONB DEFAULT '{}',     -- Regex patterns for extraction
    
    -- Learning Configuration
    learning_enabled BOOLEAN DEFAULT TRUE,
    auto_update_mappings BOOLEAN DEFAULT TRUE,
    confidence_threshold_learning DECIMAL(3,2) DEFAULT 0.90,
    
    -- Performance Metrics
    success_rate DECIMAL(3,2) DEFAULT 0.00,
    average_confidence DECIMAL(3,2) DEFAULT 0.00,
    total_documents_processed INTEGER DEFAULT 0,
    last_success_date TIMESTAMP,
    
    -- Standard Audit Fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    
    -- Soft Delete Support
    deleted_at TIMESTAMP,
    deleted_by VARCHAR(100),
    
    -- Business Logic Constraints
    UNIQUE (brand, market, document_type, model_year)
);

-- -----------------------------------------------------------------------------
-- Field Discovery Log - Dynamic field discovery and classification
-- -----------------------------------------------------------------------------
CREATE TABLE field_discovery_log (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Discovery Context
    price_list_id UUID NOT NULL,
    discovered_field_name VARCHAR(200) NOT NULL,
    discovered_field_value TEXT,
    
    -- Classification Results
    field_type VARCHAR(50),                  -- engine, track, feature, color, etc.
    classification_confidence DECIMAL(3,2),
    classification_method VARCHAR(50),       -- claude_analysis, pattern_match, manual
    
    -- Learning Status
    learning_status VARCHAR(20) DEFAULT 'discovered' CHECK (learning_status IN ('discovered', 'classified', 'validated', 'integrated', 'rejected')),
    integration_target VARCHAR(100),         -- Which system field this maps to
    
    -- Validation
    validated_by_claude BOOLEAN DEFAULT FALSE,
    validated_by_human BOOLEAN DEFAULT FALSE,
    validation_notes TEXT,
    
    -- Standard Audit Fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    
    -- Foreign Key Constraints
    FOREIGN KEY (price_list_id) REFERENCES price_lists(id) ON DELETE CASCADE
);

-- =============================================================================
-- PROCESSING AND QUALITY TABLES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Processing Jobs - Track long-running processing operations
-- -----------------------------------------------------------------------------
CREATE TABLE processing_jobs (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Job Identity
    job_type VARCHAR(50) NOT NULL,           -- inheritance_pipeline, bulk_update, export
    job_name VARCHAR(200),                   -- Human-readable job name
    price_list_id UUID,                      -- Associated price list if applicable
    
    -- Job Configuration
    job_parameters JSONB DEFAULT '{}',       -- Job-specific parameters
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    
    -- Status Tracking
    status VARCHAR(20) DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
    progress_percentage INTEGER DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    current_stage VARCHAR(100),              -- Current processing stage
    
    -- Results and Metrics
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    successful_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    
    -- Error Tracking
    error_message TEXT,
    error_details JSONB DEFAULT '{}',
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Performance Metrics
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_ms INTEGER,
    claude_api_calls INTEGER DEFAULT 0,
    total_cost_usd DECIMAL(10,4) DEFAULT 0.00,
    
    -- Standard Audit Fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    
    -- Foreign Key Constraints
    FOREIGN KEY (price_list_id) REFERENCES price_lists(id) ON DELETE SET NULL
);

-- -----------------------------------------------------------------------------
-- Quality Metrics - System performance and quality tracking
-- -----------------------------------------------------------------------------
CREATE TABLE quality_metrics (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Metric Identity
    metric_type VARCHAR(50) NOT NULL,        -- confidence_accuracy, processing_speed, claude_cost
    metric_name VARCHAR(100) NOT NULL,       -- Human-readable metric name
    measurement_period VARCHAR(20) NOT NULL, -- daily, weekly, monthly
    
    -- Measurement Details
    measured_value DECIMAL(10,4) NOT NULL,
    target_value DECIMAL(10,4),
    threshold_min DECIMAL(10,4),
    threshold_max DECIMAL(10,4),
    
    -- Context
    brand VARCHAR(50),                       -- Brand-specific metrics
    market VARCHAR(10),                      -- Market-specific metrics
    model_year INTEGER,                      -- Year-specific metrics
    
    -- Metadata
    measurement_date DATE NOT NULL,
    sample_size INTEGER,
    calculation_method VARCHAR(100),
    additional_context JSONB DEFAULT '{}',
    
    -- Standard Audit Fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);

-- =============================================================================
-- PERFORMANCE INDEXES
-- =============================================================================

-- Products Table Indexes
CREATE INDEX idx_products_brand_year ON products(brand, model_year) WHERE deleted_at IS NULL;
CREATE INDEX idx_products_model_family ON products(model_family) WHERE deleted_at IS NULL;
CREATE INDEX idx_products_category ON products(category) WHERE deleted_at IS NULL;
CREATE INDEX idx_products_confidence ON products(confidence_score DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_products_validation_status ON products(validation_status) WHERE deleted_at IS NULL;
CREATE INDEX idx_products_created_at ON products(created_at DESC);
CREATE INDEX idx_products_updated_at ON products(updated_at DESC);

-- JSONB GIN Indexes for Products
CREATE INDEX idx_products_specs_gin ON products USING GIN (full_specifications) WHERE deleted_at IS NULL;
CREATE INDEX idx_products_marketing_gin ON products USING GIN (marketing_texts) WHERE deleted_at IS NULL;
CREATE INDEX idx_products_spring_gin ON products USING GIN (spring_modifications) WHERE deleted_at IS NULL;
CREATE INDEX idx_products_audit_gin ON products USING GIN (inheritance_audit_trail) WHERE deleted_at IS NULL;

-- Specialized JSONB Path Indexes for Products
CREATE INDEX idx_products_specs_engine ON products USING GIN ((full_specifications->'engine')) WHERE deleted_at IS NULL;
CREATE INDEX idx_products_specs_track ON products USING GIN ((full_specifications->'track')) WHERE deleted_at IS NULL;
CREATE INDEX idx_products_specs_suspension ON products USING GIN ((full_specifications->'suspension')) WHERE deleted_at IS NULL;

-- Base Models Catalog Indexes
CREATE INDEX idx_base_models_lookup ON base_models_catalog(lookup_key) WHERE deleted_at IS NULL;
CREATE INDEX idx_base_models_brand_family ON base_models_catalog(brand, model_family, model_year) WHERE deleted_at IS NULL;
CREATE INDEX idx_base_models_brand ON base_models_catalog(brand) WHERE deleted_at IS NULL;
CREATE INDEX idx_base_models_completeness ON base_models_catalog(catalog_completeness_score DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_base_models_created_at ON base_models_catalog(created_at DESC);

-- JSONB Indexes for Base Models
CREATE INDEX idx_base_models_platform_gin ON base_models_catalog USING GIN (platform_specs) WHERE deleted_at IS NULL;
CREATE INDEX idx_base_models_engines_gin ON base_models_catalog USING GIN (engine_options) WHERE deleted_at IS NULL;
CREATE INDEX idx_base_models_tracks_gin ON base_models_catalog USING GIN (track_options) WHERE deleted_at IS NULL;

-- Price Lists Indexes
CREATE INDEX idx_price_lists_market_year ON price_lists(market, model_year, brand) WHERE deleted_at IS NULL;
CREATE INDEX idx_price_lists_status ON price_lists(processing_status) WHERE deleted_at IS NULL;
CREATE INDEX idx_price_lists_created_at ON price_lists(created_at DESC);
CREATE INDEX idx_price_lists_file_hash ON price_lists(file_hash) WHERE deleted_at IS NULL;

-- Price Entries Indexes
CREATE INDEX idx_price_entries_list_id ON price_entries(price_list_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_price_entries_model_code ON price_entries(model_code) WHERE deleted_at IS NULL;
CREATE INDEX idx_price_entries_processed ON price_entries(processed, created_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_price_entries_market_brand ON price_entries(market, price_list_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_price_entries_confidence ON price_entries(confidence_score DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_price_entries_review ON price_entries(requires_manual_review) WHERE requires_manual_review = TRUE AND deleted_at IS NULL;
CREATE INDEX idx_price_entries_pipeline_stages ON price_entries(stage_1_completed, stage_2_completed, stage_3_completed, stage_4_completed, stage_5_completed) WHERE deleted_at IS NULL;

-- Model Mappings Indexes
CREATE INDEX idx_model_mappings_code ON model_mappings(model_code) WHERE deleted_at IS NULL;
CREATE INDEX idx_model_mappings_sku ON model_mappings(catalog_sku) WHERE deleted_at IS NULL;
CREATE INDEX idx_model_mappings_brand_family ON model_mappings(brand, model_family) WHERE deleted_at IS NULL;
CREATE INDEX idx_model_mappings_confidence ON model_mappings(confidence_score DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_model_mappings_method ON model_mappings(processing_method) WHERE deleted_at IS NULL;
CREATE INDEX idx_model_mappings_auto_accepted ON model_mappings(auto_accepted) WHERE deleted_at IS NULL;
CREATE INDEX idx_model_mappings_requires_review ON model_mappings(requires_review) WHERE requires_review = TRUE AND deleted_at IS NULL;

-- JSONB Indexes for Model Mappings
CREATE INDEX idx_mappings_stage1_gin ON model_mappings USING GIN (stage_1_result) WHERE deleted_at IS NULL;
CREATE INDEX idx_mappings_stage4_gin ON model_mappings USING GIN (stage_4_result) WHERE deleted_at IS NULL;
CREATE INDEX idx_mappings_audit_gin ON model_mappings USING GIN (complete_audit_trail) WHERE deleted_at IS NULL;

-- Spring Options Registry Indexes
CREATE INDEX idx_spring_options_brand ON spring_options_registry(brand, option_name) WHERE deleted_at IS NULL;
CREATE INDEX idx_spring_options_type ON spring_options_registry(option_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_spring_options_confidence ON spring_options_registry(confidence_score DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_spring_options_validated ON spring_options_registry(validated_by_claude, validated_by_human) WHERE deleted_at IS NULL;

-- Parser Configurations Indexes
CREATE INDEX idx_parser_configs_brand_market ON parser_configurations(brand, market, document_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_parser_configs_success_rate ON parser_configurations(success_rate DESC) WHERE deleted_at IS NULL;

-- Field Discovery Log Indexes
CREATE INDEX idx_field_discovery_list_id ON field_discovery_log(price_list_id);
CREATE INDEX idx_field_discovery_status ON field_discovery_log(learning_status);
CREATE INDEX idx_field_discovery_field_name ON field_discovery_log(discovered_field_name) WHERE learning_status != 'rejected';

-- Processing Jobs Indexes
CREATE INDEX idx_processing_jobs_status ON processing_jobs(status, priority DESC) WHERE status IN ('queued', 'running');
CREATE INDEX idx_processing_jobs_type ON processing_jobs(job_type, created_at DESC);
CREATE INDEX idx_processing_jobs_created_at ON processing_jobs(created_at DESC);

-- Quality Metrics Indexes
CREATE INDEX idx_quality_metrics_type_date ON quality_metrics(metric_type, measurement_date DESC);
CREATE INDEX idx_quality_metrics_brand_market ON quality_metrics(brand, market, measurement_date DESC) WHERE brand IS NOT NULL AND market IS NOT NULL;

-- =============================================================================
-- TRIGGERS AND AUTOMATION
-- =============================================================================

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers to all tables
CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_base_models_updated_at BEFORE UPDATE ON base_models_catalog FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_price_lists_updated_at BEFORE UPDATE ON price_lists FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_price_entries_updated_at BEFORE UPDATE ON price_entries FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_model_mappings_updated_at BEFORE UPDATE ON model_mappings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_spring_options_updated_at BEFORE UPDATE ON spring_options_registry FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_parser_configs_updated_at BEFORE UPDATE ON parser_configurations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_field_discovery_updated_at BEFORE UPDATE ON field_discovery_log FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_processing_jobs_updated_at BEFORE UPDATE ON processing_jobs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_quality_metrics_updated_at BEFORE UPDATE ON quality_metrics FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- VIEWS FOR COMMON QUERIES
-- =============================================================================

-- Processing Status Overview
CREATE VIEW processing_status_overview AS
SELECT 
    pl.id as price_list_id,
    pl.filename,
    pl.market,
    pl.brand,
    pl.model_year,
    pl.processing_status,
    pl.total_entries,
    pl.processed_entries,
    pl.failed_entries,
    ROUND((pl.processed_entries::DECIMAL / NULLIF(pl.total_entries, 0) * 100), 2) as completion_percentage,
    pl.processing_duration_ms,
    pl.claude_api_calls,
    pl.total_cost_usd
FROM price_lists pl
WHERE pl.deleted_at IS NULL;

-- Product Quality Dashboard
CREATE VIEW product_quality_dashboard AS
SELECT 
    p.brand,
    p.model_year,
    COUNT(*) as total_products,
    COUNT(*) FILTER (WHERE p.confidence_score >= 0.95) as high_confidence_products,
    COUNT(*) FILTER (WHERE p.auto_accepted = TRUE) as auto_accepted_products,
    COUNT(*) FILTER (WHERE p.validation_status = 'requires_review') as requiring_review,
    AVG(p.confidence_score) as avg_confidence_score,
    AVG(mm.processing_duration_ms) as avg_processing_time_ms,
    SUM(mm.claude_api_calls) as total_claude_calls
FROM products p
LEFT JOIN model_mappings mm ON p.sku = mm.catalog_sku
WHERE p.deleted_at IS NULL
GROUP BY p.brand, p.model_year
ORDER BY p.brand, p.model_year DESC;

-- Spring Options Effectiveness
CREATE VIEW spring_options_effectiveness AS
SELECT 
    sor.brand,
    sor.option_type,
    sor.option_name,
    sor.times_applied,
    sor.success_rate,
    sor.confidence_score,
    sor.validated_by_claude,
    sor.validated_by_human,
    COUNT(mm.id) as recent_usage_count
FROM spring_options_registry sor
LEFT JOIN model_mappings mm ON mm.stage_4_result->>'applied_spring_options' LIKE '%' || sor.option_name || '%'
    AND mm.created_at >= CURRENT_DATE - INTERVAL '30 days'
WHERE sor.deleted_at IS NULL
GROUP BY sor.id, sor.brand, sor.option_type, sor.option_name, sor.times_applied, sor.success_rate, sor.confidence_score, sor.validated_by_claude, sor.validated_by_human
ORDER BY sor.brand, sor.option_type, sor.times_applied DESC;

-- =============================================================================
-- FUNCTIONS FOR COMMON OPERATIONS
-- =============================================================================

-- Function to get or create base model lookup key
CREATE OR REPLACE FUNCTION get_base_model_lookup_key(
    p_brand VARCHAR(50),
    p_model_family VARCHAR(100),
    p_model_year INTEGER
) RETURNS VARCHAR(200) AS $$
BEGIN
    RETURN p_brand || '_' || REPLACE(p_model_family, ' ', '_') || '_' || p_model_year::text;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to calculate processing completion percentage
CREATE OR REPLACE FUNCTION calculate_completion_percentage(
    p_processed INTEGER,
    p_total INTEGER
) RETURNS DECIMAL(5,2) AS $$
BEGIN
    IF p_total = 0 OR p_total IS NULL THEN
        RETURN 0.00;
    END IF;
    
    RETURN ROUND((p_processed::DECIMAL / p_total * 100), 2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- =============================================================================
-- INITIAL DATA AND CONFIGURATION
-- =============================================================================

-- Insert default parser configurations for each brand/market combination
INSERT INTO parser_configurations (brand, market, document_type, preferred_parser, fallback_parsers, field_mappings, created_by) VALUES
-- Ski-Doo configurations
('Ski-Doo', 'FI', 'price_list', 'PyMuPDF', '["Camelot", "Claude_OCR"]', '{"model_code": "Tuote-nro", "price": "Hinta", "engine": "Moottori"}', 'system'),
('Ski-Doo', 'SE', 'price_list', 'PyMuPDF', '["Camelot", "Claude_OCR"]', '{"model_code": "Artikelnr", "price": "Pris", "engine": "Motor"}', 'system'),
('Ski-Doo', 'NO', 'price_list', 'PyMuPDF', '["Camelot", "Claude_OCR"]', '{"model_code": "Artikkelnr", "price": "Pris", "engine": "Motor"}', 'system'),
('Ski-Doo', 'DK', 'price_list', 'PyMuPDF', '["Camelot", "Claude_OCR"]', '{"model_code": "Varenr", "price": "Pris", "engine": "Motor"}', 'system'),

-- Lynx configurations
('Lynx', 'FI', 'price_list', 'PyMuPDF', '["Camelot", "Claude_OCR"]', '{"model_code": "Tuote-nro", "price": "Hinta", "engine": "Moottori"}', 'system'),
('Lynx', 'SE', 'price_list', 'PyMuPDF', '["Camelot", "Claude_OCR"]', '{"model_code": "Artikelnr", "price": "Pris", "engine": "Motor"}', 'system'),
('Lynx', 'NO', 'price_list', 'PyMuPDF', '["Camelot", "Claude_OCR"]', '{"model_code": "Artikkelnr", "price": "Pris", "engine": "Motor"}', 'system'),

-- Sea-Doo configurations  
('Sea-Doo', 'FI', 'price_list', 'PyMuPDF', '["Camelot", "Claude_OCR"]', '{"model_code": "Tuote-nro", "price": "Hinta", "engine": "Moottori"}', 'system'),
('Sea-Doo', 'SE', 'price_list', 'PyMuPDF', '["Camelot", "Claude_OCR"]', '{"model_code": "Artikelnr", "price": "Pris", "engine": "Motor"}', 'system'),
('Sea-Doo', 'NO', 'price_list', 'PyMuPDF', '["Camelot", "Claude_OCR"]', '{"model_code": "Artikkelnr", "price": "Pris", "engine": "Motor"}', 'system'),
('Sea-Doo', 'DK', 'price_list', 'PyMuPDF', '["Camelot", "Claude_OCR"]', '{"model_code": "Varenr", "price": "Pris", "engine": "Motor"}', 'system');

-- =============================================================================
-- COMMENTS AND DOCUMENTATION
-- =============================================================================

COMMENT ON DATABASE snowmobile_reconciliation IS 'Snowmobile Product Data Reconciliation System - 5-Stage Inheritance Pipeline with Intelligent Parser Configuration';

-- Table Comments
COMMENT ON TABLE products IS 'Final constructed products with complete specifications from inheritance pipeline';
COMMENT ON TABLE base_models_catalog IS 'Catalog base models used as inheritance templates';
COMMENT ON TABLE price_lists IS 'Master table for uploaded price list documents';
COMMENT ON TABLE price_entries IS 'Individual price list entries with original data';
COMMENT ON TABLE model_mappings IS 'Tracks inheritance pipeline from model codes to final products';
COMMENT ON TABLE spring_options_registry IS 'Knowledge base of spring options and modifications';
COMMENT ON TABLE parser_configurations IS 'Intelligent parser configuration management';
COMMENT ON TABLE field_discovery_log IS 'Dynamic field discovery and classification tracking';
COMMENT ON TABLE processing_jobs IS 'Long-running processing operation tracking';
COMMENT ON TABLE quality_metrics IS 'System performance and quality metrics';

-- Key Column Comments
COMMENT ON COLUMN products.sku IS 'Final product SKU - primary business identifier';
COMMENT ON COLUMN products.full_specifications IS 'Complete product specifications in JSONB format';
COMMENT ON COLUMN products.inheritance_audit_trail IS 'Complete audit trail of inheritance pipeline processing';
COMMENT ON COLUMN model_mappings.confidence_score IS 'AI confidence score for inheritance accuracy (0.0-1.0)';
COMMENT ON COLUMN model_mappings.processing_method IS 'Method used: exact_lookup or claude_semantic';
COMMENT ON COLUMN base_models_catalog.lookup_key IS 'Unique key for base model matching: Brand_ModelFamily_Year';
COMMENT ON COLUMN spring_options_registry.specifications IS 'Technical modifications applied by this spring option';
COMMENT ON COLUMN parser_configurations.field_mappings IS 'Column name mappings for different markets/languages';

-- =============================================================================
-- SCHEMA VERSION TRACKING
-- =============================================================================

CREATE TABLE schema_version (
    version VARCHAR(20) PRIMARY KEY,
    description TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    applied_by VARCHAR(100) NOT NULL
);

INSERT INTO schema_version (version, description, applied_by) VALUES 
('2.0.0', 'Enhanced Inheritance Pipeline with Intelligent Parser Configuration', 'system');