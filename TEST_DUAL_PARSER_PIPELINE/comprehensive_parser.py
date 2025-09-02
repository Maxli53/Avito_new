import re
import pdfplumber
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from typing import List, Dict, Any, Optional

def extract_comprehensive_ski_doo_data(pdf_path: Path) -> List[Dict[str, Any]]:
    """Comprehensive extraction of all fields from SKI-DOO price list"""
    entries = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            print(f"\n=== Processing Page {page_num + 1} ===")
            
            # Extract tables first (more structured)
            tables = page.extract_tables()
            if tables:
                for table_idx, table in enumerate(tables):
                    entries.extend(parse_table_data(table, page_num + 1, table_idx))
            
            # Also try text extraction as fallback
            text = page.extract_text()
            if text:
                entries.extend(parse_text_data(text, page_num + 1))
    
    # Deduplicate by model_code
    unique_entries = {}
    for entry in entries:
        model_code = entry.get('model_code')
        if model_code and model_code not in unique_entries:
            unique_entries[model_code] = entry
    
    return list(unique_entries.values())

def parse_table_data(table: List[List], page_num: int, table_idx: int) -> List[Dict[str, Any]]:
    """Parse structured table data"""
    entries = []
    
    if not table or len(table) < 2:
        return entries
    
    print(f"Table {table_idx} has {len(table)} rows x {len(table[0]) if table[0] else 0} columns")
    
    # Find header row with field names
    header_row = None
    data_start_row = None
    
    for i, row in enumerate(table):
        if row and any('Tuote-' in str(cell) or 'nro' in str(cell) for cell in row if cell):
            header_row = i
            data_start_row = i + 1
            break
    
    if header_row is None:
        print("No header row found, trying text parsing")
        return entries
    
    # Map column headers to indices
    headers = table[header_row]
    column_map = {}
    
    for col_idx, header in enumerate(headers):
        if header:
            header = str(header).strip().lower()
            if 'tuote' in header or 'nro' in header:
                column_map['model_code'] = col_idx
            elif 'malli' in header:
                column_map['malli'] = col_idx
            elif 'paketti' in header:
                column_map['paketti'] = col_idx
            elif 'moottori' in header:
                column_map['moottori'] = col_idx
            elif 'telamatto' in header:
                column_map['telamatto'] = col_idx
            elif 'käynnistin' in header or 'kaynnistin' in header:
                column_map['kaynnistin'] = col_idx
            elif 'mittaristo' in header:
                column_map['mittaristo'] = col_idx
            elif 'kevät' in header or 'optiot' in header:
                column_map['kevatoptiot'] = col_idx
            elif 'väri' in header or 'vari' in header:
                column_map['vari'] = col_idx
            elif 'hinta' in header or 'suositus' in header:
                column_map['price'] = col_idx
    
    print(f"Column mapping: {column_map}")
    
    # Process data rows
    for row_idx in range(data_start_row, len(table)):
        row = table[row_idx]
        if not row or not any(row):
            continue
        
        # Look for model code pattern
        model_code = None
        for cell in row:
            if cell and re.match(r'^[A-Z]{4}$', str(cell).strip()):
                model_code = str(cell).strip()
                break
        
        if not model_code:
            continue
        
        # Extract all fields
        entry_data = extract_row_data(row, column_map, model_code)
        if entry_data:
            entries.append(entry_data)
            print(f"Extracted from table: {model_code} - {entry_data.get('malli')} - {entry_data.get('price')}€")
    
    return entries

def parse_text_data(text: str, page_num: int) -> List[Dict[str, Any]]:
    """Parse unstructured text data as fallback"""
    entries = []
    lines = text.split('\n')
    
    print(f"Parsing text data from page {page_num}")
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for model code at start of line
        if re.match(r'^[A-Z]{4}\s+', line):
            model_code = line[:4]
            
            # Collect full entry (may span multiple lines)
            full_entry = line
            j = i + 1
            
            # Continue collecting lines until we hit another model code or empty line
            while j < len(lines):
                next_line = lines[j].strip()
                if not next_line:
                    break
                if re.match(r'^[A-Z]{4}\s+', next_line):
                    break
                full_entry += ' ' + next_line
                j += 1
            
            # Parse the complete entry
            entry_data = parse_full_text_entry(full_entry, model_code)
            if entry_data:
                entries.append(entry_data)
                print(f"Extracted from text: {model_code} - {entry_data.get('malli')} - {entry_data.get('price')}€")
            
            i = j
        else:
            i += 1
    
    return entries

