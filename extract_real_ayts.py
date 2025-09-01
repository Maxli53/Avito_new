#!/usr/bin/env python3
"""
Extract real AYTS data from actual Ski-Doo PDF to build expected results database.
This will find the correct specifications that the pipeline should match.
"""
import PyPDF2
import re
from pathlib import Path

def extract_ayts_from_pdf():
    """Extract AYTS entry from actual Ski-Doo PDF"""
    
    pdf_path = Path("data/SKI-DOO_2025-PRICE_LIST.pdf")
    
    print("Extracting AYTS from real Ski-Doo PDF...")
    print(f"File: {pdf_path}")
    
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            print(f"Total pages: {len(pdf_reader.pages)}")
            
            ayts_found = False
            ayts_data = {}
            
            # Search through all pages for AYTS
            for page_num, page in enumerate(pdf_reader.pages, 1):
                text = page.extract_text()
                
                # Look for AYTS model code
                if "AYTS" in text:
                    print(f"\nAYTS found on page {page_num}!")
                    ayts_found = True
                    
                    # Extract the line containing AYTS
                    lines = text.split('\n')
                    for i, line in enumerate(lines):
                        if "AYTS" in line:
                            print(f"AYTS line: {line.strip()}")
                            
                            # Try to extract price from the line or surrounding lines
                            price_match = re.search(r'[\d,]+\.00', line)
                            if price_match:
                                ayts_data['price'] = price_match.group()
                                print(f"Price found: {ayts_data['price']} EUR")
                            
                            # Look in surrounding lines for more details
                            context_lines = lines[max(0, i-3):i+4]
                            context_text = ' '.join(context_lines)
                            print(f"Context: {context_text[:200]}...")
                            
                            # Look for model details
                            if "Expedition" in context_text:
                                ayts_data['model'] = "Expedition SE"
                                print(f"Model: {ayts_data['model']}")
                            
                            if "900 ACE" in context_text:
                                ayts_data['engine'] = "900 ACE Turbo R"
                                print(f"Engine: {ayts_data['engine']}")
                            
                            if "Terra Green" in context_text:
                                ayts_data['color'] = "Terra Green"
                                print(f"Color: {ayts_data['color']}")
                            
                            break
                
                # Also search for "25110" or "25,110" which is the known price
                elif "25110" in text or "25,110" in text:
                    print(f"\nPrice 25,110 found on page {page_num}")
                    lines = text.split('\n')
                    for line in lines:
                        if "25110" in line or "25,110" in line:
                            print(f"Price line: {line.strip()}")
                            if "AYTS" in line:
                                print("AYTS and price on same line!")
                                ayts_data['confirmed_price'] = "25,110.00"
            
            if ayts_found:
                print(f"\nAYTS data extracted successfully!")
                print("=" * 50)
                return ayts_data
            else:
                print(f"\nAYTS not found in PDF")
                return None
                
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None

def build_expected_results_database(ayts_data):
    """Build the expected results database with real AYTS data"""
    
    expected_results = {
        "AYTS": {
            # Based on user's correction and extracted data
            "brand": "Ski-Doo",
            "model_family": "Expedition SE", 
            "engine": "900 ACE Turbo R",
            "price_eur": 25110.00,
            "color": "Terra Green",
            "track": "154in 3900mm 1.5in 38mm Ice Crosscut",
            "display": "10.25 in. Color Touchscreen Display",
            "min_confidence": 0.95,
            "source_pdf": "SKI-DOO_2025-PRICE_LIST.pdf",
            "extraction_notes": "Corrected from previous pipeline failure"
        }
    }
    
    # Add any data we extracted from PDF
    if ayts_data:
        for key, value in ayts_data.items():
            if key == 'price' and value:
                expected_results["AYTS"]["extracted_price"] = value
            elif key == 'confirmed_price':
                expected_results["AYTS"]["pdf_confirmed_price"] = value
    
    return expected_results

if __name__ == "__main__":
    # Extract real AYTS data
    ayts_data = extract_ayts_from_pdf()
    
    # Build expected results database
    expected_results = build_expected_results_database(ayts_data)
    
    print(f"\nExpected Results Database:")
    print("=" * 50)
    for model_code, specs in expected_results.items():
        print(f"\n{model_code}:")
        for key, value in specs.items():
            print(f"  {key}: {value}")
    
    # Save to file for testing
    import json
    with open("expected_results_real.json", "w", encoding="utf-8") as f:
        json.dump(expected_results, f, indent=2, ensure_ascii=False)
    
    print(f"\nExpected results saved to: expected_results_real.json")
    print(f"Ready for real data testing framework!")