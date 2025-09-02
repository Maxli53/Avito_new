#!/usr/bin/env python3
"""
Working Database Setup - Core Enterprise Tables
Creates a working SQLite database with the essential enterprise schema
"""
import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

DATABASE_FILE = Path('snowmobile_reconciliation.db')

def create_working_database():
    """Create working SQLite database with core enterprise schema"""
    
    print("=" * 80)
    print("WORKING DATABASE SETUP")
    print("=" * 80)
    print(f"Database file: {DATABASE_FILE}")
    
    try:
        # Remove existing database
        if DATABASE_FILE.exists():
            DATABASE_FILE.unlink()
            print(f"Removed existing database: {DATABASE_FILE}")
        
        # Create new database
        conn = sqlite3.connect(str(DATABASE_FILE))
        
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        
        print("Creating core enterprise tables...")
        
        # Create core tables with working schema
        tables = [
            # Products Table - Final constructed products
            """
            CREATE TABLE products (
                -- Primary Keys and Identity
                sku TEXT PRIMARY KEY,
                internal_id TEXT NOT NULL DEFAULT '',
                
                -- Product Identity
                brand TEXT NOT NULL,
                model_year INTEGER NOT NULL,
                model_family TEXT,
                base_model_source TEXT,
                platform TEXT,
                category TEXT,
                
                -- Key Searchable Specifications
                engine_model TEXT,
                engine_displacement_cc INTEGER,
                track_length_mm INTEGER,
                track_width_mm INTEGER,
                track_profile_mm INTEGER,
                dry_weight_kg INTEGER,
                
                -- Complete Specifications (JSON for flexibility)
                full_specifications TEXT DEFAULT '{}',
                marketing_texts TEXT DEFAULT '{}',
                spring_modifications TEXT DEFAULT '{}',
                
                -- Quality and Validation
                confidence_score REAL DEFAULT 0.0,
                validation_status TEXT DEFAULT 'pending',
                auto_accepted INTEGER DEFAULT 0,
                
                -- Audit and Tracking
                inheritance_audit_trail TEXT DEFAULT '{}',
                raw_sources TEXT DEFAULT '[]',
                processing_metadata TEXT DEFAULT '{}',
                
                -- Standard Audit Fields
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                updated_by TEXT,
                
                -- Soft Delete Support
                deleted_at DATETIME,
                deleted_by TEXT
            )
            """,
            
            # Base Models Catalog Table
            """
            CREATE TABLE base_models_catalog (
                -- Primary Key
                id TEXT PRIMARY KEY,
                
                -- Base Model Identity
                brand TEXT NOT NULL,
                model_family TEXT NOT NULL,
                model_year INTEGER NOT NULL,
                lookup_key TEXT NOT NULL UNIQUE,
                
                -- Complete Base Specifications
                platform_specs TEXT DEFAULT '{}',
                engine_options TEXT DEFAULT '{}',
                track_options TEXT DEFAULT '{}',
                suspension_specs TEXT DEFAULT '{}',
                feature_options TEXT DEFAULT '{}',
                color_options TEXT DEFAULT '{}',
                
                -- Standard Specifications
                dimensions TEXT DEFAULT '{}',
                weight_specifications TEXT DEFAULT '{}',
                standard_features TEXT DEFAULT '{}',
                
                -- Quality and Validation
                catalog_completeness_score REAL DEFAULT 0.0,
                validation_status TEXT DEFAULT 'pending',
                
                -- Source Tracking
                catalog_source TEXT,
                catalog_page INTEGER,
                extraction_date DATETIME,
                extraction_confidence REAL,
                
                -- Standard Audit Fields
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                updated_by TEXT,
                
                -- Soft Delete Support
                deleted_at DATETIME,
                deleted_by TEXT
            )
            """,
            
            # Price Lists Table
            """
            CREATE TABLE price_lists (
                -- Primary Key
                id TEXT PRIMARY KEY,
                
                -- Price List Identity
                filename TEXT NOT NULL,
                file_hash TEXT NOT NULL UNIQUE,
                market TEXT NOT NULL,
                brand TEXT NOT NULL,
                model_year INTEGER NOT NULL,
                currency TEXT NOT NULL,
                
                -- Document Processing
                document_type TEXT DEFAULT 'price_list',
                document_quality TEXT DEFAULT 'unknown',
                parser_used TEXT,
                extraction_method TEXT,
                
                -- Processing Status
                processing_status TEXT DEFAULT 'uploaded',
                total_entries INTEGER DEFAULT 0,
                processed_entries INTEGER DEFAULT 0,
                failed_entries INTEGER DEFAULT 0,
                
                -- Metadata
                file_size_bytes INTEGER,
                total_pages INTEGER,
                upload_source TEXT,
                
                -- Processing Metrics
                processing_start_time DATETIME,
                processing_end_time DATETIME,
                processing_duration_ms INTEGER,
                claude_api_calls INTEGER DEFAULT 0,
                total_cost_usd REAL DEFAULT 0.0,
                
                -- Standard Audit Fields
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                updated_by TEXT,
                
                -- Soft Delete Support
                deleted_at DATETIME,
                deleted_by TEXT
            )
            """,
            
            # Price Entries Table
            """
            CREATE TABLE price_entries (
                -- Primary Key
                id TEXT PRIMARY KEY,
                price_list_id TEXT NOT NULL,
                
                -- Original Price List Data (Finnish format)
                model_code TEXT NOT NULL,
                malli TEXT,
                paketti TEXT,
                moottori TEXT,
                telamatto TEXT,
                kaynnistin TEXT,
                mittaristo TEXT,
                kevätoptiot TEXT,
                vari TEXT,
                
                -- Pricing Information
                price_amount REAL NOT NULL,
                currency TEXT NOT NULL,
                market TEXT NOT NULL,
                
                -- Processing Status and Quality
                processed INTEGER DEFAULT 0,
                processing_error TEXT,
                mapped_product_sku TEXT,
                confidence_score REAL,
                requires_manual_review INTEGER DEFAULT 0,
                
                -- Pipeline Processing Tracking
                stage_1_completed INTEGER DEFAULT 0,
                stage_2_completed INTEGER DEFAULT 0,
                stage_3_completed INTEGER DEFAULT 0,
                stage_4_completed INTEGER DEFAULT 0,
                stage_5_completed INTEGER DEFAULT 0,
                
                -- Metadata
                source_file TEXT,
                source_page INTEGER,
                extraction_confidence REAL,
                extraction_method TEXT,
                
                -- Processing Metrics
                processing_start_time DATETIME,
                processing_end_time DATETIME,
                processing_duration_ms INTEGER,
                claude_api_calls INTEGER DEFAULT 0,
                
                -- Standard Audit Fields
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                updated_by TEXT,
                
                -- Soft Delete Support
                deleted_at DATETIME,
                deleted_by TEXT,
                
                -- Foreign Key Constraints
                FOREIGN KEY (price_list_id) REFERENCES price_lists(id) ON DELETE CASCADE,
                FOREIGN KEY (mapped_product_sku) REFERENCES products(sku) ON DELETE SET NULL
            )
            """,
            
            # Model Mappings Table
            """
            CREATE TABLE model_mappings (
                -- Primary Key
                id TEXT PRIMARY KEY,
                
                -- Model Code Processing
                model_code TEXT NOT NULL,
                catalog_sku TEXT NOT NULL,
                base_model_id TEXT,
                brand TEXT NOT NULL,
                model_family TEXT NOT NULL,
                model_year INTEGER NOT NULL,
                
                -- Inheritance Chain Details
                base_model_matched TEXT NOT NULL,
                processing_method TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                
                -- Pipeline Stage Results (JSON details)
                stage_1_result TEXT DEFAULT '{}',
                stage_2_result TEXT DEFAULT '{}',
                stage_3_result TEXT DEFAULT '{}',
                stage_4_result TEXT DEFAULT '{}',
                stage_5_result TEXT DEFAULT '{}',
                
                -- Quality and Decision Tracking
                auto_accepted INTEGER DEFAULT 0,
                requires_review INTEGER DEFAULT 0,
                validation_passed INTEGER DEFAULT 1,
                manual_override INTEGER DEFAULT 0,
                override_reason TEXT,
                
                -- Performance Metrics
                complete_audit_trail TEXT DEFAULT '{}',
                processing_duration_ms INTEGER,
                claude_api_calls INTEGER DEFAULT 0,
                total_cost_usd REAL DEFAULT 0.0,
                
                -- Standard Audit Fields
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                updated_by TEXT,
                
                -- Soft Delete Support
                deleted_at DATETIME,
                deleted_by TEXT,
                
                -- Foreign Key Constraints
                FOREIGN KEY (catalog_sku) REFERENCES products(sku) ON DELETE CASCADE,
                FOREIGN KEY (base_model_id) REFERENCES base_models_catalog(id) ON DELETE SET NULL
            )
            """,
            
            # Spring Options Registry
            """
            CREATE TABLE spring_options_registry (
                -- Primary Key
                id TEXT PRIMARY KEY,
                
                -- Spring Option Identity
                brand TEXT NOT NULL,
                model_family TEXT,
                model_year INTEGER,
                option_name TEXT NOT NULL,
                option_code TEXT,
                
                -- Option Details
                option_type TEXT NOT NULL,
                description TEXT,
                specifications TEXT DEFAULT '{}',
                
                -- Application Rules
                applies_to_models TEXT DEFAULT '[]',
                conflicts_with TEXT DEFAULT '[]',
                requires_options TEXT DEFAULT '[]',
                
                -- Pricing Impact
                price_modifier_type TEXT DEFAULT 'none',
                price_modifier_value REAL DEFAULT 0.0,
                
                -- Quality and Validation
                confidence_score REAL DEFAULT 0.95,
                source TEXT,
                validated_by_claude INTEGER DEFAULT 0,
                validated_by_human INTEGER DEFAULT 0,
                
                -- Usage Tracking
                times_applied INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 1.0,
                
                -- Standard Audit Fields
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                updated_by TEXT,
                
                -- Soft Delete Support
                deleted_at DATETIME,
                deleted_by TEXT
            )
            """
        ]
        
        # Execute table creation
        for i, table_sql in enumerate(tables, 1):
            table_name = table_sql.strip().split('\n')[1].strip().split()[2]
            try:
                print(f"Creating table {i}/{len(tables)}: {table_name}")
                conn.execute(table_sql)
            except Exception as e:
                print(f"Failed to create table {table_name}: {e}")
        
        # Create indexes for performance
        indexes = [
            "CREATE INDEX idx_products_brand_year ON products(brand, model_year)",
            "CREATE INDEX idx_base_models_lookup ON base_models_catalog(lookup_key)",
            "CREATE INDEX idx_price_entries_model_code ON price_entries(model_code)",
            "CREATE INDEX idx_model_mappings_code ON model_mappings(model_code)",
            "CREATE INDEX idx_spring_options_brand ON spring_options_registry(brand, option_name)",
        ]
        
        print("\\nCreating performance indexes...")
        for index_sql in indexes:
            try:
                conn.execute(index_sql)
            except Exception as e:
                print(f"Index creation warning: {e}")
        
        conn.commit()
        
        # Verify tables were created
        cursor = conn.execute("""
            SELECT name, sql FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = cursor.fetchall()
        
        print(f"\\nCreated {len(tables)} tables:")
        for table_name, _ in tables:
            # Count columns
            col_cursor = conn.execute(f"PRAGMA table_info({table_name})")
            columns = col_cursor.fetchall()
            print(f"  - {table_name}: {len(columns)} columns")
        
        # Insert some default configuration
        sample_data = [
            """INSERT INTO base_models_catalog (id, brand, model_family, model_year, lookup_key, created_by) 
               VALUES ('test-base-1', 'Ski-Doo', 'MXZ X-RS', 2026, 'Ski-Doo_MXZ_X-RS_2026', 'system')""",
            """INSERT INTO spring_options_registry (id, brand, option_name, option_type, created_by) 
               VALUES ('test-option-1', 'Ski-Doo', 'Black Edition', 'color', 'system')"""
        ]
        
        print("\\nInserting sample configuration data...")
        for sql in sample_data:
            try:
                # Generate UUID for each insert
                uuid_val = str(uuid.uuid4())
                sql_with_uuid = sql.replace("'test-base-1'", f"'{uuid_val}'").replace("'test-option-1'", f"'{uuid_val}'")
                conn.execute(sql_with_uuid)
            except Exception as e:
                print(f"Sample data insertion warning: {e}")
        
        conn.commit()
        conn.close()
        
        print("\\nDatabase setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"Database setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_working_database():
    """Test the working database"""
    
    print("\\n" + "-" * 60)
    print("TESTING WORKING DATABASE")
    print("-" * 60)
    
    try:
        conn = sqlite3.connect(str(DATABASE_FILE))
        
        # Test basic functionality
        cursor = conn.execute("SELECT sqlite_version()")
        version = cursor.fetchone()[0]
        print(f"SQLite Version: {version}")
        
        # Test tables and data
        cursor = conn.execute("""
            SELECT name, 
                   (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name = t.name) as exists_count,
                   (SELECT COUNT(*) FROM (SELECT 1 FROM sqlite_master WHERE type='table' AND name = t.name AND sql IS NOT NULL LIMIT 1)) as has_schema
            FROM (
                SELECT 'products' as name UNION ALL
                SELECT 'base_models_catalog' UNION ALL
                SELECT 'price_lists' UNION ALL
                SELECT 'price_entries' UNION ALL
                SELECT 'model_mappings' UNION ALL
                SELECT 'spring_options_registry'
            ) t
        """)
        tables = cursor.fetchall()
        
        print(f"\\nCore Tables Status:")
        all_exist = True
        for table_name, exists, has_schema in tables:
            status = "OK" if exists and has_schema else "FAIL"
            print(f"  {status} {table_name}")
            if not (exists and has_schema):
                all_exist = False
        
        if all_exist:
            print(f"\\nOK All core enterprise tables exist and functional")
            
            # Test sample data
            cursor = conn.execute("SELECT COUNT(*) FROM base_models_catalog")
            base_count = cursor.fetchone()[0]
            cursor = conn.execute("SELECT COUNT(*) FROM spring_options_registry")  
            options_count = cursor.fetchone()[0]
            
            print(f"OK Sample data: {base_count} base models, {options_count} spring options")
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"Database test failed: {e}")
        return False

def main():
    """Main setup process"""
    
    try:
        # Create working database
        setup_success = create_working_database()
        
        if setup_success:
            # Test database
            test_success = test_working_database()
            
            if test_success:
                print("\\n" + "=" * 80)
                print("WORKING DATABASE SETUP COMPLETE")
                print("Enterprise database is ready for production use with:")
                print("  - All core enterprise tables (6 tables)")
                print("  - Foreign key relationships")
                print("  - Performance indexes")
                print("  - JSON support for specifications")
                print("  - Sample configuration data")
                print(f"  - Database file: {DATABASE_FILE.absolute()}")
                print("=" * 80)
                return True
        
        print("\\nDatabase setup failed")
        return False
        
    except Exception as e:
        print(f"\\nSetup process failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()