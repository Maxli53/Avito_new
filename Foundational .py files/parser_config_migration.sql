-- Migration: Add parser configuration support
-- File: migrations/add_parser_configuration_support.sql

-- Add parser configuration fields to existing tables
ALTER TABLE model_mappings ADD COLUMN 
    parser_config_used JSONB DEFAULT '{}';

ALTER TABLE model_mappings ADD COLUMN 
    unknown_fields_discovered JSONB DEFAULT '[]';

ALTER TABLE model_mappings ADD COLUMN 
    field_mapping_overrides JSONB DEFAULT '{}';

-- Add parser performance tracking
ALTER TABLE model_mappings ADD COLUMN 
    parsing_method VARCHAR(50) DEFAULT 'pymupdf';

ALTER TABLE model_mappings ADD COLUMN 
    parsing_performance_ms INTEGER;

ALTER TABLE model_mappings ADD COLUMN 
    ocr_confidence_score DECIMAL(3,2);

-- New table for parser configuration evolution
CREATE TABLE parser_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Configuration Identity
    brand VARCHAR(50) NOT NULL,
    market VARCHAR(10) NOT NULL,
    model_year INTEGER NOT NULL,
    
    -- Configuration Data
    configuration JSONB NOT NULL DEFAULT '{}',
    field_mappings JSONB NOT NULL DEFAULT '{}',
    parsing_rules JSONB NOT NULL DEFAULT '{}',
    
    -- Performance Metrics
    success_rate DECIMAL(5,2) DEFAULT 0.00,
    avg_confidence_score DECIMAL(3,2) DEFAULT 0.00,
    total_documents_processed INTEGER DEFAULT 0,
    
    -- Version Control
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'system',
    
    UNIQUE(brand, market, model_year, version)
);

-- Field discovery tracking table
CREATE TABLE discovered_fields (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Discovery Context
    brand VARCHAR(50) NOT NULL,
    market VARCHAR(10) NOT NULL, 
    model_year INTEGER NOT NULL,
    source_document VARCHAR(255),
    
    -- Field Information
    original_field_name VARCHAR(200) NOT NULL,
    field_values JSONB DEFAULT '[]',  -- Array of encountered values
    field_frequency INTEGER DEFAULT 1,
    
    -- Classification
    field_type VARCHAR(50),  -- 'specification', 'pricing', 'metadata', 'unknown'
    mapped_to VARCHAR(100),  -- What this field maps to in our schema
    classification_confidence DECIMAL(3,2),
    
    -- Claude Analysis
    claude_interpretation JSONB DEFAULT '{}',
    human_validated BOOLEAN DEFAULT FALSE,
    validation_notes TEXT,
    
    -- Discovery Metadata
    first_discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    discovery_source VARCHAR(50) DEFAULT 'parser',
    
    UNIQUE(brand, market, model_year, original_field_name)
);

-- Parser performance monitoring
CREATE TABLE parser_performance_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Processing Context
    brand VARCHAR(50) NOT NULL,
    market VARCHAR(10) NOT NULL,
    source_file VARCHAR(255) NOT NULL,
    
    -- Performance Metrics
    parser_used VARCHAR(50) NOT NULL,
    processing_time_ms INTEGER NOT NULL,
    memory_usage_mb INTEGER,
    pages_processed INTEGER,
    
    -- Quality Metrics
    extraction_confidence DECIMAL(3,2),
    fields_extracted INTEGER,
    unknown_fields_count INTEGER,
    validation_errors INTEGER,
    
    -- Results
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    fallback_used BOOLEAN DEFAULT FALSE,
    
    -- Tracking
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_pipeline_version VARCHAR(20)
);

-- Indexes for performance
CREATE INDEX idx_parser_configs_brand_market ON parser_configurations(brand, market, model_year);
CREATE INDEX idx_parser_configs_active ON parser_configurations(is_active, brand);
CREATE INDEX idx_discovered_fields_brand ON discovered_fields(brand, model_year);
CREATE INDEX idx_discovered_fields_frequency ON discovered_fields(field_frequency DESC);
CREATE INDEX idx_discovered_fields_validation ON discovered_fields(human_validated, classification_confidence);
CREATE INDEX idx_parser_performance_brand_file ON parser_performance_log(brand, source_file);
CREATE INDEX idx_parser_performance_time ON parser_performance_log(processed_at);
CREATE INDEX idx_parser_performance_success ON parser_performance_log(success, parser_used);

-- JSONB indexes for configuration queries
CREATE INDEX idx_parser_configs_config ON parser_configurations USING GIN (configuration);
CREATE INDEX idx_discovered_fields_claude ON discovered_fields USING GIN (claude_interpretation);
CREATE INDEX idx_model_mappings_parser_config ON model_mappings USING GIN (parser_config_used);
CREATE INDEX idx_model_mappings_unknown_fields ON model_mappings USING GIN (unknown_fields_discovered);

