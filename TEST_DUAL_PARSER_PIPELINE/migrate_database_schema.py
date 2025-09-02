import sqlite3
from pathlib import Path

def migrate_database_schema(db_path: str = "snowmobile_reconciliation.db"):
    """Add new fields for matching metadata and image data to existing database"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("=== DATABASE SCHEMA MIGRATION ===")
        print(f"Updating database: {db_path}")
        
        # Check if price_entries table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='price_entries'")
        if not cursor.fetchone():
            print("Error: price_entries table not found")
            return False
        
        # Add new columns to price_entries table for catalog matching
        new_columns = [
            ("matching_method", "VARCHAR(50)"),
            ("matching_confidence", "DECIMAL(3,3)"),
            ("confidence_description", "VARCHAR(100)"),
            ("matching_notes", "TEXT"),
            ("extraction_timestamp", "TIMESTAMP"),
            ("source_catalog_name", "VARCHAR(255)"),
            ("source_catalog_page", "INTEGER"),
            ("source_catalog_section", "VARCHAR(255)"),
            ("price_list_source", "VARCHAR(255)"),
            ("extraction_method", "VARCHAR(50)"),
            ("parser_version", "VARCHAR(20)"),
            ("has_image_data", "BOOLEAN DEFAULT FALSE"),
            ("images_processed", "INTEGER DEFAULT 0"),
            # Claude-recommended fields for Model+Package matching
            ("normalized_model_name", "VARCHAR(200)"),
            ("normalized_package_name", "VARCHAR(100)"), 
            ("normalized_engine_spec", "VARCHAR(100)"),
            ("dual_parser_stage", "VARCHAR(50) DEFAULT 'pending'"),
            ("stage_completion_flags", "TEXT"), # JSON in SQLite
            ("spring_options_raw", "TEXT"),
            ("spring_options_parsed", "TEXT") # JSON in SQLite
        ]
        
        print("Adding new columns to price_entries table:")
        for column_name, column_type in new_columns:
            try:
                cursor.execute(f"ALTER TABLE price_entries ADD COLUMN {column_name} {column_type}")
                print(f"  [OK] Added column: {column_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"  [SKIP] Column {column_name} already exists")
                else:
                    print(f"  [ERROR] Error adding column {column_name}: {e}")
        
        # Create new table for catalog entries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS catalog_entries (
                id TEXT PRIMARY KEY,
                vehicle_name TEXT NOT NULL,
                model_family TEXT,
                page_number INTEGER,
                specifications TEXT,  -- JSON
                features TEXT,        -- JSON  
                marketing TEXT,       -- JSON
                dimensions TEXT,      -- JSON
                performance TEXT,     -- JSON
                options TEXT,         -- JSON
                powertrain TEXT,      -- JSON
                suspension TEXT,      -- JSON
                tracks TEXT,          -- JSON
                colors TEXT,          -- JSON
                -- Matching metadata
                matching_method VARCHAR(50),
                matching_confidence DECIMAL(3,3),
                confidence_description VARCHAR(100),
                matching_notes TEXT,
                extraction_timestamp TIMESTAMP,
                source_catalog_name VARCHAR(255),
                source_catalog_page INTEGER,
                price_list_model_code VARCHAR(10),
                extraction_method VARCHAR(50),
                parser_version VARCHAR(20),
                -- Image data
                has_image_data BOOLEAN DEFAULT FALSE,
                images_processed INTEGER DEFAULT 0,
                main_product_image VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("[OK] Created catalog_entries table")
        
        # Create table for product images
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_images (
                id TEXT PRIMARY KEY,
                vehicle_id TEXT REFERENCES catalog_entries(id),
                vehicle_name TEXT NOT NULL,
                image_filename VARCHAR(255) NOT NULL,
                image_path VARCHAR(500) NOT NULL,
                page_number INTEGER,
                image_index INTEGER,
                width INTEGER,
                height INTEGER,
                image_type VARCHAR(50), -- MAIN_PRODUCT/COLOR_VARIANT/DETAIL/TECHNICAL
                dominant_colors TEXT,   -- JSON
                features_visible TEXT,  -- JSON
                quality_score DECIMAL(3,2),
                extraction_timestamp TIMESTAMP,
                source_catalog VARCHAR(255),
                extraction_method VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("[OK] Created product_images table")
        
        # Create Claude-recommended tables for Model+Package decomposition
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS package_definitions (
                id TEXT PRIMARY KEY,
                brand VARCHAR(50) NOT NULL,
                model_family VARCHAR(100) NOT NULL,
                package_name VARCHAR(100) NOT NULL,
                package_code VARCHAR(20),
                model_year INTEGER NOT NULL,
                package_type VARCHAR(50),
                base_model_indicator BOOLEAN DEFAULT 0,
                engine_modifications TEXT, -- JSON
                suspension_modifications TEXT, -- JSON
                track_modifications TEXT, -- JSON
                feature_additions TEXT, -- JSON
                english_equivalents TEXT, -- JSON
                finnish_variants TEXT, -- JSON
                confidence_score DECIMAL(3,2) DEFAULT 0.85,
                human_verified BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        print("[OK] Created package_definitions table")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_code_mappings (
                id TEXT PRIMARY KEY,
                model_code CHAR(4) NOT NULL,
                malli VARCHAR(100) NOT NULL,
                paketti VARCHAR(100),
                english_model_name VARCHAR(200) NOT NULL,
                english_package_name VARCHAR(100),
                base_model_id VARCHAR(100) NOT NULL,
                matching_method VARCHAR(50) NOT NULL,
                matching_confidence DECIMAL(3,2) NOT NULL,
                matching_algorithm_version VARCHAR(20) DEFAULT '1.0',
                created_by VARCHAR(50) DEFAULT 'system',
                verification_status VARCHAR(30) DEFAULT 'pending',
                manual_override BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        print("[OK] Created model_code_mappings table")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dual_parser_matching_results (
                id TEXT PRIMARY KEY,
                price_entry_id TEXT NOT NULL REFERENCES price_entries(id),
                catalog_entry_id TEXT REFERENCES catalog_entries(id),
                tier_1_exact_match BOOLEAN DEFAULT 0,
                tier_1_confidence DECIMAL(3,2) DEFAULT 0.0,
                tier_2_normalized_match BOOLEAN DEFAULT 0,
                tier_2_confidence DECIMAL(3,2) DEFAULT 0.0,
                tier_2_transformations TEXT, -- JSON
                tier_3_fuzzy_match BOOLEAN DEFAULT 0,
                tier_3_confidence DECIMAL(3,2) DEFAULT 0.0,
                tier_3_algorithms TEXT, -- JSON
                final_matching_method VARCHAR(50) NOT NULL,
                overall_confidence DECIMAL(3,2) NOT NULL,
                requires_human_review BOOLEAN DEFAULT 0,
                data_quality_issues TEXT, -- JSON
                spring_options_detected INTEGER DEFAULT 0,
                specification_conflicts TEXT, -- JSON
                processing_duration_ms INTEGER,
                claude_tokens_used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("[OK] Created dual_parser_matching_results table")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dual_parser_configuration (
                config_key VARCHAR(100) PRIMARY KEY,
                config_value TEXT NOT NULL, -- JSON
                config_description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                updated_by VARCHAR(100)
            )
        """)
        print("[OK] Created dual_parser_configuration table")
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_catalog_matching ON catalog_entries(matching_method, matching_confidence)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_images_vehicle ON product_images(vehicle_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_entries_model_code ON price_entries(model_code)")
        
        # Claude-recommended indexes for Model+Package matching
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_entries_model_package ON price_entries(malli, paketti, moottori)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_entries_normalized ON price_entries(normalized_model_name, normalized_package_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_package_definitions_lookup ON package_definitions(brand, model_family, package_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_code_mappings_lookup ON model_code_mappings(model_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_code_mappings_english ON model_code_mappings(english_model_name, english_package_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_code_mappings_confidence ON model_code_mappings(matching_confidence DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matching_results_confidence ON dual_parser_matching_results(overall_confidence DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matching_results_method ON dual_parser_matching_results(final_matching_method)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matching_results_review ON dual_parser_matching_results(requires_human_review)")
        print("[OK] Created performance indexes")
        
        # Insert default configuration
        cursor.execute("""
            INSERT OR REPLACE INTO dual_parser_configuration (config_key, config_value, config_description) VALUES
            ('exact_match_threshold', '0.95', 'Minimum confidence for tier 1 exact matches'),
            ('normalized_match_threshold', '0.85', 'Minimum confidence for tier 2 normalized matches'),
            ('fuzzy_match_threshold', '0.7', 'Minimum confidence for tier 3 fuzzy matches'),
            ('auto_accept_threshold', '0.9', 'Confidence threshold for auto-acceptance'),
            ('normalization_rules', '{"remove_chars": ["-", "_"], "case_insensitive": true}', 'Text normalization rules')
        """)
        print("[OK] Inserted default configuration")
        
        conn.commit()
        print("\n=== MIGRATION COMPLETED SUCCESSFULLY ===\nClaude-enhanced schema with Model+Package decomposition tables created!")
        
        # Display current schema
        cursor.execute("PRAGMA table_info(price_entries)")
        price_columns = cursor.fetchall()
        print(f"\nUpdated price_entries table has {len(price_columns)} columns:")
        for col in price_columns[-5:]:  # Show last 5 new columns
            print(f"  {col[1]} {col[2]}")
        
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        print(f"\nDatabase now has {table_count} tables total")
        
        return True
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def verify_migration(db_path: str = "snowmobile_reconciliation.db"):
    """Verify the migration was successful"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("\n=== MIGRATION VERIFICATION ===")
        
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['price_lists', 'price_entries', 'catalog_entries', 'product_images', 'package_definitions', 'model_code_mappings', 'dual_parser_matching_results', 'dual_parser_configuration']
        for table in expected_tables:
            if table in tables:
                print(f"[OK] Table {table} exists")
            else:
                print(f"[MISSING] Table {table} missing")
        
        # Check new columns in price_entries
        cursor.execute("PRAGMA table_info(price_entries)")
        columns = [row[1] for row in cursor.fetchall()]
        
        expected_new_columns = ['matching_method', 'matching_confidence', 'confidence_description']
        for col in expected_new_columns:
            if col in columns:
                print(f"[OK] Column {col} added to price_entries")
            else:
                print(f"[MISSING] Column {col} missing from price_entries")
        
        print("[OK] Migration verification completed")
        
    except Exception as e:
        print(f"Error during verification: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    success = migrate_database_schema()
    if success:
        verify_migration()
    else:
        print("Migration failed!")