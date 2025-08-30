# Database Schema - Inheritance Pipeline
**Snowmobile Product Data Reconciliation System**

## 🏗️ Schema Overview

The database schema is designed specifically for the **5-stage inheritance pipeline**, tracking the complete journey from model codes to final products through base model inheritance.

## 📊 Core Tables

### Products Table
**Stores final constructed products with complete specifications**

```sql
CREATE TABLE products (
    sku VARCHAR(20) PRIMARY KEY,
    internal_id UUID DEFAULT gen_random_uuid(),
    
    -- Product Identity
    brand VARCHAR(50) NOT NULL,              -- 'Ski-Doo', 'Lynx', 'Sea-Doo'
    model_year INTEGER NOT NULL,
    model_family VARCHAR(100),               -- 'Rave RE', 'MXZ X-RS', 'Summit X'
    base_model_source VARCHAR(200),          -- Source base model used for inheritance
    platform VARCHAR(50),                   -- 'REV Gen5', 'Radien²', 'SHOT'
    category VARCHAR(50),                    -- 'Trail', 'Deep Snow', 'Crossover'
    
    -- Key Searchable Specifications
    engine_model VARCHAR(100),
    engine_displacement_cc INTEGER,
    track_length_mm INTEGER,
    track_width_mm INTEGER,
    track_profile_mm INTEGER,
    dry_weight_kg INTEGER,
    
    -- Complete Specifications (JSONB for flexibility)
    full_specifications JSONB NOT NULL DEFAULT '{}',
    marketing_texts JSONB DEFAULT '{}',      -- Multi-language content
    spring_modifications JSONB DEFAULT '{}', -- Applied spring options
    
    -- Audit and Tracking
    inheritance_audit_trail JSONB DEFAULT '{}', -- Complete processing history
    raw_sources JSONB DEFAULT '[]',         -- Source attribution
    processing_metadata JSONB DEFAULT '{}', -- Pipeline processing details
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Model Mappings Table
**Tracks the inheritance pipeline from model codes to final products**

```sql
CREATE TABLE model_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Model Code Processing
    model_code VARCHAR(50) NOT NULL,         -- Original: LTTA, MVTL, UJTU
    catalog_sku VARCHAR(20) NOT NULL,        -- Final product SKU
    brand VARCHAR(50) NOT NULL,              -- Detected brand
    model_family VARCHAR(100) NOT NULL,      -- Extracted: "Rave RE", "MXZ X-RS"
    
    -- Inheritance Chain
    base_model_matched VARCHAR(200) NOT NULL, -- Base model used for inheritance
    processing_method VARCHAR(50) NOT NULL,   -- 'exact_lookup', 'claude_semantic'
    confidence_score DECIMAL(3,2) NOT NULL,
    
    -- Pipeline Stage Results
    stage_1_result JSONB DEFAULT '{}',       -- Base model matching details
    stage_2_result JSONB DEFAULT '{}',       -- Inheritance details
    stage_3_result JSONB DEFAULT '{}',       -- Variant selection details
    stage_4_result JSONB DEFAULT '{}',       -- Spring options details
    stage_5_result JSONB DEFAULT '{}',       -- Validation details
    
    -- Quality Tracking
    auto_accepted BOOLEAN DEFAULT FALSE,      -- Confidence ≥0.95
    requires_review BOOLEAN DEFAULT FALSE,    -- System-detected issues
    validation_passed BOOLEAN DEFAULT TRUE,   -- All validations successful
    
    -- Audit Trail
    complete_audit_trail JSONB DEFAULT '{}', -- Full processing audit
    processing_duration_ms INTEGER,          -- Total pipeline time
    claude_api_calls INTEGER DEFAULT 0,      -- API usage tracking
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (catalog_sku) REFERENCES products(sku),
    
    -- Ensure each model code maps to only one product
    UNIQUE (model_code, brand, model_family)
);
```

### Price Entries Table
**Stores original price list data with market information**

```sql
CREATE TABLE price_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    price_list_id UUID NOT NULL,
    
    -- Original Price List Data
    model_code VARCHAR(50) NOT NULL,         -- Tuote-nro: LTTA, MVTL
    malli VARCHAR(100),                      -- Rave, MXZ, Summit
    paketti VARCHAR(100),                    -- RE, X-RS, X
    moottori VARCHAR(100),                   -- 600R E-TEC, 850 E-TEC
    telamatto VARCHAR(100),                  -- 129in/3300mm, 137in/3500mm
    kaynnistin VARCHAR(50),                  -- Manual, Electric
    mittaristo VARCHAR(100),                 -- 7.2 in. Digital Display
    kevätoptiot TEXT,                        -- Spring options text
    vari VARCHAR(100),                       -- Color specification
    
    -- Pricing Information
    price_amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL,            -- EUR, SEK, NOK, DKK
    market VARCHAR(10) NOT NULL,             -- FI, SE, NO, DK
    
    -- Processing Status
    processed BOOLEAN DEFAULT FALSE,         -- Has been through pipeline
    processing_error TEXT,                   -- Error message if failed
    mapped_product_sku VARCHAR(20),          -- Link to final product
    
    -- Metadata
    source_file VARCHAR(255),                -- Original PDF filename
    source_page INTEGER,                     -- Page number in PDF
    extraction_confidence DECIMAL(3,2),     -- PDF extraction quality
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (mapped_product_sku) REFERENCES products(sku)
);
```

### Base Models Catalog Table
**Stores catalog base models for inheritance**

```sql
CREATE TABLE base_models_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Base Model Identity
    brand VARCHAR(50) NOT NULL,              -- Ski-Doo, Lynx, Sea-Doo
    model_family VARCHAR(100) NOT NULL,      -- "Rave RE", "MXZ X-RS"
    model_year INTEGER NOT NULL,
    lookup_key VARCHAR(200) NOT NULL UNIQUE, -- "Lynx_Rave_RE"
    
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
    
    -- Source Tracking
    catalog_source VARCHAR(255),             -- Source document
    catalog_page INTEGER,                    -- Page in catalog
    extraction_date TIMESTAMP,              -- When extracted
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Spring Options Registry Table
**Knowledge base of spring options across brands and models**

