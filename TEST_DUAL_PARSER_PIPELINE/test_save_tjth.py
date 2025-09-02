"""
Test Saving TJTH Entry to Database
Simple test to save the correctly extracted TJTH data
"""

import sqlite3
import uuid
from datetime import datetime

def test_save_tjth():
    """Test saving the TJTH entry we successfully extracted"""
    
    # This is the correctly extracted TJTH data
    tjth_entry = {
        'tuotenro': 'TJTH',
        'malli': 'Summit',
        'paketti': 'X with Expert Pkg',
        'moottori': '850 E-TEC Turbo R',
        'telamatto': '165in 4200mm 3.0in 76mm Powdermax X-light',
        'kaynnistin': 'SHOT',
        'mittaristo': '10.25 in. Color Touchscreen Display',
        'vari': '165 inch Track, Terra Green Color',
        'price': 27270.0,
        'page_number': 3
    }
    
    print("=== TESTING TJTH DATABASE SAVE ===\n")
    print(f"TJTH Entry to save:")
    for key, value in tjth_entry.items():
        print(f"  {key}: {value}")
    
    # Connect to database
    conn = sqlite3.connect("snowmobile_reconciliation.db")
    cursor = conn.cursor()
    
    try:
        # Insert with all required fields
        cursor.execute("""
            INSERT INTO price_entries (
                id, price_list_id, model_code, malli, paketti, moottori, 
                telamatto, kaynnistin, mittaristo, kevatoptiot, vari, price,
                currency, market, brand, model_year, catalog_lookup_key, status,
                extraction_timestamp, extraction_method, parser_version,
                source_catalog_page, normalized_model_name, normalized_package_name, normalized_engine_spec
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),  # id
            "SKI-DOO_2026_TABULAR",  # price_list_id
            tjth_entry['tuotenro'],  # model_code
            tjth_entry['malli'],  # malli
            tjth_entry['paketti'],  # paketti
            tjth_entry['moottori'],  # moottori
            tjth_entry['telamatto'],  # telamatto
            tjth_entry['kaynnistin'],  # kaynnistin
            tjth_entry['mittaristo'],  # mittaristo
            None,  # kevatoptiot (spring options)
            tjth_entry['vari'],  # vari
            tjth_entry['price'],  # price
            'EUR',  # currency
            'FINLAND',  # market
            'SKI-DOO',  # brand
            2026,  # model_year
            f"SKI-DOO_2026_{tjth_entry['tuotenro']}",  # catalog_lookup_key
            'extracted',  # status
            datetime.now().isoformat(),  # extraction_timestamp
            'tabular_extractor_test',  # extraction_method
            '3.1',  # parser_version
            tjth_entry['page_number'],  # source_catalog_page
            tjth_entry['malli'].upper(),  # normalized_model_name
            tjth_entry['paketti'].upper(),  # normalized_package_name
            tjth_entry['moottori'].upper()  # normalized_engine_spec
        ))
        
        conn.commit()
        print(f"\n[SUCCESS] TJTH entry saved to database!")
        
        # Verify the save
        cursor.execute("""
            SELECT model_code, malli, paketti, moottori, price 
            FROM price_entries 
            WHERE model_code = 'TJTH' AND extraction_method = 'tabular_extractor_test'
        """)
        
        result = cursor.fetchone()
        if result:
            code, malli, paketti, moottori, price = result
            print(f"Verified: {code} | {malli} {paketti} ({moottori}) - {price}€")
        else:
            print(f"[ERROR] Could not verify save")
        
    except Exception as e:
        print(f"[ERROR] Failed to save TJTH: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    test_save_tjth()