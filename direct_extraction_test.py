#!/usr/bin/env python3
"""
Direct extraction test - bypass import issues
Extract data and save directly to production database
"""

import camelot
import sqlite3
from pathlib import Path
from datetime import datetime
import uuid
import re

def extract_and_save():
    """Extract from PDF and save to database"""
    
    print("DIRECT EXTRACTION TO PRODUCTION DB")
    print("=" * 50)
    
    # Paths
    pdf_path = "data/SKI-DOO_2026-PRICE_LIST.pdf"
    db_path = "TEST_DUAL_PARSER_PIPELINE/dual_db.db"
    
    if not Path(pdf_path).exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        return
    
    if not Path(db_path).exists():
        print(f"ERROR: Database not found: {db_path}")
        return
    
    try:
        # Extract tables
        print(f"Extracting tables from: {pdf_path}")
        tables = camelot.read_pdf(pdf_path, flavor='stream', pages='all')
        print(f"Tables found: {len(tables)}")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        price_list_id = f"SKI-DOO_2026_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        total_products = 0
        
        # Process each table
        for table_idx, table in enumerate(tables):
            df = table.df
            print(f"\\nProcessing table {table_idx + 1} (shape: {df.shape}, accuracy: {table.accuracy:.2f})")
            
            # Find header row
            header_row = None
            for row_idx in range(min(10, len(df))):
                row_text = ' '.join(str(cell) for cell in df.iloc[row_idx] if str(cell) != 'nan')
                if 'Malli' in row_text and 'Paketti' in row_text:
                    header_row = row_idx
                    break
            
            if header_row is None:
                print(f"  No header found, skipping table")
                continue
            
            print(f"  Header found at row {header_row}")
            
            # Extract column mapping
            column_mapping = {}
            for col_idx in range(len(df.columns)):
                col_text = ""
                # Check header row and next row
                for h_row in [header_row, header_row + 1]:
                    if h_row < len(df):
                        cell_value = df.iloc[h_row, col_idx]
                        if str(cell_value) != 'nan':
                            col_text += str(cell_value) + " "
                
                col_text = col_text.strip()
                
                # Map columns
                if 'Tuotenro' in col_text or 'nro' in col_text:
                    column_mapping['model_code'] = col_idx
                elif 'Malli' in col_text:
                    column_mapping['malli'] = col_idx
                elif 'Paketti' in col_text:
                    column_mapping['paketti'] = col_idx
                elif 'Moottori' in col_text:
                    column_mapping['moottori'] = col_idx
                elif 'Telamatto' in col_text:
                    column_mapping['telamatto'] = col_idx
                elif 'Käynnistin' in col_text:
                    column_mapping['kaynnistin'] = col_idx
                elif 'Mittaristo' in col_text:
                    column_mapping['mittaristo'] = col_idx
                elif 'Kevätoptiot' in col_text or 'optiot' in col_text:
                    column_mapping['kevatoptiot'] = col_idx
                elif 'Väri' in col_text:
                    column_mapping['vari'] = col_idx
                elif 'Suositushinta' in col_text or 'ALV' in col_text:
                    column_mapping['price'] = col_idx
            
            print(f"  Column mapping: {column_mapping}")
            
            # Extract products - simple row-to-record mapping
            table_products = 0
            
            for row_idx in range(header_row + 2, len(df)):
                row_data = df.iloc[row_idx].tolist()
                
                # Extract all fields from this row using column mapping
                product = {}
                for field, col_idx in column_mapping.items():
                    if col_idx < len(row_data):
                        value = str(row_data[col_idx]).strip()
                        if value and value != 'nan':
                            product[field] = value
                
                # Save each row as a separate record
                if product:  # Only save if we extracted any data
                    save_product_to_db(cursor, product, price_list_id, table_idx + 1)
                    table_products += 1
            
            print(f"  Products extracted: {table_products}")
            total_products += table_products
        
        # Commit and close
        conn.commit()
        conn.close()
        
        print(f"\\nEXTRACTION COMPLETED!")
        print(f"Total products saved: {total_products}")
        
        # Parse raw data into clean products
        parse_raw_data(db_path)
        
        # Verify database
        verify_saved_data(db_path)
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