```sql
CREATE TABLE spring_options_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Spring Option Identity
    brand VARCHAR(50) NOT NULL,
    model_family VARCHAR(100),               -- NULL = applies to all models
    model_year INTEGER,                      -- NULL = applies to all years
    option_name VARCHAR(200) NOT NULL,       -- "Black edition", "Studded Track"
    
    -- Option Details
    option_type VARCHAR(50) NOT NULL,        -- 'color', 'track', 'suspension', 'gauge'
    description TEXT,                        -- Human-readable description
    specifications JSONB NOT NULL DEFAULT '{}', -- Technical modifications
    
    -- Application Rules
    applies_to_models JSONB DEFAULT '[]',    -- Specific model codes if limited
    conflicts_with JSONB DEFAULT '[]',       -- Incompatible options
    
    -- Metadata
    confidence_score DECIMAL(3,2) DEFAULT 0.95, -- How certain we are
    source VARCHAR(255),                     -- Where this was learned
    validated_by_claude BOOLEAN DEFAULT FALSE, -- AI validation status
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE (brand, option_name, model_year)
);
```

## 📈 Performance Indexes

### Primary Performance Indexes
```sql
-- Product lookups
CREATE INDEX idx_products_brand_year ON products(brand, model_year);
CREATE INDEX idx_products_model_family ON products(model_family);
CREATE INDEX idx_products_specs_gin ON products(full_specifications) USING GIN;

-- Model code processing
CREATE INDEX idx_model_mappings_code ON model_mappings(model_code);
CREATE INDEX idx_model_mappings_brand_family ON model_mappings(brand, model_family);
CREATE INDEX idx_model_mappings_confidence ON model_mappings(confidence_score DESC);
CREATE INDEX idx_model_mappings_method ON model_mappings(processing_method);

-- Price entry processing
CREATE INDEX idx_price_entries_market ON price_entries(market, model_year);
CREATE INDEX idx_price_entries_processed ON price_entries(processed, created_at);
CREATE INDEX idx_price_entries_source ON price_entries(source_file);

-- Base model inheritance
CREATE INDEX idx_base_models_lookup ON base_models_catalog(lookup_key);
CREATE INDEX idx_base_models_brand_family ON base_models_catalog(brand, model_family);

-- Spring options lookup
CREATE INDEX idx_spring_options_brand ON spring_options_registry(brand, option_name);
CREATE INDEX idx_spring_options_type ON spring_options_registry(option_type);
```

