#!/usr/bin/env python3
"""
Test Camelot Stream method on SKI-DOO_2026-PRICE_LIST.pdf
Analyze exact table structure and column mapping
"""

import camelot
import pandas as pd
from pathlib import Path

def test_camelot_extraction():
    """Test Camelot on SKI-DOO 2026 price list"""
    pdf_path = "data/SKI-DOO_2026-PRICE_LIST.pdf"
    
    if not Path(pdf_path).exists():
        print(f"ERROR: File not found: {pdf_path}")
        return
    
    print("CAMELOT STREAM METHOD TEST")
    print("=" * 50)
    print(f"File: {pdf_path}")
    
    try:
        # Extract tables using Stream method
        tables = camelot.read_pdf(pdf_path, flavor='stream', pages='all')
        
        print(f"Tables found: {len(tables)}")
        
        for i, table in enumerate(tables):
            print(f"\\nTABLE {i+1}")
            print("-" * 30)
            print(f"Shape: {table.df.shape}")
            print(f"Accuracy: {table.accuracy:.2f}")
            print(f"Page: {table.page}")
            
            # Show column headers (first row)
            print(f"\\nColumn Headers (Row 0):")
            headers = table.df.iloc[0].tolist()
            for j, header in enumerate(headers):
                print(f"  Col {j}: '{header}'")
            
            # Show first few data rows
            print(f"\\nFirst 3 data rows:")
            for row_idx in range(min(4, len(table.df))):
                row_data = table.df.iloc[row_idx].tolist()
                print(f"  Row {row_idx}: {row_data}")
            
            # Check for Finnish field names
            print(f"\\nFinnish field detection:")
            finnish_fields = ['Tuotenro', 'Malli', 'Paketti', 'Moottori', 'Telamatto', 
                            'Käynnistin', 'Mittaristo', 'Kevätoptiot', 'Väri', 'Suositushinta']
            
            table_text = table.df.to_string()
            found_fields = []
            for field in finnish_fields:
                if field in table_text:
                    found_fields.append(field)
            
            print(f"  Found: {found_fields}")
            
            # Save table as CSV for inspection
            csv_filename = f"results/table_{i+1}_structure.csv"
            Path("results").mkdir(exist_ok=True)
            table.df.to_csv(csv_filename, index=False, encoding='utf-8')
            print(f"  Saved to: {csv_filename}")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_camelot_extraction()