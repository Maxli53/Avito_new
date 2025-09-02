"""
Proper Price List Extractor - Complete Structured Lines
Extracts complete structured price entries like:
TJTH Summit X with Expert Pkg 850 E-TEC Turbo R 165in 4200mm 3.0in 76mm Powdermax X-light SHOT 10.25 in. Color Touchscreen Display 165 inch Track, Terra Green Color Terra Green 27 270,00 €
"""

import fitz  # PyMuPDF
import sqlite3
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid

class ProperPriceExtractor:
    """Extract complete structured price lines from Finnish price list PDFs"""
    
    def __init__(self, db_path: str = "snowmobile_reconciliation.db", docs_folder: str = "docs"):
        self.db_path = db_path
        self.docs_folder = Path(docs_folder)
        
        # Field mappings by brand/year - start with SKI-DOO 2026
        self.field_mappings = {
            "SKI-DOO_2026": [
                "Tuotenro",      # Product number/Model code
                "Malli",         # Model  
                "Paketti",       # Package
                "Moottori",      # Engine
                "Telamatto",     # Track
                "Käynnistin",    # Starter
                "Mittaristo",    # Gauge
                "Kevätoptiot",   # Spring options
                "Väri",          # Color
                "Suositushinta"  # Recommended price, incl. VAT
            ]
        }
    
    def analyze_all_pdfs(self):
        """Analyze all price list PDFs to understand their structures"""
        print("=== PRICE LIST PDF STRUCTURE ANALYSIS ===\n")
        
        price_pdfs = [
            {"file": "LYNX_2024-PRICE_LIST.pdf", "brand": "LYNX", "year": 2024},
            {"file": "LYNX_2025-PRICE_LIST.pdf", "brand": "LYNX", "year": 2025},
            {"file": "LYNX_2026-PRICE_LIST.pdf", "brand": "LYNX", "year": 2026},
            {"file": "SKI-DOO_2024-PRICE_LIST.pdf", "brand": "SKI-DOO", "year": 2024},
            {"file": "SKI-DOO_2025-PRICE_LIST.pdf", "brand": "SKI-DOO", "year": 2025},
            {"file": "SKI-DOO_2026-PRICE_LIST.pdf", "brand": "SKI-DOO", "year": 2026}
        ]
        
        for pdf_info in price_pdfs:
            pdf_path = self.docs_folder / pdf_info["file"]
            
            if not pdf_path.exists():
                print(f"[WARNING] {pdf_info['file']} not found, skipping...")
                continue
            
            print(f"Analyzing {pdf_info['brand']} {pdf_info['year']}...")
            print(f"  File: {pdf_info['file']} ({pdf_path.stat().st_size / 1024:.1f} KB)")
            
            try:
                self.analyze_pdf_structure(pdf_path, pdf_info['brand'], pdf_info['year'])
            except Exception as e:
                print(f"  [ERROR] Analysis failed: {e}")
            
            print()
    
    def analyze_pdf_structure(self, pdf_path: Path, brand: str, year: int):
        """Analyze the structure of a specific PDF"""
        
        with fitz.open(pdf_path) as pdf:
            print(f"    PDF has {pdf.page_count} pages")
            
            # Look for header lines and data patterns
            headers_found = []
            sample_data_lines = []
            
            for page_num in range(min(3, pdf.page_count)):  # Check first 3 pages
                page = pdf[page_num]
                text = page.get_text()
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                
                for line_num, line in enumerate(lines):
                    # Look for potential header lines (contain field names)
                    if any(field in line for field in [
                        'Tuotenro', 'Malli', 'Paketti', 'Moottori', 'Väri', 'Hinta', 'Price',
                        'MALLIKOODI', 'MODEL CODE', 'Suositushinta'
                    ]):
                        headers_found.append({
                            'page': page_num + 1,
                            'line_num': line_num,
                            'content': line
                        })
                    
                    # Look for data lines (start with model code pattern)
                    if re.match(r'^[A-Z]{4}\s', line) and '€' in line:
                        sample_data_lines.append({
                            'page': page_num + 1,
                            'line_num': line_num,
                            'content': line
                        })
                        
                        if len(sample_data_lines) >= 5:  # Get enough samples
                            break
                
                if len(sample_data_lines) >= 5:
                    break
            
            # Report findings
            print(f"    Found {len(headers_found)} potential header lines:")
            for header in headers_found:
                print(f"      Page {header['page']}: {header['content'][:100]}...")
            
            print(f"    Found {len(sample_data_lines)} sample data lines:")
            for i, sample in enumerate(sample_data_lines[:3], 1):  # Show first 3
                print(f"      Sample {i}: {sample['content'][:120]}...")
            
            # Try to detect field structure
            if sample_data_lines:
                self.detect_field_structure(sample_data_lines, brand, year)
    
    def detect_field_structure(self, data_lines: List[Dict], brand: str, year: int):
        """Try to detect the field structure from sample data lines"""
        
        print(f"    Attempting to detect field structure...")
        
        # Analyze first data line in detail
        if data_lines:
            sample_line = data_lines[0]['content']
            print(f"    Analyzing: {sample_line}")
            
            # Split by common separators and analyze parts
            parts = self.smart_split_line(sample_line)
            print(f"    Detected {len(parts)} parts:")
            
            for i, part in enumerate(parts, 1):
                print(f"      {i}: '{part}'")
            
            # Try to identify what each part represents
            field_guesses = self.guess_field_types(parts)
            print(f"    Field type guesses:")
            for i, (part, guess) in enumerate(zip(parts, field_guesses), 1):
                print(f"      {i}: '{part[:30]}...' -> {guess}")
    
    def smart_split_line(self, line: str) -> List[str]:
        """Intelligently split a data line into meaningful parts"""
        
        # First, extract and separate the price (always at the end)
        price_match = re.search(r'(\d{1,3}(?:\s?\d{3})*[.,]\d{2}\s*€)$', line)
        if price_match:
            price_part = price_match.group(1)
            line_without_price = line[:price_match.start()].strip()
        else:
            price_part = None
            line_without_price = line
        
        # Extract model code (always at the beginning)
        model_code_match = re.match(r'^([A-Z]{4})\s+', line_without_price)
        if model_code_match:
            model_code = model_code_match.group(1)
            line_after_code = line_without_price[model_code_match.end():].strip()
        else:
            model_code = None
            line_after_code = line_without_price
        
        # Now split the middle part intelligently
        # Look for common patterns: dimensions, technical specs, color names
        middle_parts = []
        
        # Split by common technical spec patterns
        remaining = line_after_code
        
        # Extract dimensions like "165in 4200mm 3.0in 76mm"
        dimension_pattern = r'(\d+(?:\.\d+)?(?:in|mm|cm)\s*(?:\d+(?:\.\d+)?(?:in|mm|cm)\s*)*)'
        dimension_matches = list(re.finditer(dimension_pattern, remaining))
        
        # Split around these technical specifications
        last_end = 0
        for match in dimension_matches:
            if match.start() > last_end:
                text_before = remaining[last_end:match.start()].strip()
                if text_before:
                    # Further split text parts by multiple spaces
                    text_parts = [p.strip() for p in re.split(r'\s{2,}', text_before) if p.strip()]
                    middle_parts.extend(text_parts)
            
            middle_parts.append(match.group(1).strip())
            last_end = match.end()
        
        # Add remaining text after last dimension
        if last_end < len(remaining):
            remaining_text = remaining[last_end:].strip()
            if remaining_text:
                # Split remaining text by multiple spaces
                text_parts = [p.strip() for p in re.split(r'\s{2,}', remaining_text) if p.strip()]
                middle_parts.extend(text_parts)
        
        # Combine all parts
        all_parts = []
        if model_code:
            all_parts.append(model_code)
        all_parts.extend(middle_parts)
        if price_part:
            all_parts.append(price_part)
        
        return all_parts
    
    def guess_field_types(self, parts: List[str]) -> List[str]:
        """Guess what type of field each part represents"""
        
        guesses = []
        
        for i, part in enumerate(parts):
            if i == 0 and re.match(r'^[A-Z]{4}$', part):
                guesses.append("Model Code (Tuotenro)")
            elif '€' in part:
                guesses.append("Price (Suositushinta)")
            elif any(model in part.upper() for model in [
                'SUMMIT', 'MXZ', 'RENEGADE', 'EXPEDITION', 'BACKCOUNTRY', 'FREERIDE',
                'GRAND TOURING', 'SKANDIC', 'TUNDRA', 'RAVE', 'ADVENTURE', 'RANGER'
            ]):
                guesses.append("Model Name (Malli)")
            elif any(pkg in part.upper() for pkg in [
                'EXPERT', 'COMPETITION', 'SPORT', 'ADRENALINE', 'NEO', 'XTREME', 'PKG', 'PACKAGE'
            ]):
                guesses.append("Package (Paketti)")
            elif any(engine in part.upper() for engine in [
                'E-TEC', 'ACE', 'TURBO', '600', '850', '900', 'EFI', 'HP'
            ]):
                guesses.append("Engine (Moottori)")
            elif re.search(r'\d+(?:\.\d+)?(?:in|mm|cm)', part):
                guesses.append("Technical Spec (Telamatto/etc)")
            elif any(color in part.upper() for color in [
                'BLACK', 'WHITE', 'RED', 'BLUE', 'GREEN', 'YELLOW', 'ORANGE', 'GRAY', 'SILVER',
                'TERRA', 'MUSTA', 'VALKOINEN', 'PUNAINEN', 'SININEN', 'VIHREÄ'
            ]):
                guesses.append("Color (Väri)")
            elif 'SHOT' in part.upper():
                guesses.append("Starter (Käynnistin)")
            elif any(gauge in part.upper() for gauge in [
                'DISPLAY', 'GAUGE', 'SCREEN', 'DIGITAL', 'ANALOG'
            ]):
                guesses.append("Gauge (Mittaristo)")
            else:
                guesses.append("Unknown")
        
        return guesses
    
    def extract_skidoo_2026(self):
        """Extract SKI-DOO 2026 data with known field structure"""
        print("=== EXTRACTING SKI-DOO 2026 WITH PROPER STRUCTURE ===\n")
        
        pdf_path = self.docs_folder / "SKI-DOO_2026-PRICE_LIST.pdf"
        
        if not pdf_path.exists():
            print("SKI-DOO_2026-PRICE_LIST.pdf not found!")
            return
        
        print(f"Processing: {pdf_path.name}")
        
        entries = []
        
        with fitz.open(pdf_path) as pdf:
            print(f"PDF has {pdf.page_count} pages")
            
            for page_num in range(pdf.page_count):
                page = pdf[page_num]
                text = page.get_text()
                
                # Find complete structured data lines
                lines = text.split('\n')
                
                for line in lines:
                    line = line.strip()
                    
                    # Look for lines that start with model code and contain price
                    if re.match(r'^[A-Z]{4}\s', line) and '€' in line:
                        entry = self.parse_skidoo_2026_line(line, page_num + 1)
                        if entry:
                            entries.append(entry)
        
        print(f"Found {len(entries)} complete entries")
        
        # Show samples
        print("\nSample entries:")
        for i, entry in enumerate(entries[:5], 1):
            print(f"  {i}. {entry['tuotenro']}: {entry.get('malli', 'N/A')} {entry.get('paketti', 'N/A')} - {entry['price']}€")
        
        # Save to database
        if entries:
            saved = self.save_proper_entries(entries, "SKI-DOO", 2026)
            print(f"\nSaved {saved} entries to database")
        
        return entries
    
    def parse_skidoo_2026_line(self, line: str, page_num: int) -> Optional[Dict[str, Any]]:
        """Parse a complete SKI-DOO 2026 structured line"""
        
        try:
            # Extract price first (always at the end)
            price_match = re.search(r'(\d{1,3}(?:\s\d{3})*)[.,](\d{2})\s*€$', line)
            if not price_match:
                return None
            
            # Convert Finnish price format to float
            price_int = price_match.group(1).replace(' ', '')
            price_dec = price_match.group(2)
            price_value = float(f"{price_int}.{price_dec}")
            
            # Remove price from line
            line_without_price = line[:price_match.start()].strip()
            
            # Extract model code (first 4 letters)
            model_code_match = re.match(r'^([A-Z]{4})\s+', line_without_price)
            if not model_code_match:
                return None
            
            model_code = model_code_match.group(1)
            remaining_line = line_without_price[model_code_match.end():].strip()
            
            # Parse the remaining fields intelligently
            entry = {
                'tuotenro': model_code,
                'price': price_value,
                'page_number': page_num,
                'raw_line': line
            }
            
            # Split remaining line and try to identify fields
            parts = self.smart_split_line(remaining_line + f" {price_match.group(0)}")
            field_types = self.guess_field_types(parts)
            
            # Map identified parts to proper fields
            for part, field_type in zip(parts, field_types):
                if "Model Name" in field_type:
                    entry['malli'] = part
                elif "Package" in field_type:
                    entry['paketti'] = part
                elif "Engine" in field_type:
                    entry['moottori'] = part
                elif "Color" in field_type:
                    entry['vari'] = part
                elif "Technical Spec" in field_type:
                    # Could be track, starter, gauge, etc.
                    if 'telamatto' not in entry:
                        entry['telamatto'] = part
                    elif 'kaynnistin' not in entry and 'SHOT' in part.upper():
                        entry['kaynnistin'] = part
                    elif 'mittaristo' not in entry and any(g in part.upper() for g in ['DISPLAY', 'SCREEN', 'GAUGE']):
                        entry['mittaristo'] = part
            
            return entry
            
        except Exception as e:
            print(f"    [WARNING] Failed to parse line: {line[:50]}... - {e}")
            return None
    
    def save_proper_entries(self, entries: List[Dict[str, Any]], brand: str, year: int) -> int:
        """Save properly extracted entries to database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing data for this brand/year
        cursor.execute("DELETE FROM price_entries WHERE brand = ? AND model_year = ?", (brand, year))
        print(f"Cleared existing {brand} {year} entries")
        
        saved_count = 0
        
        for entry in entries:
            try:
                cursor.execute("""
                    INSERT INTO price_entries (
                        id, price_list_id, model_code, malli, paketti, moottori, 
                        telamatto, kaynnistin, mittaristo, vari, price,
                        currency, market, brand, model_year, catalog_lookup_key,
                        extraction_timestamp, extraction_method, parser_version,
                        source_catalog_page, price_list_source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),  # id
                    f"{brand}_{year}_PROPER",  # price_list_id
                    entry['tuotenro'],  # model_code
                    entry.get('malli'),  # malli
                    entry.get('paketti'),  # paketti
                    entry.get('moottori'),  # moottori
                    entry.get('telamatto'),  # telamatto
                    entry.get('kaynnistin'),  # kaynnistin
                    entry.get('mittaristo'),  # mittaristo
                    entry.get('vari'),  # vari
                    entry['price'],  # price
                    'EUR',  # currency
                    'FINLAND',  # market
                    brand,  # brand
                    year,  # model_year
                    f"{brand}_{year}_{entry['tuotenro']}",  # catalog_lookup_key
                    datetime.now().isoformat(),  # extraction_timestamp
                    'proper_structured_extractor',  # extraction_method
                    '2.0',  # parser_version
                    entry.get('page_number'),  # source_catalog_page
                    entry.get('raw_line')[:255] if entry.get('raw_line') else None  # price_list_source (truncated)
                ))
                saved_count += 1
                
            except Exception as e:
                print(f"Failed to save entry {entry.get('tuotenro', 'UNKNOWN')}: {e}")
        
        conn.commit()
        conn.close()
        
        return saved_count

if __name__ == "__main__":
    extractor = ProperPriceExtractor()
    
    # First analyze all PDFs to understand structures
    extractor.analyze_all_pdfs()
    
    print("\n" + "="*80)
    
    # Then extract SKI-DOO 2026 with proper structure
    extractor.extract_skidoo_2026()