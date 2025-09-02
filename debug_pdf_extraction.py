#!/usr/bin/env python3
"""
Debug PDF Extraction - Investigate price and data issues
"""
import PyPDF2
import re
from pathlib import Path

def debug_pdf_content():
    """Debug what's actually in the PDF for both models"""
    
    pdf_path = Path("TEST_DUAL_PARSER_PIPELINE/docs/SKI-DOO_2026-PRICE_LIST.pdf")
    target_models = ["ADTD", "ADTC"]
    
    print("=" * 80)
    print("DEBUG PDF EXTRACTION")
    print("=" * 80)
    print(f"PDF Path: {pdf_path}")
    print(f"Target Models: {target_models}")
    
    if not pdf_path.exists():
        print(f"ERROR: PDF file not found: {pdf_path}")
        return
    
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            total_pages = len(reader.pages)
            print(f"Total pages: {total_pages}")
            
            for model_code in target_models:
                print(f"\n" + "-" * 50)
                print(f"SEARCHING FOR MODEL: {model_code}")
                print("-" * 50)
                
                found_pages = []
                
                # Search through all pages
                for page_num, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text()
                        
                        if model_code in text:
                            found_pages.append(page_num + 1)
                            print(f"\nFOUND {model_code} on page {page_num + 1}")
                            
                            # Extract the relevant section
                            lines = text.split('\n')
                            relevant_lines = []
                            
                            for i, line in enumerate(lines):
                                if model_code in line:
                                    # Get context lines around the model code
                                    start_line = max(0, i - 5)
                                    end_line = min(len(lines), i + 10)
                                    relevant_lines = lines[start_line:end_line]
                                    
                                    print(f"Context around {model_code} (lines {start_line}-{end_line}):")
                                    for j, context_line in enumerate(relevant_lines, start_line):
                                        marker = ">>> " if model_code in context_line else "    "
                                        print(f"{marker}{j:3d}: {context_line}")
                                    
                                    # Look for prices in context
                                    print(f"\nPrice analysis for {model_code}:")
                                    prices_found = []
                                    
                                    for j, check_line in enumerate(relevant_lines):
                                        price_matches = re.findall(r'(\d{1,3}(?:[\xa0.,\s]\d{3})*(?:[.,]\d{2})?)\s*€', check_line)
                                        if price_matches:
                                            for price_match in price_matches:
                                                price_str = price_match.replace('\xa0', '').replace(',', '.')
                                                # Ensure decimal format
                                                if '.' not in price_str[-3:] and len(price_str) > 3:
                                                    price_str = price_str[:-2] + '.' + price_str[-2:]
                                                try:
                                                    price = float(price_str)
                                                    prices_found.append((price, check_line.strip()))
                                                    print(f"    Found price: {price} EUR in line: '{check_line.strip()}'")
                                                except ValueError:
                                                    pass
                                    
                                    if prices_found:
                                        valid_prices = [p for p, _ in prices_found if p > 20000]
                                        if valid_prices:
                                            print(f"    Valid prices (>20000): {valid_prices}")
                                        else:
                                            print(f"    No valid prices found (all < 20000)")
                                    else:
                                        print(f"    No prices found in context")
                                    
                                    # Look for Finnish data fields
                                    print(f"\nFinnish field analysis for {model_code}:")
                                    finnish_fields = {
                                        'malli': ['Rave', 'MXZ', 'Summit', 'Expedition', 'Renegade'],
                                        'paketti': ['RE', 'X-RS', 'X', 'SE', 'Sport'],
                                        'moottori': ['600R E-TEC', '850 E-TEC', '900 ACE', 'Turbo R'],
                                        'telamatto': ['129in', '137in', '146in', '154in', '3300mm', '3500mm'],
                                        'kaynnistin': ['Manual', 'Electric', 'E-Start'],
                                        'mittaristo': ['Digital Display', 'Touchscreen', '7.2 in', '10.25 in'],
                                        'kevätoptiot': ['Spring', 'Option', 'Upgrade'],
                                        'vari': ['Black', 'White', 'Red', 'Blue', 'Green', 'Yellow']
                                    }
                                    
                                    for field_name, keywords in finnish_fields.items():
                                        found_keywords = []
                                        for keyword in keywords:
                                            for context_line in relevant_lines:
                                                if keyword.lower() in context_line.lower():
                                                    found_keywords.append(keyword)
                                                    break
                                        
                                        if found_keywords:
                                            print(f"    {field_name}: {found_keywords}")
                                        else:
                                            print(f"    {field_name}: No data found")
                                    
                                    break  # Found the model, don't search more in this page
                    
                    except Exception as e:
                        print(f"Error processing page {page_num + 1}: {e}")
                
                if not found_pages:
                    print(f"Model {model_code} NOT FOUND in any page")
                else:
                    print(f"Model {model_code} found on pages: {found_pages}")
            
    except Exception as e:
        print(f"ERROR reading PDF: {e}")

if __name__ == "__main__":
    debug_pdf_content()