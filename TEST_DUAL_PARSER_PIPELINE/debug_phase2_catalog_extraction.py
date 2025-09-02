"""
Phase 2 Debug: Transparent Catalog Vehicle Extraction
Shows raw PDF text, extraction logic, and why vehicles show as "Unknown"
"""

import fitz  # PyMuPDF
import re
from pathlib import Path
from modular_parser import CatalogExtractor
from data_models import DualParserConfig

def debug_catalog_extraction(pdf_path: str = None):
    """Debug catalog vehicle extraction with complete transparency"""
    
    print("=== PHASE 2: CATALOG VEHICLE EXTRACTION DEBUG ===\n")
    
    # Find the PDF if not specified
    if pdf_path is None:
        docs_folder = Path("docs")
        pdf_candidates = list(docs_folder.glob("*SKIDOO*2026*PRODUCT*SPEC*.pdf"))
        if not pdf_candidates:
            print("ERROR: No SKI-DOO 2026 Product Spec Book found")
            return
        pdf_path = pdf_candidates[0]
    
    pdf_path = Path(pdf_path)
    print(f"Debugging PDF: {pdf_path}")
    print(f"PDF exists: {pdf_path.exists()}")
    print(f"PDF size: {pdf_path.stat().st_size / 1024 / 1024:.1f}MB")
    
    # Initialize extractor
    config = DualParserConfig()
    extractor = CatalogExtractor(config)
    
    print("\n" + "="*80)
    
    # Open PDF and debug first few pages
    with fitz.open(pdf_path) as pdf:
        total_pages = pdf.page_count
        print(f"\nPDF has {total_pages} pages")
        
        # Debug first 10 pages
        pages_to_debug = min(10, total_pages)
        print(f"Debugging first {pages_to_debug} pages...")
        
        for page_num in range(pages_to_debug):
            page = pdf[page_num]
            text = page.get_text()
            
            print(f"\n{'='*20} PAGE {page_num + 1} {'='*20}")
            
            # Show raw text (first 300 chars)
            print(f"RAW TEXT (first 300 chars):")
            print(f"'{text[:300]}...'")
            
            # Test if this is considered a vehicle page
            is_vehicle = extractor._is_vehicle_page(text)
            print(f"\nIS_VEHICLE_PAGE: {is_vehicle}")
            
            if is_vehicle:
                print(f"\n[VEHICLE PAGE DETECTED - EXTRACTING...]")
                
                # Debug vehicle extraction step by step
                print(f"\n1. MODEL INFO EXTRACTION:")
                name, family = extractor._extract_model_info(text)
                print(f"   Extracted name: '{name}'")
                print(f"   Extracted family: '{family}'")
                
                # Show the logic behind name extraction
                print(f"\n2. NAME EXTRACTION LOGIC DEBUG:")
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                print(f"   Total text lines: {len(lines)}")
                print(f"   First 10 lines for analysis:")
                
                for i, line in enumerate(lines[:10]):
                    line_upper = line.upper()
                    print(f"     Line {i+1}: '{line}' (length: {len(line)})")
                    
                    # Check skip conditions
                    skip_reasons = []
                    if any(skip in line_upper for skip in ['2026', 'VEHICLE SPECIFICATIONS', 'PAGE']):
                        skip_reasons.append("Contains skip keywords")
                    
                    # Check model family detection
                    model_families = ['SUMMIT', 'MXZ', 'RENEGADE', 'EXPEDITION', 'FREERIDE', 'BACKCOUNTRY', 'SKANDIC', 'TUNDRA']
                    detected_families = [family for family in model_families if family in line_upper]
                    
                    if detected_families:
                        print(f"       [+] Model families detected: {detected_families}")
                    if skip_reasons:
                        print(f"       [-] Skipped: {skip_reasons}")
                    
                    if detected_families and not skip_reasons:
                        print(f"       [TARGET] THIS LINE SHOULD BE SELECTED!")
                        break
                
                print(f"\n3. SPECIFICATIONS EXTRACTION:")
                specs = extractor._extract_specifications(text)
                print(f"   Engine: '{specs.engine}'")
                print(f"   Engine family: '{specs.engine_family}'")
                print(f"   Displacement: {specs.displacement_cc}")
                print(f"   Track length (in): {specs.track_length_in}")
                print(f"   Track length (mm): {specs.track_length_mm}")
                print(f"   Display size: '{specs.display_size}'")
                print(f"   Starter system: '{specs.starter_system}'")
                
                # Debug engine extraction
                print(f"\n4. ENGINE EXTRACTION DEBUG:")
                engine_pattern = r'(\d{3,4})\s*([R]?)\s*(E-TEC|ACE)\s*(TURBO\s*R?)?'
                engine_matches = list(re.finditer(engine_pattern, text, re.IGNORECASE))
                print(f"   Engine regex matches found: {len(engine_matches)}")
                for i, match in enumerate(engine_matches[:3]):  # Show first 3
                    print(f"     Match {i+1}: '{match.group()}' at position {match.start()}-{match.end()}")
                    print(f"       Groups: {match.groups()}")
                
                print(f"\n5. MARKETING CONTENT EXTRACTION:")
                marketing = extractor._extract_marketing_content(text)
                print(f"   Tagline: '{marketing.tagline}'")
                print(f"   Key benefits count: {len(marketing.key_benefits)}")
                if marketing.key_benefits:
                    print(f"   First 3 benefits:")
                    for i, benefit in enumerate(marketing.key_benefits[:3], 1):
                        print(f"     {i}. '{benefit[:50]}...'")
                
                print(f"\n6. COLOR EXTRACTION:")
                colors = extractor._extract_colors(text)
                print(f"   Colors found: {len(colors)}")
                for color in colors:
                    print(f"     - {color.name} (spring only: {color.spring_only})")
                
                print(f"\n7. SPRING OPTIONS EXTRACTION:")
                spring_options = extractor._extract_spring_options(text)
                print(f"   Spring options found: {len(spring_options)}")
                for option in spring_options:
                    print(f"     - '{option.description}' (color: {option.color_name}, engine: {option.engine_restriction})")
                
            else:
                print(f"\n[-] NOT A VEHICLE PAGE")
                
                # Explain why it's not a vehicle page
                print(f"\n   WHY NOT A VEHICLE PAGE:")
                
                # Check model family presence
                model_families = ['SUMMIT', 'MXZ', 'RENEGADE', 'EXPEDITION', 'FREERIDE', 'BACKCOUNTRY', 'SKANDIC', 'TUNDRA']
                has_model = any(model in text.upper() for model in model_families)
                print(f"     Has model family: {has_model}")
                if has_model:
                    found_models = [m for m in model_families if m in text.upper()]
                    print(f"     Found model families: {found_models}")
                
                # Check technical specs presence
                spec_keywords = ['ENGINE', 'TRACK', 'SUSPENSION', 'E-TEC', 'ACE', 'ROTAX']
                has_specs = any(keyword in text.upper() for keyword in spec_keywords)
                print(f"     Has technical specs: {has_specs}")
                if has_specs:
                    found_specs = [s for s in spec_keywords if s in text.upper()]
                    print(f"     Found spec keywords: {found_specs}")
                
                # Check avoid keywords
                avoid_keywords = ['TABLE OF CONTENTS', 'SPECIFICATIONS OVERVIEW', '2026 PRODUCT SPEC BOOK']
                is_intro = any(keyword in text.upper() for keyword in avoid_keywords)
                print(f"     Is intro/cover page: {is_intro}")
                if is_intro:
                    found_avoid = [a for a in avoid_keywords if a in text.upper()]
                    print(f"     Found avoid keywords: {found_avoid}")
                
                # Final decision logic
                should_be_vehicle = has_model and has_specs and not is_intro
                print(f"     Should be vehicle page: {should_be_vehicle}")
                
            print(f"\n" + "="*60)
        
        print(f"\n=== PHASE 2 COMPLETE: Catalog extraction debug finished ===")
        
def test_vehicle_name_extraction():
    """Test vehicle name extraction with sample text"""
    
    print(f"\n=== VEHICLE NAME EXTRACTION TEST ===")
    
    # Sample texts that should extract vehicle names
    test_texts = [
        "SUMMIT X WITH EXPERT PACKAGE\nThe ultimate precise and predictable deep-snow sled",
        "SUMMIT X\nThe lightest and nimble of its family",
        "SUMMIT ADRENALINE\nAn excellent deep-snow machine for any rider",
        "MXZ X-RS WITH COMPETITION PACKAGE\nBuilt for the rider who demands performance",
        "EXPEDITION XTREME\nLong-distance comfort meets capability",
    ]
    
    config = DualParserConfig()
    extractor = CatalogExtractor(config)
    
    for i, text in enumerate(test_texts, 1):
        print(f"\nTest {i}: '{text[:50]}...'")
        name, family = extractor._extract_model_info(text)
        print(f"  Result - Name: '{name}', Family: '{family}'")

if __name__ == "__main__":
    debug_catalog_extraction()
    test_vehicle_name_extraction()