def extract_row_data(row: List, column_map: Dict, model_code: str) -> Optional[Dict[str, Any]]:
    """Extract data from a table row using column mapping"""
    try:
        # Get values from mapped columns
        malli = safe_get_cell(row, column_map.get('malli'))
        paketti = safe_get_cell(row, column_map.get('paketti'))
        moottori = safe_get_cell(row, column_map.get('moottori'))
        telamatto = safe_get_cell(row, column_map.get('telamatto'))
        kaynnistin = safe_get_cell(row, column_map.get('kaynnistin'))
        mittaristo = safe_get_cell(row, column_map.get('mittaristo'))
        kevatoptiot = safe_get_cell(row, column_map.get('kevatoptiot'))
        vari = safe_get_cell(row, column_map.get('vari'))
        
        # Extract price from price column or entire row
        price = None
        price_col = column_map.get('price')
        if price_col is not None:
            price = safe_get_cell(row, price_col)
        
        # If price not found in mapped column, search entire row
        if not price:
            for cell in row:
                if cell and '€' in str(cell):
                    price = str(cell)
                    break
        
        if price:
            price_decimal = parse_price(price)
            if price_decimal:
                return create_entry(model_code, malli, paketti, moottori, telamatto, 
                                  kaynnistin, mittaristo, kevatoptiot, vari, price_decimal)
    except Exception as e:
        print(f"Error extracting row data: {e}")
    
    return None

def parse_full_text_entry(full_entry: str, model_code: str) -> Optional[Dict[str, Any]]:
    """Parse a complete text entry with all fields"""
    try:
        print(f"Parsing entry: {full_entry[:100]}...")
        
        # Extract price first (most reliable anchor)
        price_match = re.search(r'(\d+\s?\d*\s?\d*),(\d{2})\s*€', full_entry)
        if not price_match:
            return None
        
        price_decimal = Decimal(price_match.group(1).replace(' ', '') + '.' + price_match.group(2))
        
        # Remove model code from start
        text_after_code = full_entry[4:].strip()
        
        # Remove price from end
        text_before_price = full_entry[:price_match.start()].strip()
        if text_before_price.endswith(model_code):
            text_before_price = text_before_price[:-4].strip()
        else:
            text_before_price = text_before_price[4:].strip()  # Remove model code
        
        # Split into components
        components = text_before_price.split()
        
        # Parse components using position and keyword clues
        malli = None
        paketti = None
        moottori = None
        telamatto = None
        kaynnistin = None
        mittaristo = None
        kevatoptiot = None
        vari = None
        
        idx = 0
        
        # Model (first significant word)
        if idx < len(components):
            malli = components[idx]
            idx += 1
        
        # Package (second word, unless it's engine-related)
        if idx < len(components) and not is_engine_word(components[idx]):
            paketti = components[idx]
            idx += 1
        
        # Engine (look for HP, EFI, E-TEC patterns)
        engine_parts = []
        while idx < len(components) and (is_engine_word(components[idx]) or 
                                        (engine_parts and is_engine_continuation(components[idx]))):
            engine_parts.append(components[idx])
            idx += 1
        
        if engine_parts:
            moottori = ' '.join(engine_parts)
        
        # Track (look for measurements: 120in, 146in, mm, etc.)
        track_parts = []
        while idx < len(components) and is_track_word(components[idx]):
            track_parts.append(components[idx])
            idx += 1
            # Check for continuation (like "3700mm")
            if idx < len(components) and (components[idx].endswith('mm') or components[idx].isdigit()):
                track_parts.append(components[idx])
                idx += 1
        
        if track_parts:
            telamatto = ' '.join(track_parts)
        
        # Starter (Electric, SHOT)
        if idx < len(components) and components[idx].lower() in ['electric', 'shot']:
            kaynnistin = components[idx]
            idx += 1
        
        # Display (look for display-related terms)
        display_parts = []
        while idx < len(components) and is_display_word(components[idx]):
            display_parts.append(components[idx])
            idx += 1
            # Continue with display-related words
            while idx < len(components) and is_display_continuation(components[idx]):
                display_parts.append(components[idx])
                idx += 1
            break
        
        if display_parts:
            mittaristo = ' '.join(display_parts)
        
        # Spring options (kevätoptiot) - look for specific option names
        option_parts = []
        while idx < len(components) and is_spring_option(components[idx]):
            option_parts.append(components[idx])
            idx += 1
        
        if option_parts:
            kevatoptiot = ' '.join(option_parts)
        
        # Color (remaining words)
        if idx < len(components):
            color_parts = components[idx:]
            # Clean up color (remove common non-color words)
            clean_color_parts = [part for part in color_parts if not is_non_color_word(part)]
            if clean_color_parts:
                vari = ' '.join(clean_color_parts)
        
        return create_entry(model_code, malli, paketti, moottori, telamatto, 
                          kaynnistin, mittaristo, kevatoptiot, vari, price_decimal)
        
    except Exception as e:
        print(f"Error parsing text entry: {e}")
        return None

