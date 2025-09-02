"""
Tabular Price List Extractor - Sequential Field Lines
The PDF data is in tabular format where each field is on a separate line:
Line 1: Model Code (BPTB)
Line 2: Model (MXZ)
Line 3: Package (Neo+)
Line 4: Engine (600 EFI - 55 HP)
etc.
"""

import fitz
import sqlite3
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

class TabularPriceExtractor:
    """Extract price data from tabular PDF format (sequential lines)"""
    
    def __init__(self, db_path: str = "snowmobile_reconciliation.db", docs_folder: str = "docs"):
        self.db_path = db_path
        self.docs_folder = Path(docs_folder)
        
        # Expected field sequence for SKI-DOO 2026
        self.skidoo_2026_fields = [
            "tuotenro",      # Product code (BPTB)
            "malli",         # Model (MXZ)
            "paketti",       # Package (Neo+)
            "moottori",      # Engine (600 EFI - 55 HP)
            "telamatto1",    # Track length (120in)
            "telamatto2",    # Track length metric (3050mm)
            "telamatto3",    # Track details (1.25in 32mm RipSaw)
            "kaynnistin",    # Starter (Electric/SHOT)
            "mittaristo",    # Gauge (4.5 in. Digital Display)
            "vari",          # Color (Neo Yellow / Black)
            "hinta"          # Price (10 100,00 €)
        ]
    
    def extract_skidoo_2026_tabular(self):
        """Extract SKI-DOO 2026 data from tabular format"""
        print("=== TABULAR EXTRACTION: SKI-DOO 2026 ===\n")
        
        pdf_path = self.docs_folder / "SKI-DOO_2026-PRICE_LIST.pdf"
        
        if not pdf_path.exists():
            print("SKI-DOO_2026-PRICE_LIST.pdf not found!")
            return []
        
        entries = []
        
        with fitz.open(pdf_path) as pdf:
            print(f"Processing {pdf.page_count} pages...")
            
            for page_num in range(pdf.page_count):
                page = pdf[page_num]
                text = page.get_text()
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                
                print(f"\nPage {page_num + 1}: {len(lines)} lines")
                
                # Find data sequences
                page_entries = self.extract_tabular_entries(lines, page_num + 1)
                entries.extend(page_entries)
                
                print(f"  Found {len(page_entries)} entries")
        
        print(f"\nTotal entries extracted: {len(entries)}")
        
        # Show samples
        print(f"\nSample entries:")
        for i, entry in enumerate(entries[:5], 1):
            print(f"  {i}. {entry['tuotenro']}: {entry['malli']} {entry['paketti']} ({entry['moottori']}) - {entry['price']}€")
        
        # Save to database
        if entries:
            saved = self.save_tabular_entries(entries, "SKI-DOO", 2026)
            print(f"\nSaved {saved} entries to database")
        
        return entries
    
    def extract_tabular_entries(self, lines: List[str], page_num: int) -> List[Dict[str, Any]]:
        """Extract entries from tabular format lines"""
        
        entries = []
        i = 0
        
        while i < len(lines):
            # Look for model code pattern (4 uppercase letters)
            line = lines[i]
            
            if re.match(r'^[A-Z]{4}$', line):
                # Found potential model code, try to extract complete entry
                entry = self.extract_variable_entry(lines, i, page_num)
                if entry:
                    entries.append(entry)
                    # Skip past this entry (variable length - use the actual length found)
                    i += entry.get('field_count', 11)
                else:
                    i += 1
            else:
                i += 1
        
        return entries
    
    def extract_single_entry(self, lines: List[str], start_idx: int, page_num: int) -> Optional[Dict[str, Any]]:
        """Extract a single entry starting from model code line"""
        
        try:
            # Check if we have enough lines for complete entry
            if start_idx + 10 >= len(lines):
                return None
            
            # Extract fields according to expected sequence
            entry = {
                'page_number': page_num,
                'start_line': start_idx + 1
            }
            
            # Extract each field
            for field_idx, field_name in enumerate(self.skidoo_2026_fields):
                line_idx = start_idx + field_idx
                if line_idx < len(lines):
                    raw_value = lines[line_idx]
                    entry[field_name] = raw_value
                else:
                    entry[field_name] = None
            
            # Validate this looks like a real entry
            if not self.validate_entry(entry):
                return None
            
            # Process price field
            entry['price'] = self.parse_finnish_price(entry.get('hinta', ''))
            if entry['price'] is None:
                return None
            
            # Combine track fields
            entry['telamatto'] = f"{entry.get('telamatto1', '')} {entry.get('telamatto2', '')} {entry.get('telamatto3', '')}".strip()
            
            return entry
            
        except Exception as e:
            print(f"    [WARNING] Failed to extract entry at line {start_idx + 1}: {e}")
            return None
    
    def validate_entry(self, entry: Dict[str, Any]) -> bool:
        """Validate that extracted entry looks reasonable"""
        
        # Must have model code
        tuotenro = entry.get('tuotenro', '')
        if not re.match(r'^[A-Z]{4}$', tuotenro):
            return False
        
        # Must have model name
        malli = entry.get('malli', '')
        if not malli or len(malli) < 2:
            return False
        
        # Must have price that looks like Finnish format
        hinta = entry.get('hinta', '')
        if not hinta or '€' not in hinta:
            return False
        
        # Engine field should contain engine info
        moottori = entry.get('moottori', '')
        if not moottori or not any(pattern in moottori.upper() for pattern in ['HP', 'E-TEC', 'ACE', 'EFI']):
            return False
        
        return True
    
    def parse_finnish_price(self, price_str: str) -> Optional[float]:
        """Parse Finnish price format like '10 100,00 €' or '27 270,00 €'"""
        
        if not price_str:
            return None
        
        try:
            # Remove € and extra spaces
            clean_price = price_str.replace('€', '').strip()
            
            # Handle non-breaking space (\xa0)
            clean_price = clean_price.replace('\xa0', ' ')
            
            # Extract price pattern: digits spaces digits comma digits
            price_match = re.search(r'(\d{1,3}(?:\s\d{3})*)[,.](\d{2})', clean_price)
            if price_match:
                # Convert format like "27 270,00" to 27270.00
                euros = price_match.group(1).replace(' ', '')
                cents = price_match.group(2)
                return float(f"{euros}.{cents}")
            
            return None
            
        except Exception as e:
            print(f"    [WARNING] Failed to parse price '{price_str}': {e}")
            return None
    
    def save_tabular_entries(self, entries: List[Dict[str, Any]], brand: str, year: int) -> int:
        """Save tabular entries to database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing data for this brand/year
        cursor.execute("DELETE FROM price_entries WHERE brand = ? AND model_year = ? AND extraction_method = 'tabular_extractor'", (brand, year))
        print(f"Cleared existing {brand} {year} tabular entries")
        
        saved_count = 0
        
        for entry in entries:
            try:
                cursor.execute("""
                    INSERT INTO price_entries (
                        price_list_id, model_code, malli, paketti, moottori, telamatto, kaynnistin, 
                        mittaristo, kevatoptiot, vari, price, currency, market, brand, 
                        model_year, catalog_lookup_key, extraction_method, parser_version,
                        source_catalog_page, normalized_model_name, normalized_package_name, 
                        normalized_engine_spec
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"{brand}_{year}_TABULAR",  # price_list_id
                    entry['tuotenro'],  # model_code
                    entry.get('malli'),  # malli
                    entry.get('paketti'),  # paketti
                    entry.get('moottori'),  # moottori
                    entry.get('telamatto'),  # telamatto (combined)
                    entry.get('kaynnistin'),  # kaynnistin
                    entry.get('mittaristo'),  # mittaristo
                    None,  # kevatoptiot (spring options)
                    entry.get('vari'),  # vari
                    entry.get('price'),  # price
                    'EUR',  # currency
                    'FINLAND',  # market
                    brand,  # brand
                    year,  # model_year
                    f"{brand}_{year}_{entry['tuotenro']}",  # catalog_lookup_key
                    'tabular_extractor',  # extraction_method
                    '3.0',  # parser_version
                    entry.get('page_number'),  # source_catalog_page
                    entry.get('malli', '').upper() if entry.get('malli') else None,  # normalized_model_name
                    entry.get('paketti', '').upper() if entry.get('paketti') else None,  # normalized_package_name
                    entry.get('moottori', '').upper() if entry.get('moottori') else None  # normalized_engine_spec
                ))
                saved_count += 1
                
            except Exception as e:
                print(f"    [WARNING] Failed to save {entry.get('tuotenro', 'UNKNOWN')}: {e}")
        
        conn.commit()
        conn.close()
        
        return saved_count
    
    def debug_tjth_extraction(self):
        """Debug extraction of TJTH entry specifically"""
        print("=== DEBUG: TJTH EXTRACTION ===\n")
        
        pdf_path = self.docs_folder / "SKI-DOO_2026-PRICE_LIST.pdf"
        
        with fitz.open(pdf_path) as pdf:
            for page_num in range(pdf.page_count):
                page = pdf[page_num]
                text = page.get_text()
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                
                # Find TJTH
                for i, line in enumerate(lines):
                    if line == 'TJTH':
                        print(f"Found TJTH on page {page_num + 1}, line {i + 1}")
                        print(f"Next 15 lines:")  # Show more lines
                        
                        for j in range(15):
                            if i + j < len(lines):
                                print(f"  {j+1:2d}: '{lines[i + j]}'")
                        
                        # Find the price line
                        price_line_idx = None
                        for j in range(15):
                            if i + j < len(lines) and '€' in lines[i + j]:
                                price_line_idx = j
                                print(f"\n  Price found at offset {j}: '{lines[i + j]}'")
                                break
                        
                        if price_line_idx:
                            print(f"\nTJTH has {price_line_idx + 1} fields (including model code)")
                            
                            # Try custom extraction for TJTH
                            entry = self.extract_tjth_custom(lines, i, page_num + 1)
                            if entry:
                                print(f"\nCustom extraction successful:")
                                for key, value in entry.items():
                                    print(f"  {key}: {value}")
                            else:
                                print(f"\nCustom extraction also failed")
                        
                        return
    
    def extract_variable_entry(self, lines: List[str], start_idx: int, page_num: int) -> Optional[Dict[str, Any]]:
        """Extract entry with variable field count - dynamically detect structure"""
        
        try:
            # Find the price line to determine entry length
            price_line_idx = None
            field_count = 0
            
            for i in range(1, 20):  # Check up to 20 lines ahead
                if start_idx + i >= len(lines):
                    break
                    
                if '€' in lines[start_idx + i] and any(char.isdigit() for char in lines[start_idx + i]):
                    price_line_idx = i
                    field_count = i + 1  # Include the price line
                    break
            
            if not price_line_idx:
                return None
            
            # Extract based on detected field count
            entry = {
                'page_number': page_num,
                'start_line': start_idx + 1,
                'field_count': field_count,
                'tuotenro': lines[start_idx]
            }
            
            # Standard fields that are consistent across entries
            if field_count >= 4:
                entry['malli'] = lines[start_idx + 1] 
                entry['paketti'] = lines[start_idx + 2]
                entry['moottori'] = lines[start_idx + 3]
            
            # Track fields (usually 3 consecutive lines after engine)
            track_parts = []
            track_start = 4
            track_end = min(7, field_count - 4)  # Leave room for other fields
            for i in range(track_start, track_end):
                if start_idx + i < len(lines):
                    track_parts.append(lines[start_idx + i])
            entry['telamatto'] = ' '.join(track_parts)
            
            # Find starter field (usually "Electric" or "SHOT")
            entry['kaynnistin'] = None
            for i in range(4, field_count - 1):
                if start_idx + i < len(lines):
                    line = lines[start_idx + i]
                    if any(keyword in line.upper() for keyword in ['ELECTRIC', 'SHOT']):
                        entry['kaynnistin'] = line
                        break
            
            # Find gauge field (usually contains "Display" or "in.")
            gauge_parts = []
            for i in range(4, field_count - 1):
                if start_idx + i < len(lines):
                    line = lines[start_idx + i]
                    if any(keyword in line for keyword in ['Display', 'in.', 'Touchscreen']):
                        gauge_parts.append(line)
            entry['mittaristo'] = ' '.join(gauge_parts)
            
            # Color fields (everything else between starter/gauge and price)
            color_parts = []
            for i in range(max(7, field_count - 6), field_count - 1):  # Last few lines before price
                if start_idx + i < len(lines):
                    line = lines[start_idx + i]
                    # Skip if it's already captured as starter or gauge
                    if (entry['kaynnistin'] and line == entry['kaynnistin']) or \
                       (entry['mittaristo'] and line in entry['mittaristo']):
                        continue
                    color_parts.append(line)
            entry['vari'] = ' '.join(color_parts)
            
            # Price (last line)
            price_str = lines[start_idx + price_line_idx]
            entry['price'] = self.parse_finnish_price(price_str)
            
            # Validate basic requirements
            if not self.validate_variable_entry(entry):
                return None
                
            return entry
            
        except Exception as e:
            print(f"    [WARNING] Failed to extract variable entry at line {start_idx + 1}: {e}")
            return None
    
    def validate_variable_entry(self, entry: Dict[str, Any]) -> bool:
        """Validate variable entry structure"""
        
        # Must have model code (4 uppercase letters)
        tuotenro = entry.get('tuotenro', '')
        if not re.match(r'^[A-Z]{4}$', tuotenro):
            return False
        
        # Must have model name  
        malli = entry.get('malli', '')
        if not malli or len(malli) < 2:
            return False
            
        # Must have valid price
        if not entry.get('price') or entry.get('price') <= 0:
            return False
        
        # Engine should contain engine indicators
        moottori = entry.get('moottori', '')
        if moottori and not any(pattern in moottori.upper() for pattern in ['HP', 'E-TEC', 'ACE', 'EFI', 'TURBO']):
            return False
            
        return True

    def extract_tjth_custom(self, lines: List[str], start_idx: int, page_num: int) -> Optional[Dict[str, Any]]:
        """Custom extraction for TJTH which has different field structure"""
        
        try:
            # TJTH field sequence (from debug output):
            # 1: 'TJTH'                          -> tuotenro
            # 2: 'Summit'                        -> malli  
            # 3: 'X with Expert Pkg'             -> paketti
            # 4: '850 E-TEC Turbo R'             -> moottori
            # 5: '165in'                         -> telamatto1
            # 6: '4200mm'                        -> telamatto2 
            # 7: '3.0in 76mm Powdermax X-light'  -> telamatto3
            # 8: 'SHOT'                          -> kaynnistin
            # 9: '10.25 in. Color'               -> mittaristo1
            # 10: 'Touchscreen Display'          -> mittaristo2
            # 11: '165 inch Track, Terra Green'  -> vari1
            # 12: 'Color Terra Green'            -> vari2
            # 13: '27 270,00 €'                 -> hinta
            
            entry = {
                'page_number': page_num,
                'start_line': start_idx + 1,
                'tuotenro': lines[start_idx],
                'malli': lines[start_idx + 1] if start_idx + 1 < len(lines) else None,
                'paketti': lines[start_idx + 2] if start_idx + 2 < len(lines) else None,
                'moottori': lines[start_idx + 3] if start_idx + 3 < len(lines) else None,
                'kaynnistin': lines[start_idx + 7] if start_idx + 7 < len(lines) else None,
            }
            
            # Combine track fields
            track_parts = []
            for i in [4, 5, 6]:  # Lines 5, 6, 7
                if start_idx + i < len(lines):
                    track_parts.append(lines[start_idx + i])
            entry['telamatto'] = ' '.join(track_parts)
            
            # Combine gauge fields  
            gauge_parts = []
            for i in [8, 9]:  # Lines 9, 10
                if start_idx + i < len(lines):
                    gauge_parts.append(lines[start_idx + i])
            entry['mittaristo'] = ' '.join(gauge_parts)
            
            # Combine color fields
            color_parts = []
            for i in [10, 11]:  # Lines 11, 12
                if start_idx + i < len(lines):
                    color_parts.append(lines[start_idx + i])
            entry['vari'] = ' '.join(color_parts)
            
            # Find price (should be around line 12-13)
            price_value = None
            for i in range(10, 15):  # Check lines 11-15 for price
                if start_idx + i < len(lines) and '€' in lines[start_idx + i]:
                    price_value = self.parse_finnish_price(lines[start_idx + i])
                    break
            
            entry['price'] = price_value
            
            # Validate
            if not entry['tuotenro'] or not entry['price']:
                return None
            
            return entry
            
        except Exception as e:
            print(f"    Custom TJTH extraction failed: {e}")
            return None

if __name__ == "__main__":
    extractor = TabularPriceExtractor()
    
    # First debug TJTH specifically
    extractor.debug_tjth_extraction()
    
    print("\n" + "="*60 + "\n")
    
    # Then extract all entries
    extractor.extract_skidoo_2026_tabular()