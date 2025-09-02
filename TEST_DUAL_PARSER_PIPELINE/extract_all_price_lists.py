"""
Comprehensive Price List Extractor for All Brand/Year Combinations
Extracts Finnish price data from all 6 price list PDFs in docs/
"""

import fitz  # PyMuPDF
import sqlite3
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from matching_engine import TextNormalizer

class ComprehensivePriceExtractor:
    """Extract price data from all Finnish price list PDFs"""
    
    def __init__(self, db_path: str = "snowmobile_reconciliation.db", docs_folder: str = "docs"):
        self.db_path = db_path
        self.docs_folder = Path(docs_folder)
        self.normalizer = TextNormalizer()
        
        # Price list PDFs to process
        self.price_pdfs = [
            {"file": "LYNX_2024-PRICE_LIST.pdf", "brand": "LYNX", "year": 2024},
            {"file": "LYNX_2025-PRICE_LIST.pdf", "brand": "LYNX", "year": 2025},
            {"file": "LYNX_2026-PRICE_LIST.pdf", "brand": "LYNX", "year": 2026},
            {"file": "SKI-DOO_2024-PRICE_LIST.pdf", "brand": "SKI-DOO", "year": 2024},
            {"file": "SKI-DOO_2025-PRICE_LIST.pdf", "brand": "SKI-DOO", "year": 2025},
            {"file": "SKI-DOO_2026-PRICE_LIST.pdf", "brand": "SKI-DOO", "year": 2026}
        ]
    
    def extract_all_price_lists(self):
        """Extract data from all price list PDFs"""
        print("=== COMPREHENSIVE PRICE LIST EXTRACTION ===\n")
        
        total_extracted = 0
        extraction_results = {}
        
        for pdf_info in self.price_pdfs:
            pdf_path = self.docs_folder / pdf_info["file"]
            
            if not pdf_path.exists():
                print(f"[WARNING] {pdf_info['file']} not found, skipping...")
                continue
            
            print(f"Processing {pdf_info['brand']} {pdf_info['year']}...")
            print(f"  File: {pdf_info['file']} ({pdf_path.stat().st_size / 1024:.1f} KB)")
            
            try:
                entries = self.extract_price_pdf(pdf_path, pdf_info['brand'], pdf_info['year'])
                saved_count = self.save_to_database(entries, pdf_info['brand'], pdf_info['year'])
                
                extraction_results[f"{pdf_info['brand']}_{pdf_info['year']}"] = {
                    "extracted": len(entries),
                    "saved": saved_count,
                    "success": saved_count > 0
                }
                
                total_extracted += saved_count
                print(f"  [SUCCESS] Extracted {len(entries)} entries, saved {saved_count} to database\n")
                
            except Exception as e:
                print(f"  [ERROR] Failed to process {pdf_info['file']}: {e}\n")
                extraction_results[f"{pdf_info['brand']}_{pdf_info['year']}"] = {
                    "extracted": 0,
                    "saved": 0,
                    "success": False,
                    "error": str(e)
                }
        
        # Final summary
        print("=== EXTRACTION SUMMARY ===")
        print(f"Total entries extracted: {total_extracted}")
        
        for key, result in extraction_results.items():
            status = "[SUCCESS]" if result["success"] else "[FAILED]"
            print(f"  {key}: {status} {result['saved']} entries")
        
        # Database verification
        self.verify_database_contents()
        
        return extraction_results
    
    def extract_price_pdf(self, pdf_path: Path, brand: str, year: int) -> List[Dict[str, Any]]:
        """Extract price data from a single PDF"""
        
        entries = []
        
        with fitz.open(pdf_path) as pdf:
            print(f"    PDF has {pdf.page_count} pages")
            
            # Process all pages
            for page_num in range(pdf.page_count):
                page = pdf[page_num]
                text = page.get_text()
                
                # Extract price entries from this page
                page_entries = self.parse_price_page(text, page_num + 1)
                entries.extend(page_entries)
        
        print(f"    Found {len(entries)} price entries")
        return entries
    
    def parse_price_page(self, page_text: str, page_num: int) -> List[Dict[str, Any]]:
        """Parse price entries from a single page of text"""
        
        entries = []
        lines = [line.strip() for line in page_text.split('\n') if line.strip()]
        
        # Look for price table patterns
        # Finnish price lists typically have: Model Code | Malli | Paketti | Moottori | Väri | Hinta
        
        current_entry = {}
        collecting_entry = False
        
        for i, line in enumerate(lines):
            # Skip headers and non-data lines
            if any(header in line.upper() for header in [
                'MALLIKOODI', 'MODEL CODE', 'MALLI', 'PAKETTI', 'MOOTTORI', 'VÄRI', 'HINTA', 'PRICE',
                'PAGE', 'SIVU', 'LYNX', 'SKI-DOO', 'HINNASTO', 'PRICE LIST'
            ]):
                continue
            
            # Look for model code pattern (usually 4 uppercase letters)
            model_code_match = re.match(r'^([A-Z]{4})', line)
            if model_code_match:
                # Save previous entry if we have one
                if current_entry and self.is_valid_entry(current_entry):
                    entries.append(current_entry.copy())
                
                # Start new entry
                current_entry = {
                    'model_code': model_code_match.group(1),
                    'page_number': page_num
                }
                collecting_entry = True
                
                # Try to extract other fields from the same line
                remaining_line = line[4:].strip()
                self.parse_entry_fields(remaining_line, current_entry)
                
            elif collecting_entry and current_entry:
                # Continue parsing fields for current entry
                self.parse_entry_fields(line, current_entry)
                
                # If we have price, this entry is complete
                if 'price' in current_entry:
                    if self.is_valid_entry(current_entry):
                        entries.append(current_entry.copy())
                    current_entry = {}
                    collecting_entry = False
        
        # Don't forget the last entry
        if current_entry and self.is_valid_entry(current_entry):
            entries.append(current_entry)
        
        return entries
    
    def parse_entry_fields(self, line: str, entry: Dict[str, Any]):
        """Parse individual fields from a line"""
        
        # Look for price (usually EUR at the end)
        price_match = re.search(r'(\d{1,3}(?:\s?\d{3})*)[.,]?(\d{2})?\s*€?(?:\s*EUR)?', line)
        if price_match and 'price' not in entry:
            price_str = price_match.group(1).replace(' ', '') + '.' + (price_match.group(2) or '00')
            try:
                entry['price'] = float(price_str)
            except ValueError:
                pass
        
        # Remove price from line for other field parsing
        line_without_price = re.sub(r'\d{1,3}(?:\s?\d{3})*[.,]?\d{0,2}\s*€?\s*EUR?', '', line).strip()
        
        # Parse remaining fields
        parts = [part.strip() for part in line_without_price.split('|') if part.strip()]
        
        if not parts:
            # Try splitting by multiple spaces
            parts = [part.strip() for part in re.split(r'\s{2,}', line_without_price) if part.strip()]
        
        # Assign fields based on what we don't have yet
        for part in parts:
            if not part or len(part) < 2:
                continue
                
            if 'malli' not in entry and any(model in part.upper() for model in [
                'SUMMIT', 'MXZ', 'RENEGADE', 'EXPEDITION', 'BACKCOUNTRY', 'FREERIDE', 
                'GRAND TOURING', 'SKANDIC', 'TUNDRA', 'RAVE', 'ADVENTURE', 'RANGER'
            ]):
                entry['malli'] = part
                
            elif 'paketti' not in entry and any(pkg in part.upper() for pkg in [
                'PKG', 'PACKAGE', 'EXPERT', 'COMPETITION', 'SPORT', 'ADRENALINE', 'NEO', 'XTREME'
            ]):
                entry['paketti'] = part
                
            elif 'moottori' not in entry and any(engine in part.upper() for engine in [
                'E-TEC', 'ETEC', 'ACE', 'TURBO', '600', '850', '900'
            ]):
                entry['moottori'] = part
                
            elif 'vari' not in entry and len(part.split()) <= 3:  # Colors are usually short
                # Could be color, but we'll be conservative
                entry['vari'] = part
    
    def is_valid_entry(self, entry: Dict[str, Any]) -> bool:
        """Check if entry has minimum required fields"""
        required_fields = ['model_code', 'price']
        return all(field in entry for field in required_fields)
    
    def save_to_database(self, entries: List[Dict[str, Any]], brand: str, year: int) -> int:
        """Save entries to database"""
        
        if not entries:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing data for this brand/year
        cursor.execute("DELETE FROM price_entries WHERE brand = ? AND model_year = ?", (brand, year))
        print(f"    Cleared existing {brand} {year} entries")
        
        saved_count = 0
        
        for entry in entries:
            try:
                # Generate normalized fields
                normalized_model = self.normalizer.normalize_model_name(entry.get('malli', ''))
                normalized_package = self.normalizer.normalize_package_name(entry.get('paketti', ''))
                normalized_engine = self.normalizer.normalize_engine_spec(entry.get('moottori', ''))
                
                cursor.execute("""
                    INSERT INTO price_entries (
                        id, price_list_id, model_code, malli, paketti, moottori, vari, price,
                        currency, market, brand, model_year, catalog_lookup_key,
                        normalized_model_name, normalized_package_name, normalized_engine_spec,
                        extraction_timestamp, extraction_method, parser_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),  # id
                    f"{brand}_{year}_PRICE_LIST",  # price_list_id
                    entry['model_code'],  # model_code
                    entry.get('malli'),  # malli
                    entry.get('paketti'),  # paketti
                    entry.get('moottori'),  # moottori
                    entry.get('vari'),  # vari
                    entry['price'],  # price
                    'EUR',  # currency
                    'FINLAND',  # market
                    brand,  # brand
                    year,  # model_year
                    f"{brand}_{year}_{entry['model_code']}",  # catalog_lookup_key
                    normalized_model,  # normalized_model_name
                    normalized_package,  # normalized_package_name
                    normalized_engine,  # normalized_engine_spec
                    datetime.now().isoformat(),  # extraction_timestamp
                    'comprehensive_extractor',  # extraction_method
                    '1.0'  # parser_version
                ))
                saved_count += 1
                
            except Exception as e:
                print(f"    [WARNING] Failed to save entry {entry.get('model_code', 'UNKNOWN')}: {e}")
        
        conn.commit()
        conn.close()
        
        return saved_count
    
    def verify_database_contents(self):
        """Verify what's now in the database"""
        print("\n=== DATABASE VERIFICATION ===")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get counts by brand/year
        cursor.execute("""
            SELECT brand, model_year, COUNT(*) as entries 
            FROM price_entries 
            GROUP BY brand, model_year 
            ORDER BY brand, model_year
        """)
        
        total_entries = 0
        for brand, year, count in cursor.fetchall():
            print(f"  {brand} {year}: {count} entries")
            total_entries += count
        
        print(f"\nTotal entries in database: {total_entries}")
        
        # Sample entries
        print("\nSample entries:")
        cursor.execute("""
            SELECT brand, model_year, model_code, malli, paketti, price 
            FROM price_entries 
            ORDER BY brand, model_year, model_code 
            LIMIT 10
        """)
        
        for brand, year, code, malli, paketti, price in cursor.fetchall():
            print(f"  {brand} {year} | {code}: {malli} {paketti or ''} - {price}€")
        
        conn.close()

if __name__ == "__main__":
    extractor = ComprehensivePriceExtractor()
    results = extractor.extract_all_price_lists()