def safe_get_cell(row: List, col_idx: Optional[int]) -> Optional[str]:
    """Safely get cell value from row"""
    if col_idx is None or col_idx >= len(row):
        return None
    cell = row[col_idx]
    return str(cell).strip() if cell else None

def parse_price(price_str: str) -> Optional[Decimal]:
    """Parse price string to Decimal"""
    if not price_str:
        return None
    
    # Remove non-numeric characters except comma, period, and space
    price_clean = re.sub(r'[^\d\s,.]', '', str(price_str))
    
    # Handle European format: "10 100,00"
    if ',' in price_clean and '.' not in price_clean:
        price_clean = price_clean.replace(' ', '').replace(',', '.')
    elif ' ' in price_clean:
        price_clean = price_clean.replace(' ', '')
    
    try:
        return Decimal(price_clean)
    except:
        return None

def is_engine_word(word: str) -> bool:
    """Check if word is engine-related"""
    word_lower = word.lower()
    return any(x in word_lower for x in ['600', '850', 'hp', 'efi', 'tec', 'ace'])

def is_engine_continuation(word: str) -> bool:
    """Check if word continues engine description"""
    word_lower = word.lower()
    return word_lower in ['e-tec', '-', 'hp'] or word.isdigit()

def is_track_word(word: str) -> bool:
    """Check if word is track-related"""
    return 'in' in word or 'mm' in word or (word.endswith('in') and any(c.isdigit() for c in word))

def is_display_word(word: str) -> bool:
    """Check if word is display-related"""
    word_lower = word.lower()
    return any(x in word_lower for x in ['display', 'digital', 'touchscreen', 'color']) or \
           (('in' in word or 'in.' in word) and any(c.isdigit() for c in word))

def is_display_continuation(word: str) -> bool:
    """Check if word continues display description"""
    word_lower = word.lower()
    return word_lower in ['digital', 'display', 'color', 'touchscreen', 'in.']

def is_spring_option(word: str) -> bool:
    """Check if word is a spring option"""
    word_lower = word.lower()
    # Add known spring options here
    spring_options = ['qrs', 'rmotion', 'sc5', 'tmotion']
    return word_lower in spring_options

def is_non_color_word(word: str) -> bool:
    """Check if word should be excluded from color"""
    word_lower = word.lower()
    return word_lower in ['display', 'digital', 'touchscreen', 'electric', 'shot', 'hp', 'efi']

def create_entry(model_code: str, malli: Optional[str], paketti: Optional[str], 
                moottori: Optional[str], telamatto: Optional[str], kaynnistin: Optional[str],
                mittaristo: Optional[str], kevatoptiot: Optional[str], vari: Optional[str],
                price: Decimal) -> Dict[str, Any]:
    """Create standardized entry dict"""
    
    catalog_lookup_key = f"{malli or 'UNKNOWN'}_{paketti or 'STANDARD'}_{moottori or 'UNKNOWN'}"
    
    return {
        'id': uuid4(),
        'model_code': model_code,
        'malli': malli,
        'paketti': paketti,
        'moottori': moottori,
        'telamatto': telamatto,
        'kaynnistin': kaynnistin,
        'mittaristo': mittaristo,
        'kevatoptiot': kevatoptiot,
        'vari': vari,
        'price': price,
        'currency': 'EUR',
        'market': 'FI',
        'brand': 'SKI-DOO',
        'model_year': 2026,
        'catalog_lookup_key': catalog_lookup_key
    }

if __name__ == "__main__":
    pdf_path = Path("../data/SKI-DOO_2026-PRICE_LIST.pdf")
    entries = extract_comprehensive_ski_doo_data(pdf_path)
    print(f"\n=== FINAL RESULTS ===")
    print(f"Total entries extracted: {len(entries)}")
    
    for i, entry in enumerate(entries[:10]):  # Show first 10
        print(f"\nEntry {i+1}:")
        for key, value in entry.items():
            if key != 'id':
                print(f"  {key}: {value}")