#!/usr/bin/env python3
"""Debug UZT record extraction specifically"""

import camelot
import pandas as pd
import re

def debug_uzt_extraction():
    """Debug the UZT records extraction"""
    
    pdf_path = "data/SKI-DOO_2026-PRICE_LIST.pdf"
    
    print("DEBUGGING UZT EXTRACTION")
    print("=" * 50)
    
    # Extract table 2 where UZT records are located
    tables = camelot.read_pdf(pdf_path, flavor='stream', pages='all')
    table = tables[1]  # Table 2 (0-indexed)
    df = table.df
    
    print(f"Table 2 shape: {df.shape}")
    print(f"Table 2 accuracy: {table.accuracy:.2f}")
    
    # Find header row
    header_row = None
    for row_idx in range(min(10, len(df))):
        row_text = ' '.join(str(cell) for cell in df.iloc[row_idx] if str(cell) != 'nan')
        if 'Malli' in row_text and 'Paketti' in row_text:
            header_row = row_idx
            break
    
    print(f"Header row: {header_row}")
    
    # Look at rows around UZT records (rows 25-45)
    print(f"\nRows around UZT records:")
    for row_idx in range(25, 45):
        if row_idx < len(df):
            row_data = df.iloc[row_idx].tolist()
            # Check model code column (should be column 1)
            model_cell = str(row_data[1]).strip() if len(row_data) > 1 else ""
            price_cell = str(row_data[11]).strip() if len(row_data) > 11 else ""
            
            if model_cell or 'UZT' in str(row_data) or any('UZT' in str(cell) for cell in row_data):
                print(f"Row {row_idx}: Model='{model_cell}' | Price='{price_cell}' | Full: {row_data}")
                
                # Check if model_cell matches our patterns
                if re.match(r'^[A-Z]{4}(\d+)?$', model_cell):
                    print(f"  -> MATCH: '{model_cell}' matches pattern")
                else:
                    print(f"  -> NO MATCH: '{model_cell}' does not match pattern")

if __name__ == "__main__":
    debug_uzt_extraction()