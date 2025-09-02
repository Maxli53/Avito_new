-- ========================================
-- UNIFIED SNOWMOBILE DATABASE SCHEMA (ALL BRANDS)
-- Handles: Ski-Doo, Lynx, Polaris, Arctic Cat, Yamaha, etc.
-- Supports: Multiple engine variants per model
-- ========================================

CREATE TABLE products (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sku VARCHAR(100) UNIQUE NOT NULL,
    
    -- Basic Model Information (Universal)
    brand VARCHAR(50) NOT NULL, -- 'Ski-Doo', 'Lynx', 'Polaris', 'Arctic Cat', 'Yamaha'
    model VARCHAR(100) NOT NULL, -- 'Summit X', 'Rave RE', 'RMK', 'M Series'
    configuration VARCHAR(100), -- 'Expert Package', 'Base', 'Sport', etc.
    category VARCHAR(50), -- 'deep-snow', 'trail', 'racing', 'utility', 'touring'
    model_year YEAR,
    description TEXT,
    
    -- Marketing Content
    whats_new JSON, -- Array of new features
    package_highlights JSON, -- Array of key selling points  
    spring_options JSON, -- Array of seasonal options
    
    -- All specifications as flexible JSON - handles multiple engine variants
    specifications JSON,
    
    -- Key extracted fields for fast queries (handles multiple engines)
    primary_engine_displacement INT GENERATED ALWAYS AS (
        COALESCE(
            JSON_EXTRACT(specifications, '$.engines[0].displacement'),
            JSON_EXTRACT(specifications, '$.engine.displacement')
        )
    ) STORED,
    
    min_dry_weight_kg INT GENERATED ALWAYS AS (
        COALESCE(
            JSON_EXTRACT(specifications, '$.weight.min'),
            JSON_EXTRACT(specifications, '$.dimensions.dryWeight'),
            JSON_EXTRACT(specifications, '$.weight.dry')
        )
    ) STORED,
    
    max_dry_weight_kg INT GENERATED ALWAYS AS (
        COALESCE(
            JSON_EXTRACT(specifications, '$.weight.max'),
            JSON_EXTRACT(specifications, '$.dimensions.dryWeight'),
            JSON_EXTRACT(specifications, '$.weight.dry')
        )
    ) STORED,
    
    msrp DECIMAL(10,2) GENERATED ALWAYS AS (
        JSON_EXTRACT(specifications, '$.pricing.msrp')
    ) STORED,
    
    has_turbo BOOLEAN GENERATED ALWAYS AS (
        COALESCE(
            JSON_EXTRACT(specifications, '$.engines[0].turbo'),
            JSON_EXTRACT(specifications, '$.engine.turbo'),
            JSON_CONTAINS(specifications, 'true', '$.engines[*].turbo'),
            false
        )
    ) STORED,
    
    engine_count INT GENERATED ALWAYS AS (
        COALESCE(
            JSON_LENGTH(specifications, '$.engines'),
            1
        )
    ) STORED,
    
    -- Cross-reference fields  
    supplier_id INT,
    category_id INT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    status ENUM('active', 'discontinued') DEFAULT 'active',
    
    -- Indexes for performance
    INDEX idx_brand_model_year (brand, model, model_year),
    INDEX idx_category (category),
    INDEX idx_displacement (primary_engine_displacement),
    INDEX idx_weight_range (min_dry_weight_kg, max_dry_weight_kg),
    INDEX idx_msrp (msrp),
    INDEX idx_turbo (has_turbo),
    INDEX idx_engine_count (engine_count),
    INDEX idx_supplier (supplier_id),
    INDEX idx_category_ref (category_id),
    
    -- JSON indexes for common queries
    INDEX idx_engine_types ((CAST(JSON_EXTRACT(specifications, '$.engines[*].type') AS CHAR(50) ARRAY))),
    INDEX idx_platforms ((JSON_UNQUOTE(JSON_EXTRACT(specifications, '$.features.platform')))),
    
    -- Foreign keys to existing tables
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- Example data structure for RAVE RE (multiple engines)
INSERT INTO products (sku, brand, model, category, model_year, whats_new, package_highlights, spring_options, specifications)
VALUES (
    'SKI-RAVE-RE-2026',
    'Ski-Doo',
    'Rave RE', 
    'trail',
    2026,
    JSON_ARRAY(
        'LFS-R front suspension',
        'Electric Starter standard on 850 and 600R E-TEC',
        '38 mm Ice Ripper XT studded track standard on 850 Turbo R and 850 E-TEC'
    ),
    JSON_ARRAY(
        'Launch Control and E-TEC SHOT starter (850 E-TEC Turbo R only)',
        '10.25 in. touchscreen display with BRP Connect and built-in GPS',
        'High-Performance 4-piston brake caliper with adjustable brake lever',
        'Kashima coated high-performance KYB PRO 46 HLCR shocks',
        'PPS³ rear suspension',
        'Premium LED headlights',
        'Rail Reinforcements'
    ),
    JSON_ARRAY(
        'Black color (850 E-TEC Turbo R)'
    ),
    JSON_OBJECT(
        'engines', JSON_ARRAY(
            JSON_OBJECT(
                'name', '850 E-TEC Turbo R',
                'type', '2-stroke', 
                'displacement', 849,
                'bore', 82.0,
                'stroke', 80.4,
                'maxRPM', 7900,
                'turbo', true,
                'cooling', 'liquid-cooled',
                'carburation', 'Electronic Direct Injection with additional booster injectors',
                'fuelType', 'Unleaded - 95',
                'fuelTank', 37,
                'oilCapacity', 3.4,
                'dryWeight', 240,
                'starter', 'SHOT',
                'gaugeType', '10.25 in. touchscreen'
            ),
            JSON_OBJECT(
                'name', '850 E-TEC',
                'type', '2-stroke',
                'displacement', 849, 
                'bore', 82.0,
                'stroke', 80.4,
                'maxRPM', 8100,
                'turbo', false,
                'cooling', 'liquid-cooled',
                'carburation', 'Electronic Direct Injection',
                'fuelType', 'Unleaded - 95',
                'fuelTank', 37,
                'oilCapacity', 3.4,
                'dryWeight', 238,
                'starter', 'Electric and manual',
                'gaugeType', '10.25 in. touchscreen'
            ),
            JSON_OBJECT(
                'name', '600R E-TEC',
                'type', '2-stroke',
                'displacement', 599.4,
                'bore', 72.3,
                'stroke', 73.0,
                'maxRPM', 8100,
                'turbo', false,
                'cooling', 'liquid-cooled', 
                'carburation', 'Electronic Direct Injection',
                'fuelType', 'Unleaded - 95',
                'fuelTank', 37,
                'oilCapacity', 3.4,
                'dryWeight', 229,
                'starter', 'Electric and manual',
                'gaugeType', '7.2 in. digital'
            )
        ),
        'weight', JSON_OBJECT('min', 229, 'max', 240),
        'dimensions', JSON_OBJECT(
            'overall', JSON_OBJECT('length', 3040, 'width', 1270, 'height', 1140),
            'skiStance', 1097
        ),
        'tracks', JSON_ARRAY(
            JSON_OBJECT('name', 'Cobra', 'dimensions', '381 x 3487 x 41 mm', 'engineCompatibility', '600R'),
            JSON_OBJECT('name', 'Ice Ripper XT studded', 'dimensions', '381 x 3487 x 38 mm', 'engineCompatibility', '850 and 850 Turbo')
        ),
        'suspension', JSON_OBJECT(
            'front', JSON_OBJECT('type', 'LFS-R', 'shock', 'KYB PRO 46 HLCR Kashima'),
            'rear', JSON_OBJECT('type', 'PPS³', 'shock', 'KYB PRO 46 HLCR Kashima'),  
            'center', JSON_OBJECT('shock', 'KYB PRO 46 HLCR Kashima')
        ),
        'powertrain', JSON_OBJECT(
            'driveClutch', 'pDrive with clickers',
            'drivenClutch', 'QRS'
        ),
        'features', JSON_OBJECT(
            'platform', 'Radien²',
            'headlights', 'Premium LED',
            'skis', 'Blade XC+',
            'seating', 'Sport, 1-up',
            'handlebar', 'U-type aluminium with hooks',
            'riserBlockHeight', 90,
            'reverse', 'RER',
            'brakeSystem', 'Brembo 4-Piston with adjustable lever',
            'heatedGrips', true,
            'windshield', 'Low',
            'visorPlug', 'Front',
            'usb', 'Yes, in front compartment',
            'bumpers', 'Std / Std'
        ),
        'colors', JSON_ARRAY(
            JSON_OBJECT('name', 'Viper Red / Black', 'availability', 'standard'),
            JSON_OBJECT('name', 'Black', 'availability', 'spring only')
        )
    )
);

-- Example data for SUMMIT X (single engine variants)
INSERT INTO products (sku, brand, model, configuration, category, model_year, whats_new, package_highlights, spring_options, specifications)
VALUES (
    'SKI-SUMMIT-X-EXPERT-2026',
    'Ski-Doo',
    'Summit X',
    'Expert Package',
    'deep-snow',
    2026,
    JSON_ARRAY(
        'REV Gen5 Lightweight platform',
        '813 mm (32 in.) ski stance',
        'Twin link steering',
        'Super-short tunnel and radiator',
        'Improved Pilot DS 4 skis'
    ),
    JSON_ARRAY(
        'Premium LED headlights',
        'RAS 3 front suspension with 813 mm (32 in.) ski stance',
        'tMotion XT rear suspension with rigid rear arm',
        'PowderMax X-Light 3 in. track with full-width rods',
        'E-TEC SHOT starter standard',
        'Ultra compact and lightweight deep snow seat',
        '10.25 in. touchscreen display with BRP Connect and built-in GPS'
    ),
    JSON_ARRAY(
        'Monument Grey color (850 E-TEC)',
        'Terra Green (850 E-TEC Turbo R)',
        '165" track length'
    ),
    JSON_OBJECT(
        'engines', JSON_ARRAY(
            JSON_OBJECT(
                'name', '850 E-TEC Turbo R',
                'type', '2-stroke',
                'displacement', 849,
                'bore', 82.0,
                'stroke', 80.4,
                'turbo', true,
                'cooling', 'liquid-cooled',
                'fuelSystem', 'E-TEC direct injection with additional booster injectors',
                'fuelType', 'Premium unleaded - 95',
                'fuelTank', 36,
                'oilCapacity', 3.4,
                'dryWeight', 207, -- 154 in.
                'dryWeightVariant', 209 -- 165 in.
            ),
            JSON_OBJECT(
                'name', '850 E-TEC',
                'type', '2-stroke', 
                'displacement', 849,
                'bore', 82.0,
                'stroke', 80.4,
                'turbo', false,
                'cooling', 'liquid-cooled',
                'fuelSystem', 'E-TEC direct injection with additional booster injectors',
                'fuelType', 'Premium unleaded - 95',
                'fuelTank', 36,
                'oilCapacity', 3.4,
                'dryWeight', 199, -- 154 in.
                'dryWeightVariant', 201 -- 165 in.
            )
        ),
        'weight', JSON_OBJECT('min', 199, 'max', 209),
        'dimensions', JSON_OBJECT(
            'overall', JSON_OBJECT('length', 3188, 'width', 971, 'height', 1306),
            'skiStance', 813,
            'fuelCapacity', 36
        ),
        'tracks', JSON_ARRAY(
            JSON_OBJECT('name', 'PowderMax X-Light', 'size', '154 x 16 x 3.0', 'availability', 'standard'),
            JSON_OBJECT('name', 'PowderMax X-Light', 'size', '165 x 16 x 3.0', 'availability', 'spring only')
        ),
        'suspension', JSON_OBJECT(
            'front', JSON_OBJECT('type', 'RAS 3', 'travel', 207, 'shock', 'KYB PRO 36 EA-3'),
            'rear', JSON_OBJECT('type', 'tMotion XT with rigid rear arm', 'travel', 264, 'shock', 'KYB PRO 36 EA-3'),
            'center', JSON_OBJECT('shock', 'KYB 36 Plus')
        ),
        'powertrain', JSON_OBJECT(
            'driveClutch', 'pDrive with clickers',
            'drivenClutch', 'QRS Vent Plus',
            'sprocketPitch', 89
        ),
        'features', JSON_OBJECT(
            'platform', 'REV Gen5',
            'headlights', 'Premium LED',
            'skis', 'Pilot DS 4',
            'seating', 'Deep snow ultra compact',
            'handlebar', 'Tapered with J-hooks / Grab handle / Flexible handguards',
            'riserBlockHeight', 120,
            'starter', 'E-TEC SHOT Starter',
            'reverse', 'RER',
            'brakeSystem', 'Brembo with adjustable lever',
            'heatedGrips', true,
            'gaugeType', '10.25 in. touchscreen display (std on 850 Turbo R) / 4.5 in. digital display',
            'windshield', 'No',
            'runner', '3/8 square – 4',
            'bumpers', 'Standard / Standard'
        ),
        'colors', JSON_ARRAY(
            JSON_OBJECT('name', 'Monument Grey', 'availability', 'spring only on 850 E-TEC'),
            JSON_OBJECT('name', 'Timeless Black', 'availability', 'standard'),
            JSON_OBJECT('name', 'Terra Green', 'availability', 'spring only on 850 E-TEC Turbo R')
        )
    )
);

-- Queries to demonstrate the unified approach

-- Find all models with turbo engines
SELECT brand, model, configuration, has_turbo, engine_count
FROM products 
WHERE has_turbo = true;

-- Get all engine variants for a specific model
SELECT 
    brand, model,
    JSON_EXTRACT(specifications, '$.engines[*].name') as engine_variants,
    JSON_EXTRACT(specifications, '$.engines[*].displacement') as displacements,
    JSON_EXTRACT(specifications, '$.engines[*].dryWeight') as weights
FROM products 
WHERE model = 'Rave RE';

-- Find models by weight range (works with single or multiple engines)
SELECT brand, model, min_dry_weight_kg, max_dry_weight_kg
FROM products
WHERE min_dry_weight_kg <= 230 AND max_dry_weight_kg >= 200;

-- Search by suspension type across all brands
SELECT brand, model, 
       JSON_UNQUOTE(JSON_EXTRACT(specifications, '$.suspension.front.type')) as front_suspension
FROM products
WHERE JSON_EXTRACT(specifications, '$.suspension.front.type') LIKE '%LFS-R%'
   OR JSON_EXTRACT(specifications, '$.suspension.front.type') LIKE '%RAS%';

-- Cross-reference with existing tables
SELECT p.brand, p.model, p.msrp, s.name as supplier_name, c.category_name
FROM products p
JOIN suppliers s ON p.supplier_id = s.id  
JOIN categories c ON p.category_id = c.id
WHERE p.category = 'trail'
ORDER BY p.msrp;

-- ========================================
-- VIEWS FOR SIMPLIFIED ACCESS
-- ========================================

-- Flat view for existing integrations
CREATE VIEW snowmobile_flat_view AS
SELECT 
    id, sku, brand, model, configuration, model_year, category,
    primary_engine_displacement,
    min_dry_weight_kg,
    max_dry_weight_kg,
    msrp,
    has_turbo,
    engine_count,
    JSON_UNQUOTE(JSON_EXTRACT(specifications, '$.features.platform')) as platform,
    JSON_UNQUOTE(JSON_EXTRACT(specifications, '$.suspension.front.type')) as front_suspension,
    JSON_UNQUOTE(JSON_EXTRACT(specifications, '$.suspension.rear.type')) as rear_suspension,
    JSON_UNQUOTE(JSON_EXTRACT(specifications, '$.features.headlights')) as headlights,
    specifications as full_specs
FROM products;

-- Engine details view (flattens multiple engines)
CREATE VIEW engine_variants_view AS
SELECT 
    p.id as product_id,
    p.brand,
    p.model,
    p.configuration,
    JSON_UNQUOTE(engine.name) as engine_name,
    JSON_EXTRACT(engine.displacement) as displacement,
    JSON_UNQUOTE(engine.type) as engine_type,
    JSON_EXTRACT(engine.turbo) as turbo,
    JSON_EXTRACT(engine.dryWeight) as dry_weight,
    JSON_EXTRACT(engine.maxRPM) as max_rpm
FROM products p
JOIN JSON_TABLE(
    p.specifications,
    '$.engines[*]' 
    COLUMNS (
        name VARCHAR(100) PATH '$.name',
        displacement INT PATH '$.displacement',
        type VARCHAR(20) PATH '$.type',
        turbo BOOLEAN PATH '$.turbo',
        dryWeight INT PATH '$.dryWeight',
        maxRPM INT PATH '$.maxRPM'
    )
) as engine;