-- Views for monitoring and reporting
CREATE VIEW parser_configuration_summary AS
SELECT 
    brand,
    market, 
    model_year,
    COUNT(*) as total_configs,
    MAX(version) as latest_version,
    AVG(success_rate) as avg_success_rate,
    SUM(total_documents_processed) as total_processed
FROM parser_configurations 
WHERE is_active = TRUE
GROUP BY brand, market, model_year;

CREATE VIEW unknown_fields_summary AS  
SELECT
    brand,
    model_year,
    original_field_name,
    field_frequency,
    field_type,
    mapped_to,
    classification_confidence,
    human_validated,
    COUNT(*) OVER (PARTITION BY brand, model_year) as total_unknown_fields_brand_year
FROM discovered_fields
ORDER BY field_frequency DESC, classification_confidence DESC;

CREATE VIEW parser_performance_summary AS
SELECT 
    brand,
    parser_used,
    DATE(processed_at) as processing_date,
    COUNT(*) as documents_processed,
    AVG(processing_time_ms) as avg_processing_time,
    AVG(extraction_confidence) as avg_confidence,
    COUNT(*) FILTER (WHERE success = FALSE) as failures,
    COUNT(*) FILTER (WHERE fallback_used = TRUE) as fallbacks_used
FROM parser_performance_log
GROUP BY brand, parser_used, DATE(processed_at)
ORDER BY processing_date DESC;

-- Functions for configuration management
CREATE OR REPLACE FUNCTION update_field_mapping(
    p_brand VARCHAR(50),
    p_market VARCHAR(10), 
    p_model_year INTEGER,
    p_original_field VARCHAR(200),
    p_mapped_to VARCHAR(100),
    p_confidence DECIMAL(3,2) DEFAULT 1.00
)
RETURNS UUID AS $$
DECLARE
    discovered_field_id UUID;
BEGIN
    -- Update or insert discovered field
    INSERT INTO discovered_fields (
        brand, market, model_year, original_field_name, 
        mapped_to, classification_confidence, field_frequency,
        human_validated
    ) VALUES (
        p_brand, p_market, p_model_year, p_original_field,
        p_mapped_to, p_confidence, 1, TRUE
    ) 
    ON CONFLICT (brand, market, model_year, original_field_name)
    DO UPDATE SET
        mapped_to = EXCLUDED.mapped_to,
        classification_confidence = EXCLUDED.classification_confidence,
        human_validated = TRUE,
        last_seen_at = CURRENT_TIMESTAMP
    RETURNING id INTO discovered_field_id;
    
    -- Update configuration
    UPDATE parser_configurations SET
        field_mappings = field_mappings || 
            jsonb_build_object(p_original_field, p_mapped_to),
        updated_at = CURRENT_TIMESTAMP
    WHERE brand = p_brand 
      AND market = p_market 
      AND model_year = p_model_year 
      AND is_active = TRUE;
    
    RETURN discovered_field_id;
END;
$$ LANGUAGE plpgsql;

-- Sample data for initial configuration
INSERT INTO parser_configurations (brand, market, model_year, configuration, field_mappings) VALUES
(
    'Ski-Doo', 
    'FI', 
    2026, 
    '{"primary_parser": "pymupdf", "ocr_confidence_threshold": 0.85, "table_detection_method": "lattice"}',
    '{"Tuote-nro": "model_code", "Malli": "malli", "Paketti": "paketti", "Moottori": "moottori", "Telamatto": "telamatto", "Kevätoptiot": "spring_options", "Väri": "color"}'
),
(
    'Lynx', 
    'FI', 
    2026, 
    '{"primary_parser": "pymupdf", "ocr_confidence_threshold": 0.85, "table_detection_method": "lattice"}',
    '{"Tuote-nro": "model_code", "Malli": "malli", "Paketti": "paketti", "Moottori": "moottori", "Telamatto": "telamatto", "Kevätoptiot": "spring_options", "Väri": "color"}'
),
(
    'Sea-Doo',
    'FI',
    2026,
    '{"primary_parser": "pymupdf", "ocr_confidence_threshold": 0.90, "table_detection_method": "stream", "expected_language": "en"}',
    '{"Model": "model_code", "Engine": "moottori", "Features": "features", "Color": "color"}'
);

COMMENT ON TABLE parser_configurations IS 'Stores brand/market/year specific parser configurations';
COMMENT ON TABLE discovered_fields IS 'Tracks new fields discovered during PDF parsing for learning';
COMMENT ON TABLE parser_performance_log IS 'Monitors parser performance and success rates';
COMMENT ON VIEW parser_configuration_summary IS 'Summary of parser configurations by brand/market/year';
COMMENT ON VIEW unknown_fields_summary IS 'Summary of unknown fields discovered during parsing';
COMMENT ON VIEW parser_performance_summary IS 'Daily parser performance metrics by brand and parser type';