def save_product_to_db(cursor, product_dict, price_list_id, page_num):
    """Save product to database"""
    
    # Parse price
    price = 0.0
    price_valid = True
    if 'price' in product_dict:
        # Extract only digits, commas, and dots
        price_str = re.sub(r'[^\d,.]', '', product_dict['price'])
        # Replace comma with dot for decimal separator
        price_str = price_str.replace(',', '.')
        try:
            price = float(price_str)
            if price <= 0:
                price_valid = False
                print(f"  WARNING: {product_dict.get('model_code', 'UNKNOWN')} - Invalid price: {price} (SAVING ANYWAY)")
        except:
            price_valid = False
            print(f"  WARNING: {product_dict.get('model_code', 'UNKNOWN')} - Price parsing failed: {product_dict.get('price', 'N/A')} (SAVING ANYWAY)")
            pass
    
    # Normalize fields
    def normalize(text):
        if not text:
            return ""
        return re.sub(r'[^\\w\\s-]', ' ', text.lower().strip())
    
    cursor.execute("""
        INSERT INTO raw_pricelist_data (
            model_code, malli, paketti, moottori, telamatto, 
            kaynnistin, mittaristo, kevatoptiot, vari, price, currency,
            price_list_id, brand, model_year, market, source_catalog_page,
            extraction_timestamp, extraction_method, parser_version,
            normalized_model_name, normalized_package_name, normalized_engine_spec,
            normalized_telamatto, normalized_mittaristo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        product_dict.get('model_code', ''),
        product_dict.get('malli', ''),
        product_dict.get('paketti', ''),
        product_dict.get('moottori', ''),
        product_dict.get('telamatto', ''),
        product_dict.get('kaynnistin', ''),
        product_dict.get('mittaristo', ''),
        product_dict.get('kevatoptiot', ''),
        product_dict.get('vari', ''),
        price,
        'EUR',
        price_list_id,
        'SKI-DOO',
        2026,
        'FINLAND',
        page_num,
        datetime.now().isoformat(),
        'camelot_stream_direct',
        '2.0_camelot_direct',
        normalize(product_dict.get('malli', '')),
        normalize(product_dict.get('paketti', '')),
        normalize(product_dict.get('moottori', '')),
        normalize(product_dict.get('telamatto', '')),
        normalize(product_dict.get('mittaristo', ''))
    ))

def verify_saved_data(db_path):
    """Verify what was saved to database"""
    
    print("\\nDATABASE VERIFICATION")
    print("-" * 30)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Count raw records
    cursor.execute("SELECT COUNT(*) FROM raw_pricelist_data")
    raw_total = cursor.fetchone()[0]
    print(f"Raw records: {raw_total}")
    
    # Count parsed records
    cursor.execute("SELECT COUNT(*) FROM raw_pricelist_data_parsed")
    parsed_total = cursor.fetchone()[0]
    print(f"Parsed records: {parsed_total}")
    
    # Show parsed products sample
    cursor.execute("""
        SELECT model_code, malli, paketti, moottori, price 
        FROM raw_pricelist_data_parsed 
        ORDER BY model_code 
        LIMIT 10
    """)
    
    records = cursor.fetchall()
    print("\\nFirst 10 parsed records:")
    for i, (code, malli, paketti, moottori, price) in enumerate(records):
        print(f"  {i+1:2d}. {code} - {malli} {paketti} - {moottori} - {price}€")
    
    # Show UZT records specifically
    cursor.execute("""
        SELECT model_code, malli, paketti, price 
        FROM raw_pricelist_data_parsed 
        WHERE model_code LIKE '%UZT%' 
        ORDER BY model_code
    """)
    
    uzt_records = cursor.fetchall()
    if uzt_records:
        print("\\nUZT records:")
        for code, malli, paketti, price in uzt_records:
            print(f"  {code} - {malli} {paketti} - {price}€")
    
    # Debug kevatoptiot field
    cursor.execute("""
        SELECT model_code, kevatoptiot 
        FROM raw_pricelist_data_parsed 
        WHERE kevatoptiot IS NOT NULL AND kevatoptiot != ''
        LIMIT 5
    """)
    
    kevat_records = cursor.fetchall()
    print(f"\\nKevatoptiot debug (found {len(kevat_records)} records with data):")
    for code, kevat in kevat_records:
        print(f"  {code}: '{kevat}'")
    
    # Check raw data for kevatoptiot
    cursor.execute("""
        SELECT model_code, kevatoptiot 
        FROM raw_pricelist_data 
        WHERE kevatoptiot IS NOT NULL AND kevatoptiot != ''
        LIMIT 5
    """)
    
    raw_kevat = cursor.fetchall()
    print(f"\\nRaw kevatoptiot debug (found {len(raw_kevat)} records with data):")
    for code, kevat in raw_kevat:
        print(f"  {code}: '{kevat}'")
    
    conn.close()

def parse_raw_data(db_path):
    """Parse raw extracted data into clean products"""
    
    print(f"\nPARSING RAW DATA")
    print("=" * 30)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create raw_pricelist_data_parsed table
        cursor.execute("DROP TABLE IF EXISTS raw_pricelist_data_parsed")
        cursor.execute("""
            CREATE TABLE raw_pricelist_data_parsed (
                model_code TEXT NOT NULL,
                malli TEXT,
                paketti TEXT,
                moottori TEXT,
                telamatto TEXT,
                kaynnistin TEXT,
                mittaristo TEXT,
                kevatoptiot TEXT,
                vari TEXT,
                price REAL,
                currency TEXT DEFAULT 'EUR',
                price_list_id TEXT,
                brand TEXT NOT NULL,
                model_year INTEGER,
                market TEXT DEFAULT 'FINLAND',
                source_catalog_page INTEGER,
                extraction_timestamp TEXT,
                extraction_method TEXT,
                parser_version TEXT,
                normalized_model_name TEXT,
                normalized_package_name TEXT,
                normalized_engine_spec TEXT,
                normalized_telamatto TEXT,
                normalized_mittaristo TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Read all raw data ordered by page and creation time
        cursor.execute("""
            SELECT * FROM raw_pricelist_data 
            ORDER BY source_catalog_page, created_at
        """)
        
        raw_records = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]
        
        print(f"Processing {len(raw_records)} raw records...")
        
        current_product = None
        parsed_count = 0
        
        for record in raw_records:
            record_dict = dict(zip(column_names, record))
            model_code = record_dict.get('model_code', '').strip()
            
            # Check if this is a new product (4-character model code)
            if model_code and len(model_code) == 4:
                # Save previous product if exists
                if current_product:
                    save_parsed_product(cursor, current_product)
                    parsed_count += 1
                
                # Start new product
                current_product = record_dict.copy()
                print(f"  New product: {model_code}")
            
            elif current_product and model_code and not is_header_row(model_code):
                # This is a continuation row with data - merge it
                print(f"    Merging continuation: {model_code} (kevatoptiot: '{record_dict.get('kevatoptiot', '')}')")
                merge_continuation_data(current_product, record_dict)
                print(f"    After merge, current product kevatoptiot: '{current_product.get('kevatoptiot', '')}'")
            
            elif current_product and has_useful_data(record_dict):
                # Row with no model code but has useful data - merge it
                print(f"    Merging no-code row (kevatoptiot: '{record_dict.get('kevatoptiot', '')}')")
                merge_continuation_data(current_product, record_dict)
        
        # Don't forget the last product
        if current_product:
            save_parsed_product(cursor, current_product)
            parsed_count += 1
        
        conn.commit()
        conn.close()
        
        print(f"PARSING COMPLETED!")
        print(f"Parsed products: {parsed_count}")
        
    except Exception as e:
        print(f"PARSING ERROR: {e}")
        import traceback
        traceback.print_exc()

def is_header_row(model_code):
    """Check if this is a header/category row"""
    headers = ['Mid-sized', 'Trail', 'Deep Snow', 'Utility', 'Crossover']
    return model_code in headers

def has_useful_data(record_dict):
    """Check if record has any useful data to merge"""
    useful_fields = ['malli', 'paketti', 'moottori', 'telamatto', 'kaynnistin', 'mittaristo', 'vari']
    return any(record_dict.get(field) for field in useful_fields)

def merge_continuation_data(current_product, new_record):
    """Merge continuation row data into current product"""
    merge_fields = ['malli', 'paketti', 'moottori', 'telamatto', 'kaynnistin', 'mittaristo', 'kevatoptiot', 'vari']
    
    for field in merge_fields:
        new_value = new_record.get(field, '').strip()
        if new_value and new_value != 'nan':
            current_value = current_product.get(field, '').strip()
            if current_value and current_value != new_value:
                # Append new value
                current_product[field] = f"{current_value} {new_value}"
            elif not current_value:
                # Set new value
                current_product[field] = new_value

def save_parsed_product(cursor, product):
    """Save parsed product to database"""
    
    def normalize(text):
        if not text:
            return ""
        return re.sub(r'[^\w\s-]', ' ', text.lower().strip())
    
    cursor.execute("""
        INSERT INTO raw_pricelist_data_parsed (
            model_code, malli, paketti, moottori, telamatto, 
            kaynnistin, mittaristo, kevatoptiot, vari, price, currency,
            price_list_id, brand, model_year, market, source_catalog_page,
            extraction_timestamp, extraction_method, parser_version,
            normalized_model_name, normalized_package_name, normalized_engine_spec,
            normalized_telamatto, normalized_mittaristo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        product.get('model_code', ''),
        product.get('malli', ''),
        product.get('paketti', ''),
        product.get('moottori', ''),
        product.get('telamatto', ''),
        product.get('kaynnistin', ''),
        product.get('mittaristo', ''),
        product.get('kevatoptiot', ''),
        product.get('vari', ''),
        product.get('price', 0),
        'EUR',
        product.get('price_list_id', ''),
        product.get('brand', 'SKI-DOO'),
        product.get('model_year', 2026),
        'FINLAND',
        product.get('source_catalog_page', 0),
        datetime.now().isoformat(),
        'camelot_parsed',
        '2.0_parsed',
        normalize(product.get('malli', '')),
        normalize(product.get('paketti', '')),
        normalize(product.get('moottori', '')),
        normalize(product.get('telamatto', '')),
        normalize(product.get('mittaristo', ''))
    ))

if __name__ == "__main__":
    extract_and_save()