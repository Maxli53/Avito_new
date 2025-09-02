-- ============================================================================
-- SNOWMOBILE DUAL PARSER PIPELINE DATABASE SCHEMA
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- EXTRACTION TABLES
-- ============================================================================

-- Table 1: Price lists metadata
CREATE TABLE price_lists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    brand VARCHAR(50) NOT NULL,
    market VARCHAR(10) NOT NULL,
    model_year INTEGER NOT NULL,
    
    -- Processing tracking
    total_entries INTEGER DEFAULT 0,
    processed_entries INTEGER DEFAULT 0,
    failed_entries INTEGER DEFAULT 0,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN (
        'pending', 'processing', 'completed', 'failed'
    )),
    
    -- Audit
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    
    UNIQUE(brand, market, model_year)
);

-- Table 2: Catalogs metadata
CREATE TABLE catalogs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    brand VARCHAR(50) NOT NULL,
    model_year INTEGER NOT NULL,
    document_type VARCHAR(50) DEFAULT 'product_spec_book',
    language VARCHAR(10),
    
    -- Extraction metrics
    total_pages INTEGER,
    total_models_extracted INTEGER DEFAULT 0,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN (
        'pending', 'processing', 'completed', 'failed'
    )),
    
    -- Audit
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    
    UNIQUE(brand, model_year, document_type)
);

-- Table 3: Price list entries (from price PDFs)
CREATE TABLE price_entries (
    -- Identity
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    price_list_id UUID NOT NULL REFERENCES price_lists(id) ON DELETE CASCADE,
    
    -- Core extracted fields (Finnish column names preserved)
    model_code VARCHAR(20) NOT NULL,        -- "LTTA"
    malli VARCHAR(100) NOT NULL,            -- "Rave"
    paketti VARCHAR(100),                   -- "RE"
    moottori VARCHAR(100),                  -- "600R E-TEC"
    telamatto VARCHAR(100),                 -- "137in 3500mm"
    kaynnistin VARCHAR(100),                -- "Manual"
    mittaristo VARCHAR(100),                -- "7.2 in. Digital Display"
    kevatoptiot TEXT,                       -- "Black edition" or NULL
    vari VARCHAR(100),                      -- "Viper Red / Black"
    
    -- Price data
    price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    
    -- Metadata (from price_lists table)
    market VARCHAR(10) NOT NULL,            -- "FI", "SE", "NO"
    brand VARCHAR(50) NOT NULL,             -- "Lynx", "Ski-Doo"
    model_year INTEGER NOT NULL,            -- 2026
    
    -- Generated deterministic lookup key
    catalog_lookup_key VARCHAR(200) GENERATED ALWAYS AS (
        brand || '_' || 
        REPLACE(malli || '_' || COALESCE(paketti, ''), ' ', '_') || '_' || 
        model_year::text
    ) STORED,
    
    -- Processing status
    status VARCHAR(20) DEFAULT 'extracted' CHECK (status IN (
        'extracted', 'matched', 'processing', 'completed', 'failed'
    )),
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table 4: Base model specifications (from catalog PDFs)
CREATE TABLE base_models_catalog (
    -- Identity  
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    catalog_id UUID NOT NULL REFERENCES catalogs(id) ON DELETE CASCADE,
    
    -- Lookup key for matching
    lookup_key VARCHAR(200) NOT NULL UNIQUE,  -- "Lynx_Rave_RE_2026"
    
    -- Identification
    brand VARCHAR(50) NOT NULL,               -- "Lynx"
    model_family VARCHAR(100) NOT NULL,       -- "Rave RE"
    model_year INTEGER NOT NULL,              -- 2026
    
    -- Available options (all possibilities)
    engine_options JSONB,                     -- All engine variants with specs
    track_options JSONB,                      -- All track variants with specs
    suspension_options JSONB,                 -- All suspension options
    starter_options JSONB,                    -- Manual/Electric options
    
    -- Standard specifications
    dimensions JSONB,                         -- Length, width, height, weight
    features TEXT[],                          -- Standard features list
    
    -- Complete catalog data
    full_specifications JSONB,                -- Everything from catalog
    marketing_description TEXT,               -- Marketing copy
    
    -- Source tracking
    source_pages INTEGER[],                   -- [14, 15, 16]
    
    -- Quality metrics
    extraction_confidence DECIMAL(3,2),
    completeness_score DECIMAL(3,2),
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints and indexes
    UNIQUE(brand, model_family, model_year)
);

-- ============================================================================
-- PROCESSING TABLES
-- ============================================================================

-- Table 5: Final products (after Claude inheritance)
CREATE TABLE products (
    -- Identity
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku VARCHAR(100) UNIQUE NOT NULL,
    
    -- Model identification
    model_code VARCHAR(20) NOT NULL,
    brand VARCHAR(50) NOT NULL,
    model_family VARCHAR(100) NOT NULL,
    model_year INTEGER NOT NULL,
    
    -- Market specific
    market VARCHAR(10) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    
    -- Source tracking
    price_entry_id UUID NOT NULL REFERENCES price_entries(id),
    base_model_id UUID NOT NULL REFERENCES base_models_catalog(id),
    
    -- Claude intelligent inheritance results
    resolved_specifications JSONB NOT NULL,   -- Final specs after inheritance
    inheritance_adjustments JSONB,            -- What Claude changed and why
    selected_variations JSONB,                -- Which options were selected
    
    -- Generated content
    html_content TEXT,                        -- Final HTML specification sheet
    html_generated_at TIMESTAMP,
    
    -- Quality and validation
    confidence_score DECIMAL(3,2),
    validation_status VARCHAR(20) DEFAULT 'pending' CHECK (validation_status IN (
        'pending', 'validated', 'published', 'requires_review'
    )),
    auto_approved BOOLEAN DEFAULT FALSE,
    
    -- Performance tracking
    claude_api_calls INTEGER DEFAULT 0,
    claude_processing_ms INTEGER,
    total_cost_usd DECIMAL(10,4),
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP
);

-- Table 6: Spring options registry (learning system)
CREATE TABLE spring_options_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    option_name VARCHAR(200) NOT NULL,        -- "Black edition"
    brand VARCHAR(50),
    
    -- Known modifications
    specifications_changes JSONB,             -- What this option changes
    
    -- Learning metrics
    times_seen INTEGER DEFAULT 1,
    confidence_score DECIMAL(3,2),
    
    -- Validation
    validated_by_claude BOOLEAN DEFAULT FALSE,
    validated_by_human BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(option_name, brand)
);

