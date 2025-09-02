import re
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import pdfplumber
from typing import List, Dict, Any

def extract_ski_doo_prices(pdf_path: Path) -> List[Dict[str, Any]]:
    """Extract SKI-DOO price data using text parsing"""
    entries = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            
            # Look for price entries with pattern: PRODUCT_CODE Model Package Engine Track Starter Display Options Color Price
            # Using regex to find lines with model codes (4-letter codes like BPTB, TWTB, etc.)
            lines = text.split('\n')
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Skip header lines and empty lines
                if not line or 'Suositushinta' in line or 'KEVÄTTENNAKKOMALLI' in line:
                    continue
                
                # Look for pattern: 4-letter code followed by model name
                match = re.match(r'^([A-Z]{4})\s+(.+)', line)
                if match:
                    model_code = match.group(1)
                    rest_of_line = match.group(2).strip()
                    
                    # Try to parse the complete entry (might span multiple lines)
                    full_entry = line
                    
                    # Look ahead for continuation lines
                    j = i + 1
                    while j < len(lines) and lines[j].strip() and not re.match(r'^[A-Z]{4}\s+', lines[j]):
                        full_entry += ' ' + lines[j].strip()
                        j += 1
                    
                    # Extract price (format: 10 100,00 € or 22 310,00 €)
                    price_match = re.search(r'(\d+\s?\d*\s?\d*),(\d{2})\s*€', full_entry)
                    if price_match:
                        # Convert price string to decimal
                        price_str = price_match.group(1).replace(' ', '') + '.' + price_match.group(2)
                        price = Decimal(price_str)
                        
                        # Parse the components using known patterns
                        parts = full_entry.split()
                        
                        # Find indices of key components
                        model_idx = 1  # After model code
                        
                        # Find price position to work backwards
                        price_idx = -1
                        for idx, part in enumerate(parts):
                            if '€' in part:
                                price_idx = idx
                                break
                        
                        if price_idx > 0:
                            # Extract components between model and price
                            middle_parts = parts[model_idx:price_idx-2]  # Exclude price numbers
                            
                            # Try to identify components based on patterns
                            malli = None
                            paketti = None
                            moottori = None
                            telamatto = None
                            kaynnistin = None
                            mittaristo = None
                            kevatoptiot = None
                            vari = None
                            
                            # Simple heuristic parsing
                            current_idx = 0
                            
                            # Model name (first 1-2 words)
                            if current_idx < len(middle_parts):
                                malli = middle_parts[current_idx]
                                current_idx += 1
                            
                            # Package (if next word doesn't contain numbers/engine indicators)
                            if current_idx < len(middle_parts) and not any(x in middle_parts[current_idx].lower() for x in ['600', '850', 'hp', 'efi']):
                                paketti = middle_parts[current_idx]
                                current_idx += 1
                            
                            # Engine (look for HP or EFI patterns)
                            engine_parts = []
                            while current_idx < len(middle_parts):
                                part = middle_parts[current_idx]
                                if any(x in part.lower() for x in ['hp', 'efi', 'tec', '600', '850']):
                                    engine_parts.append(part)
                                    current_idx += 1
                                    # Continue collecting engine-related parts
                                    if current_idx < len(middle_parts) and middle_parts[current_idx] in ['-', 'E-TEC', 'HP']:
                                        engine_parts.append(middle_parts[current_idx])
                                        current_idx += 1
                                else:
                                    break
                            
                            if engine_parts:
                                moottori = ' '.join(engine_parts)
                            
                            # Track (look for "in" measurements)
                            track_parts = []
                            while current_idx < len(middle_parts):
                                part = middle_parts[current_idx]
                                if 'in' in part or 'mm' in part:
                                    track_parts.append(part)
                                    current_idx += 1
                                    # Get next part if it's also track-related
                                    if current_idx < len(middle_parts) and ('mm' in middle_parts[current_idx] or middle_parts[current_idx].isdigit()):
                                        track_parts.append(middle_parts[current_idx])
                                        current_idx += 1
                                else:
                                    break
                            
                            if track_parts:
                                telamatto = ' '.join(track_parts)
                            
                            # Starter (Electric, SHOT, etc.)
                            if current_idx < len(middle_parts) and middle_parts[current_idx].lower() in ['electric', 'shot']:
                                kaynnistin = middle_parts[current_idx]
                                current_idx += 1
                            
                            # Display (look for "Display" or "in." patterns)
                            display_parts = []
                            while current_idx < len(middle_parts):
                                part = middle_parts[current_idx]
                                if 'display' in part.lower() or 'touchscreen' in part.lower() or ('in.' in part and 'digital' in full_entry.lower()):
                                    display_parts.append(part)
                                    current_idx += 1
                                    # Continue collecting display parts
                                    while current_idx < len(middle_parts) and any(x in middle_parts[current_idx].lower() for x in ['digital', 'color', 'touchscreen']):
                                        display_parts.append(middle_parts[current_idx])
                                        current_idx += 1
                                    break
                                else:
                                    current_idx += 1
                            
                            if display_parts:
                                mittaristo = ' '.join(display_parts)
                            
                            # Remaining parts are likely color
                            remaining_parts = middle_parts[current_idx:]
                            if remaining_parts:
                                vari = ' '.join(remaining_parts)
                            
                            # Create catalog lookup key
                            catalog_lookup_key = f"{malli or 'UNKNOWN'}_{paketti or 'STANDARD'}_{moottori or 'UNKNOWN'}"
                            
                            entry = {
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
                                'market': 'FI',  # Finnish market
                                'brand': 'SKI-DOO',
                                'model_year': 2026,
                                'catalog_lookup_key': catalog_lookup_key
                            }
                            
                            entries.append(entry)
                            print(f"Extracted: {model_code} - {malli} - {price}€")
    
    return entries

if __name__ == "__main__":
    pdf_path = Path("../data/SKI-DOO_2026-PRICE_LIST.pdf")
    entries = extract_ski_doo_prices(pdf_path)
    print(f"\nTotal entries extracted: {len(entries)}")
    
    for i, entry in enumerate(entries[:5]):  # Show first 5
        print(f"\nEntry {i+1}:")
        for key, value in entry.items():
            if key != 'id':
                print(f"  {key}: {value}")