### JSONB Specialized Indexes
```sql
-- Full specifications search
CREATE INDEX idx_products_specs_engine ON products 
    USING GIN ((full_specifications->'engine'));
CREATE INDEX idx_products_specs_track ON products 
    USING GIN ((full_specifications->'track'));

-- Audit trail search
CREATE INDEX idx_mappings_audit_confidence ON model_mappings 
    USING GIN ((complete_audit_trail->'confidence_components'));
CREATE INDEX idx_mappings_audit_spring ON model_mappings 
    USING GIN ((stage_4_result->'spring_modifications'));
```

## 🔍 Key Query Patterns

### Base Model Lookup (Stage 1)
```sql
-- Exact lookup for inheritance
SELECT * FROM base_models_catalog 
WHERE lookup_key = 'Lynx_Rave_RE' 
AND model_year = 2026;

-- Find similar base models for Claude fallback
SELECT * FROM base_models_catalog 
WHERE brand = 'Lynx' 
AND model_family ILIKE '%Rave%'
AND model_year = 2026;
```

### Pipeline Status Tracking
```sql
-- Monitor processing success rates
SELECT 
    processing_method,
    COUNT(*) as total_processed,
    AVG(confidence_score) as avg_confidence,
    COUNT(*) FILTER (WHERE auto_accepted) as auto_accepted,
    AVG(processing_duration_ms) as avg_duration_ms
FROM model_mappings 
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY processing_method;
```

### Spring Options Research
```sql
-- Find applicable spring options for a model
SELECT * FROM spring_options_registry 
WHERE brand = 'Lynx'
AND (model_family IS NULL OR model_family = 'Rave RE')
AND (model_year IS NULL OR model_year = 2026)
AND option_name ILIKE '%Black%';
```

### Quality Monitoring
```sql
-- Find products requiring review
SELECT 
    mm.model_code,
    mm.confidence_score,
    mm.processing_method,
    pe.kevätoptiot,
    mm.complete_audit_trail->'validation_issues' as issues
FROM model_mappings mm
JOIN price_entries pe ON pe.model_code = mm.model_code
WHERE mm.requires_review = TRUE
OR mm.confidence_score < 0.95
ORDER BY mm.confidence_score ASC;
```

## 🚀 Migration Strategy

### Schema Evolution Process
```sql
-- All schema changes use Alembic migrations
-- Example migration for adding new inheritance features:

"""Add stage-specific result tracking

Revision ID: add_stage_results
Revises: base_inheritance_schema
Create Date: 2024-01-15 10:30:00.000000
"""

def upgrade():
    op.add_column('model_mappings', 
        sa.Column('stage_1_result', postgresql.JSONB(), nullable=True))
    op.add_column('model_mappings', 
        sa.Column('stage_2_result', postgresql.JSONB(), nullable=True))
    # ... additional stage columns
    
def downgrade():
    op.drop_column('model_mappings', 'stage_1_result')
    # ... rollback logic
```

## 📊 Data Relationships

```
Price Entry (LTTA) 
    ↓
Model Mapping (inheritance pipeline tracking)
    ↓ (inherits from)
Base Model (Lynx Rave RE catalog)
    ↓ (enhanced with)
Spring Options (Black edition modifications)
    ↓ (produces)
Final Product (complete specifications)
```

This schema design eliminates all references to the old fuzzy matching approach and is optimized specifically for the inheritance pipeline methodology.