"""
Phase 1 Debug: Transparent Price List Data Inspection
Shows actual data fields, normalization, and database content
"""

import sqlite3
import json
from typing import List, Dict, Any
from data_models import PriceListEntry
from matching_engine import TextNormalizer

def inspect_price_list_data(db_path: str = "snowmobile_reconciliation.db"):
    """Inspect actual price list data with complete transparency"""
    
    print("=== PHASE 1: PRICE LIST DATA INSPECTION ===\n")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get database schema first
        print("1. DATABASE SCHEMA INSPECTION:")
        cursor.execute("PRAGMA table_info(price_entries)")
        columns = cursor.fetchall()
        print(f"   Total columns in price_entries: {len(columns)}")
        print("   Column details:")
        for col in columns:
            print(f"     {col[1]} ({col[2]}) - Not Null: {bool(col[3])}")
        
        # Get total record count
        cursor.execute("SELECT COUNT(*) FROM price_entries")
        total_records = cursor.fetchone()[0]
        print(f"\n   Total records: {total_records}")
        
        print("\n" + "="*80)
        
        # Load first 5 records with all fields
        print("\n2. FIRST 5 PRICE ENTRIES (RAW DATA):")
        cursor.execute("""
            SELECT id, model_code, malli, paketti, moottori, telamatto,
                   kaynnistin, mittaristo, kevatoptiot, vari, price, currency,
                   normalized_model_name, normalized_package_name, normalized_engine_spec
            FROM price_entries 
            ORDER BY model_code 
            LIMIT 5
        """)
        
        records = cursor.fetchall()
        normalizer = TextNormalizer()
        
        for i, record in enumerate(records, 1):
            print(f"\n--- RECORD {i} ---")
            print(f"ID: {record[0]}")
            print(f"Model Code: '{record[1]}'")
            
            print(f"\nRAW FIELDS:")
            print(f"  malli (Finnish model): '{record[2]}'")
            print(f"  paketti (Finnish package): '{record[3]}'")
            print(f"  moottori (engine): '{record[4]}'")
            print(f"  telamatto (track): '{record[5]}'")
            print(f"  kaynnistin (starter): '{record[6]}'")
            print(f"  mittaristo (instrumentation): '{record[7]}'")
            print(f"  kevatoptiot (spring options): '{record[8]}'")
            print(f"  vari (color): '{record[9]}'")
            print(f"  price: {record[10]} {record[11]}")
            
            print(f"\nNORMALIZED FIELDS (from database):")
            print(f"  normalized_model_name: '{record[12]}'")
            print(f"  normalized_package_name: '{record[13]}'")
            print(f"  normalized_engine_spec: '{record[14]}'")
            
            print(f"\nLIVE NORMALIZATION TEST:")
            live_model = normalizer.normalize_model_name(record[2] or "")
            live_package = normalizer.normalize_package_name(record[3] or "")
            live_engine = normalizer.normalize_engine_spec(record[4] or "")
            
            print(f"  live normalized model: '{live_model}'")
            print(f"  live normalized package: '{live_package}'")
            print(f"  live normalized engine: '{live_engine}'")
            
            # Check if database and live normalization match
            db_vs_live_match = (
                (record[12] or "") == live_model and
                (record[13] or "") == live_package and  
                (record[14] or "") == live_engine
            )
            print(f"  Database vs Live normalization match: {db_vs_live_match}")
            
            print("-" * 50)
        
        print("\n" + "="*80)
        
        # Show unique model families
        print("\n3. UNIQUE MODEL FAMILIES ANALYSIS:")
        cursor.execute("""
            SELECT malli, COUNT(*) as count, 
                   GROUP_CONCAT(DISTINCT paketti) as packages
            FROM price_entries 
            WHERE malli IS NOT NULL 
            GROUP BY malli 
            ORDER BY count DESC
        """)
        
        families = cursor.fetchall()
        print(f"Found {len(families)} unique model families:")
        
        for family, count, packages in families:
            packages_list = packages.split(',') if packages else ['None']
            print(f"  '{family}': {count} entries")
            print(f"    Packages: {packages_list}")
            
        print("\n" + "="*80)
        
        # Show normalization effectiveness
        print("\n4. NORMALIZATION EFFECTIVENESS:")
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(normalized_model_name) as has_norm_model,
                COUNT(normalized_package_name) as has_norm_package,
                COUNT(normalized_engine_spec) as has_norm_engine
            FROM price_entries
        """)
        
        norm_stats = cursor.fetchone()
        print(f"Total entries: {norm_stats[0]}")
        print(f"Has normalized model name: {norm_stats[1]} ({norm_stats[1]/norm_stats[0]*100:.1f}%)")
        print(f"Has normalized package name: {norm_stats[2]} ({norm_stats[2]/norm_stats[0]*100:.1f}%)")
        print(f"Has normalized engine spec: {norm_stats[3]} ({norm_stats[3]/norm_stats[0]*100:.1f}%)")
        
        # Show sample normalized values
        print(f"\nSAMPLE NORMALIZED VALUES:")
        cursor.execute("""
            SELECT DISTINCT normalized_model_name 
            FROM price_entries 
            WHERE normalized_model_name IS NOT NULL 
            ORDER BY normalized_model_name 
            LIMIT 10
        """)
        
        norm_models = [row[0] for row in cursor.fetchall()]
        print(f"Sample normalized model names: {norm_models}")
        
        cursor.execute("""
            SELECT DISTINCT normalized_package_name 
            FROM price_entries 
            WHERE normalized_package_name IS NOT NULL AND normalized_package_name != ''
            ORDER BY normalized_package_name 
            LIMIT 10
        """)
        
        norm_packages = [row[0] for row in cursor.fetchall()]
        print(f"Sample normalized package names: {norm_packages}")
        
        print("\n" + "="*80)
        
        # Test normalization on specific examples
        print("\n5. NORMALIZATION ALGORITHM TESTING:")
        
        test_cases = [
            ("Summit X-RS", "Expert Package", "850 E-TEC TURBO R"),
            ("MXZ X-RS", "Competition Package", "600R E-TEC"),
            ("Expedition", "Xtreme", "900 ACE TURBO R"),
            ("Renegade", "", "850 E-TEC"),
            ("Backcountry", "Adrenaline", "850 E-TEC")
        ]
        
        for model, package, engine in test_cases:
            print(f"\nTest case: '{model}' + '{package}' + '{engine}'")
            print(f"  Normalized model: '{normalizer.normalize_model_name(model)}'")
            print(f"  Normalized package: '{normalizer.normalize_package_name(package)}'") 
            print(f"  Normalized engine: '{normalizer.normalize_engine_spec(engine)}'")
        
        print(f"\n=== PHASE 1 COMPLETE: Price list data inspection finished ===")
        
        return {
            'total_records': total_records,
            'sample_records': records,
            'model_families': families,
            'normalization_stats': norm_stats
        }
        
    except Exception as e:
        print(f"Error during price list inspection: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_price_list_data()