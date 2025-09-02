#!/usr/bin/env python3
"""
Analyze first 10 pages of Ski-Doo 2026 Product Specification Book
for dual parser pipeline structure analysis
"""
import PyPDF2
import re
from pathlib import Path

def analyze_spec_book_structure():
    """Analyze the first 10 pages of the Ski-Doo 2026 Product Spec Book"""
    
    pdf_path = Path("TEST_DUAL_PARSER_PIPELINE/docs/SKIDOO_2026 PRODUCT SPEC BOOK.pdf")
    
    print("=" * 80)
    print("SKI-DOO 2026 PRODUCT SPECIFICATION BOOK - FIRST 10 PAGES ANALYSIS")
    print("=" * 80)
    print(f"PDF Path: {pdf_path}")
    
    if not pdf_path.exists():
        print(f"ERROR: PDF file not found: {pdf_path}")
        return
    
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            total_pages = len(reader.pages)
            print(f"Total pages in document: {total_pages}")
            print(f"Analyzing first 10 pages...\n")
            
            # Analyze first 10 pages only
            pages_to_analyze = min(10, total_pages)
            
            for page_num in range(pages_to_analyze):
                print(f"\n{'=' * 60}")
                print(f"PAGE {page_num + 1} ANALYSIS")
                print(f"{'=' * 60}")
                
                try:
                    page = reader.pages[page_num]
                    text = page.extract_text()
                    
                    if not text.strip():
                        print("No extractable text found on this page")
                        continue
                    
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    
                    # Basic page structure analysis
                    print(f"Total lines: {len(lines)}")
                    print(f"First 5 lines:")
                    for i, line in enumerate(lines[:5], 1):
                        print(f"  {i}: {line}")
                    
                    if len(lines) > 5:
                        print(f"Last 5 lines:")
                        for i, line in enumerate(lines[-5:], len(lines) - 4):
                            print(f"  {i}: {line}")
                    
                    # Look for model names and patterns
                    print(f"\nMODEL NAME ANALYSIS:")
                    model_patterns = [
                        r'(SUMMIT|Summit)\s*(X|Expert|X\s+Expert)*',
                        r'(MXZ|Mxz)\s*(X-RS|Sport|RE)*',
                        r'(EXPEDITION|Expedition)\s*(SE|Sport)*',
                        r'(RENEGADE|Renegade)\s*(X-RS|Sport|Adrenaline)*',
                        r'(FREERIDE|Freeride)\s*(ST|Sport)*',
                        r'(BACKCOUNTRY|Backcountry)\s*(X-RS|Sport)*',
                        r'(GRAND TOURING|Grand Touring)\s*(SE|Limited)*',
                        r'(SKANDIC|Skandic)\s*(Sport|WT|LE)*',
                        r'(TUNDRA|Tundra)\s*(Sport|LT|LE)*'
                    ]
                    
                    found_models = []
                    for line in lines:
                        for pattern in model_patterns:
                            matches = re.findall(pattern, line, re.IGNORECASE)
                            if matches:
                                for match in matches:
                                    model_name = ' '.join(match).strip()
                                    if model_name and model_name not in found_models:
                                        found_models.append(model_name)
                                        print(f"  Found model: '{model_name}' in line: '{line}'")
                    
                    if not found_models:
                        # Look for any capitalized words that might be models
                        caps_words = re.findall(r'\b[A-Z]{3,}\b', text)
                        if caps_words:
                            print(f"  Capitalized words (potential models): {list(set(caps_words))}")
                    
                    # Look for technical specifications
                    print(f"\nTECHNICAL SPECIFICATIONS:")
                    spec_patterns = {
                        'Engine': [r'(\d{3,4})\s*(R\s*)?E-TEC', r'(\d{3,4})\s*ACE', r'Turbo\s*R?'],
                        'Track': [r'(\d{2,3})\s*in', r'(\d{4})\s*mm', r'x\s*(\d{1,2})"'],
                        'Suspension': [r'SC-5M', r'rMotion', r'tMotion', r'Air Ride'],
                        'Features': [r'Electric Start', r'Manual Start', r'Touchscreen', r'Digital Display']
                    }
                    
                    for spec_type, patterns in spec_patterns.items():
                        found_specs = []
                        for line in lines:
                            for pattern in patterns:
                                matches = re.findall(pattern, line, re.IGNORECASE)
                                if matches:
                                    found_specs.extend(matches)
                        
                        if found_specs:
                            unique_specs = list(set([str(spec) for spec in found_specs if spec]))
                            print(f"  {spec_type}: {unique_specs}")
                    
                    # Look for pricing information
                    print(f"\nPRICING ANALYSIS:")
                    price_patterns = [
                        r'(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)\s*€',
                        r'\$(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)',
                        r'(\d{1,3}(?:[,\s]\d{3})+)',
                        r'MSRP.*?(\d+)',
                        r'Price.*?(\d+)'
                    ]
                    
                    prices_found = []
                    for line in lines:
                        for pattern in price_patterns:
                            matches = re.findall(pattern, line)
                            if matches:
                                for match in matches:
                                    try:
                                        price_str = str(match).replace(',', '').replace(' ', '')
                                        if price_str.isdigit() and int(price_str) > 10000:
                                            prices_found.append((price_str, line))
                                    except:
                                        pass
                    
                    if prices_found:
                        print(f"  Found potential prices:")
                        for price, line in prices_found[:3]:  # Show first 3
                            print(f"    {price} in: '{line[:60]}...'")
                    else:
                        print(f"  No pricing information found")
                    
                    # Look for page structure markers
                    print(f"\nPAGE STRUCTURE MARKERS:")
                    structure_markers = [
                        'Header', 'Footer', 'Page', 'Section', 'Chapter',
                        '2026', 'SKI-DOO', 'SPECIFICATIONS', 'FEATURES'
                    ]
                    
                    found_markers = []
                    for line in lines:
                        for marker in structure_markers:
                            if marker.lower() in line.lower():
                                if line not in found_markers:
                                    found_markers.append(line)
                    
                    if found_markers:
                        print(f"  Structure indicators found:")
                        for marker in found_markers[:5]:  # Show first 5
                            print(f"    '{marker}'")
                    
                    # Look for package information
                    print(f"\nPACKAGE/VARIANT ANALYSIS:")
                    package_keywords = [
                        'Package', 'Expert', 'Spring', 'Option', 'Upgrade',
                        'SE', 'X-RS', 'Sport', 'Limited', 'Adrenaline'
                    ]
                    
                    package_info = []
                    for line in lines:
                        for keyword in package_keywords:
                            if keyword.lower() in line.lower():
                                if line not in package_info:
                                    package_info.append(line)
                    
                    if package_info:
                        print(f"  Package-related content found:")
                        for info in package_info[:3]:  # Show first 3
                            print(f"    '{info}'")
                    else:
                        print(f"  No package information found")
                
                except Exception as e:
                    print(f"Error processing page {page_num + 1}: {e}")
            
            # Summary analysis
            print(f"\n{'=' * 80}")
            print("SUMMARY ANALYSIS FOR DUAL PARSER PIPELINE")
            print(f"{'=' * 80}")
            
            print("Key Findings:")
            print("1. Page Layout Structure: [To be determined from analysis above]")
            print("2. Model Naming Conventions: [Check model patterns found]")
            print("3. Technical Spec Placement: [Review spec locations]")
            print("4. Pricing Information: [Check price analysis results]")
            print("5. Package Variants: [Review package analysis]")
            
            print("\nRecommendations for Parser Development:")
            print("- Focus on consistent text patterns found across pages")
            print("- Implement regex patterns for model identification")
            print("- Structure extraction logic based on recurring elements")
            print("- Consider page-specific vs global parsing strategies")
            
    except Exception as e:
        print(f"ERROR reading PDF: {e}")

if __name__ == "__main__":
    analyze_spec_book_structure()