"""
Phase 2 Debug: Simple Analysis Without Unicode Issues
Shows what's wrong with vehicle name extraction
"""

import fitz
from pathlib import Path
from modular_parser import CatalogExtractor
from data_models import DualParserConfig

def simple_debug():
    print("=== PHASE 2 DEBUG: VEHICLE NAME EXTRACTION ISSUE ===\n")
    
    # Find PDF
    docs_folder = Path("docs")
    pdf_path = list(docs_folder.glob("*SKIDOO*2026*PRODUCT*SPEC*.pdf"))[0]
    
    # Initialize extractor
    config = DualParserConfig()
    extractor = CatalogExtractor(config)
    
    with fitz.open(pdf_path) as pdf:
        # Check first vehicle page (page 8 based on table of contents)
        page8 = pdf[7]  # 0-indexed
        text = page8.get_text()
        
        print("PAGE 8 ANALYSIS:")
        print("Raw text first 500 chars:")
        # Clean text for safe printing
        safe_text = ''.join(c if ord(c) < 128 else '?' for c in text[:500])
        print(repr(safe_text))
        
        print("\nFirst 20 lines:")
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        for i, line in enumerate(lines[:20], 1):
            safe_line = ''.join(c if ord(c) < 128 else '?' for c in line)
            print(f"  {i:2d}: '{safe_line}'")
        
        print("\nVehicle name extraction test:")
        name, family = extractor._extract_model_info(text)
        print(f"  Result: name='{name}', family='{family}'")
        
        print("\nModel family detection in each line:")
        model_families = ['SUMMIT', 'MXZ', 'RENEGADE', 'EXPEDITION', 'FREERIDE', 'BACKCOUNTRY', 'SKANDIC', 'TUNDRA']
        
        for i, line in enumerate(lines[:15], 1):
            line_upper = line.upper()
            detected = [f for f in model_families if f in line_upper]
            skip = any(skip in line_upper for skip in ['2026', 'VEHICLE SPECIFICATIONS', 'PAGE'])
            
            if detected and not skip:
                safe_line = ''.join(c if ord(c) < 128 else '?' for c in line)
                print(f"  Line {i} SHOULD BE SELECTED: '{safe_line}' -> {detected}")

if __name__ == "__main__":
    simple_debug()