"""
Debug PDF Text Extraction
Look at the raw text from SKI-DOO 2026 to see the actual format
"""

import fitz
from pathlib import Path

def debug_skidoo_2026_text():
    """Debug the actual text content of SKI-DOO 2026 PDF"""
    
    pdf_path = Path("docs/SKI-DOO_2026-PRICE_LIST.pdf")
    
    if not pdf_path.exists():
        print("SKI-DOO_2026-PRICE_LIST.pdf not found!")
        return
    
    print("=== RAW TEXT DEBUG: SKI-DOO 2026 ===\n")
    
    with fitz.open(pdf_path) as pdf:
        print(f"PDF has {pdf.page_count} pages\n")
        
        for page_num in range(pdf.page_count):
            page = pdf[page_num]
            text = page.get_text()
            
            print(f"PAGE {page_num + 1}:")
            print("=" * 50)
            
            lines = text.split('\n')
            
            # Show first 50 lines of each page
            for i, line in enumerate(lines[:50], 1):
                if line.strip():  # Only show non-empty lines
                    print(f"{i:3d}: {repr(line)}")
            
            print(f"\n... (showing first 50 lines of {len(lines)} total lines)")
            print()
            
            # Look specifically for lines that might contain TJTH or model codes
            tjth_lines = []
            model_code_lines = []
            
            for i, line in enumerate(lines):
                if 'TJTH' in line or 'TSTH' in line:
                    tjth_lines.append((i+1, line))
                elif line.strip() and any(line.startswith(code) for code in ['TWTB', 'TXTC', 'BPTB', 'UCTA', 'MZTD']):
                    model_code_lines.append((i+1, line))
            
            if tjth_lines:
                print("TJTH/TSTH LINES FOUND:")
                for line_num, line in tjth_lines:
                    print(f"  Line {line_num}: {repr(line)}")
                print()
            
            if model_code_lines:
                print("SAMPLE MODEL CODE LINES:")
                for line_num, line in model_code_lines[:5]:
                    print(f"  Line {line_num}: {repr(line)}")
                print()
            
            # Look for price patterns
            price_lines = []
            for i, line in enumerate(lines):
                if '€' in line and any(char.isdigit() for char in line):
                    price_lines.append((i+1, line))
                    if len(price_lines) >= 10:  # Get first 10 price lines
                        break
            
            if price_lines:
                print("PRICE LINES FOUND:")
                for line_num, line in price_lines[:5]:
                    print(f"  Line {line_num}: {repr(line)}")
                print()
            
            print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    debug_skidoo_2026_text()