-- ============================================================================
-- PROCESSING TRACKING
-- ============================================================================

-- Table 7: Processing jobs
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type VARCHAR(50) NOT NULL CHECK (job_type IN (
        'price_extraction', 'catalog_extraction', 'product_generation', 'batch_processing'
    )),
    
    -- References
    price_list_id UUID REFERENCES price_lists(id),
    catalog_id UUID REFERENCES catalogs(id),
    
    -- Status tracking
    status VARCHAR(20) DEFAULT 'queued' CHECK (status IN (
        'queued', 'running', 'completed', 'failed', 'cancelled'
    )),
    progress_percentage INTEGER DEFAULT 0,
    
    -- Metrics
    total_items INTEGER,
    processed_items INTEGER DEFAULT 0,
    successful_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    
    -- Performance
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    
    -- Error tracking
    error_message TEXT,
    error_details JSONB,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Price entries indexes
CREATE INDEX idx_price_model_code ON price_entries(model_code);
CREATE INDEX idx_price_lookup_key ON price_entries(catalog_lookup_key);
CREATE INDEX idx_price_status ON price_entries(status);
CREATE INDEX idx_price_brand_year ON price_entries(brand, model_year);

-- Base models catalog indexes
CREATE INDEX idx_base_lookup ON base_models_catalog(lookup_key);
CREATE INDEX idx_base_brand_year ON base_models_catalog(brand, model_year);

-- Products indexes
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_model_code ON products(model_code);
CREATE INDEX idx_products_market ON products(market);
CREATE INDEX idx_products_status ON products(validation_status);
CREATE INDEX idx_products_confidence ON products(confidence_score DESC);
CREATE INDEX idx_products_brand_year ON products(brand, model_year);

-- Processing jobs indexes
CREATE INDEX idx_jobs_type_status ON processing_jobs(job_type, status);
CREATE INDEX idx_jobs_created ON processing_jobs(created_at DESC);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to relevant tables
CREATE TRIGGER update_price_entries_updated_at BEFORE UPDATE ON price_entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_base_models_updated_at BEFORE UPDATE ON base_models_catalog
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- MONITORING VIEWS
-- ============================================================================

-- Processing success rate view
CREATE VIEW processing_metrics AS
SELECT 
    COUNT(*) FILTER (WHERE status = 'completed') * 100.0 / COUNT(*) as success_rate,
    AVG(confidence_score) as avg_confidence,
    AVG(claude_processing_ms) / 1000.0 as avg_processing_seconds,
    AVG(total_cost_usd) as avg_cost_per_product,
    COUNT(*) as total_products,
    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') as products_last_7d
FROM products
WHERE created_at >= NOW() - INTERVAL '30 days';

-- Unmatched entries view
CREATE VIEW unmatched_entries AS
SELECT 
    pe.model_code,
    pe.malli,
    pe.paketti,
    pe.catalog_lookup_key,
    pe.brand,
    pe.model_year,
    COUNT(*) as occurrences
FROM price_entries pe
LEFT JOIN base_models_catalog bmc ON pe.catalog_lookup_key = bmc.lookup_key
WHERE bmc.id IS NULL AND pe.status = 'extracted'
GROUP BY 1,2,3,4,5,6
ORDER BY occurrences DESC;

-- Processing pipeline status view
CREATE VIEW pipeline_status AS
SELECT 
    pl.brand,
    pl.market,
    pl.model_year,
    pl.total_entries,
    pl.processed_entries,
    pl.failed_entries,
    COALESCE(c.total_models_extracted, 0) as catalog_models,
    COUNT(p.id) as generated_products,
    pl.status as price_list_status,
    c.status as catalog_status
FROM price_lists pl
LEFT JOIN catalogs c ON pl.brand = c.brand AND pl.model_year = c.model_year
LEFT JOIN price_entries pe ON pl.id = pe.price_list_id
LEFT JOIN products p ON pe.id = p.price_entry_id
GROUP BY pl.id, c.id;