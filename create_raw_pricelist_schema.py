#!/usr/bin/env python3
"""
Create clean raw_pricelist_data table schema
Drop existing price_entries and create new clean table
"""

import sqlite3
from pathlib import Path

def create_clean_schema():
    """Create clean raw_pricelist_data table"""
    
    db_path = "TEST_DUAL_PARSER_PIPELINE/dual_db.db"
    
    if not Path(db_path).exists():
        print(f"ERROR: Database not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("CREATING CLEAN RAW_PRICELIST_DATA SCHEMA")
        print("=" * 50)
        
        # Drop existing price_entries table
        print("Dropping existing price_entries table...")
        cursor.execute("DROP TABLE IF EXISTS price_entries")
        
        # Create new clean raw_pricelist_data table
        print("Creating raw_pricelist_data table...")
        cursor.execute("""
            CREATE TABLE raw_pricelist_data (
                -- Raw Finnish Data 
                model_code TEXT NOT NULL,      -- Tuotenro
                malli TEXT,                    -- Malli
                paketti TEXT,                  -- Paketti  
                moottori TEXT,                 -- Moottori
                telamatto TEXT,                -- Telamatto
                kaynnistin TEXT,               -- Käynnistin
                mittaristo TEXT,               -- Mittaristo
                kevatoptiot TEXT,              -- Kevätoptiot
                vari TEXT,                     -- Väri
                price REAL,                    -- Can be 0 for missing prices
                currency TEXT DEFAULT 'EUR',
                
                -- Source Metadata
                price_list_id TEXT,            -- Links to source document
                brand TEXT NOT NULL,           -- SKI-DOO/LYNX
                model_year INTEGER,            -- 2026
                market TEXT DEFAULT 'FINLAND',
                source_catalog_page INTEGER,   -- PDF page number
                
                -- Processing Metadata  
                extraction_timestamp TEXT,
                extraction_method TEXT,        -- 'camelot_stream'
                parser_version TEXT,           -- Track code version
                
                -- Normalized Data (for matching)
                normalized_model_name TEXT,
                normalized_package_name TEXT, 
                normalized_engine_spec TEXT,
                normalized_telamatto TEXT,     -- Cleaned track spec
                normalized_mittaristo TEXT,    -- Cleaned display spec
                
                -- Timestamps
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Verify table creation
        cursor.execute("PRAGMA table_info(raw_pricelist_data)")
        columns = cursor.fetchall()
        
        print(f"Table created successfully with {len(columns)} columns:")
        for i, col in enumerate(columns):
            name, type_, notnull = col[1], col[2], col[3]
            print(f"  {i+1:2d}. {name:<25} {type_:<10} {'NOT NULL' if notnull else ''}")
        
        conn.commit()
        conn.close()
        
        print("\\nSCHEMA CREATION COMPLETED!")
        print("Ready for PDFExtractor to populate raw_pricelist_data table")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_clean_schema()