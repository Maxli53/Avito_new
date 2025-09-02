"""
Smart Price List Extractor - LLM-Powered
Adapted from production optimized_price_list_extractor.py for test environment
"""

import os
import json
import re
import fitz
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

class SmartPriceExtractor:
    """LLM-powered extraction from PRICE_LIST PDFs"""
    
    def __init__(self, db_path: str = "snowmobile_reconciliation.db", docs_folder: str = "docs"):
        self.db_path = db_path
        self.docs_folder = Path(docs_folder)
        
        # All available price lists
        self.price_lists = [
            ("LYNX", 2024, "LYNX_2024-PRICE_LIST.pdf"),
            ("LYNX", 2025, "LYNX_2025-PRICE_LIST.pdf"), 
            ("LYNX", 2026, "LYNX_2026-PRICE_LIST.pdf"),
            ("SKI-DOO", 2024, "SKI-DOO_2024-PRICE_LIST.pdf"),
            ("SKI-DOO", 2025, "SKI-DOO_2025-PRICE_LIST.pdf"),
            ("SKI-DOO", 2026, "SKI-DOO_2026-PRICE_LIST.pdf"),
        ]
    
    def extract_full_pdf_text(self, pdf_path: str) -> str:
        """Extract text from entire PDF file"""
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            total_pages = len(doc)
            
            for page_num in range(total_pages):
                page = doc[page_num]
                page_text = page.get_text()
                full_text += f"\n--- PAGE {page_num + 1} ---\n{page_text}\n"
            
            doc.close()
            print(f"    Extracted {len(full_text)} characters from {total_pages} pages")
            
            # Clean up Unicode characters
            full_text = full_text.encode('utf-8', errors='ignore').decode('utf-8')
            
            return full_text
            
        except Exception as e:
            print(f"    Error extracting PDF {pdf_path}: {e}")
            return ""
    
    def create_finnish_extraction_prompt(self, brand: str, year: str) -> str:
        """Create extraction prompt for Finnish PRICE_LIST"""
        return f"""You are analyzing a {brand} {year} PRICE_LIST PDF text. Extract ALL article information with Finnish field mapping.

Finnish column headers: Tuotenro, Malli, Paketti, Moottori, Telamatto, Käynnistin, Kevätoptiot, Mittaristo, Väri, Suositushinta

Field mapping:
- Tuotenro → article_code (4-letter model codes like BPTB, TJTH)
- Malli → model (Summit, MXZ, etc.)
- Paketti → package (Neo+, X with Expert Pkg, etc.)  
- Moottori → engine (600 EFI - 55 HP, 850 E-TEC Turbo R, etc.)
- Telamatto → track (146in 3700mm 1.6in 41mm Cobra Flex, etc.)
- Käynnistin → starter (Electric, SHOT)
- Kevätoptiot → spring_options (empty for most entries)
- Mittaristo → gauge (4.5 in. Digital Display, 10.25 in. Color Touchscreen Display)
- Väri → color (Neo Yellow, Terra Green, Black, etc.)
- Suositushinta → price (10 100,00 €, 27 270,00 €)

RETURN ONLY valid JSON array. No explanations, no markdown. Start with [ and end with ].

[
  {{
    "article_code": "BPTB",
    "model": "MXZ",
    "package": "Neo+",
    "engine": "600 EFI - 55 HP",
    "track": "120in 3050mm 1.25in 32mm RipSaw", 
    "starter": "Electric",
    "spring_options": "",
    "gauge": "4.5 in. Digital Display",
    "color": "Neo Yellow / Black",
    "price": "10 100,00 €",
    "brand": "{brand}",
    "year": "{year}"
  }}
]

Extract ALL visible rows. Use empty string "" for missing data. NO inventions - only what you see."""

    def extract_with_claude(self, pdf_text: str, brand: str, year: str) -> List[Dict[str, Any]]:
        """Extract articles using Claude"""
        try:
            import anthropic
            
            api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
            if not api_key:
                print("    No ANTHROPIC_API_KEY or CLAUDE_API_KEY found")
                return []
            
            client = anthropic.Anthropic(api_key=api_key)
            system_prompt = self.create_finnish_extraction_prompt(brand, year)
            
            user_content = f"""BRAND: {brand}
YEAR: {year}

PDF TEXT:
{pdf_text}

Extract ALL article information from this entire PDF. Return pure JSON array only."""

            print(f"    Calling Claude with {len(pdf_text)} characters...")
            
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Use available Claude model
                max_tokens=8000,
                temperature=0.1,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}]
            )
            
            content = response.content[0].text.strip()
            
            # Parse JSON response
            try:
                clean_content = content.strip()
                if clean_content.startswith('```json'):
                    clean_content = clean_content.replace('```json', '').replace('```', '').strip()
                
                articles = json.loads(clean_content)
                if isinstance(articles, list):
                    print(f"    Claude extracted {len(articles)} articles")
                    return articles
                else:
                    print(f"    Unexpected response format")
                    return []
                    
            except json.JSONDecodeError as e:
                print(f"    JSON parsing failed: {e}")
                print(f"    Content preview: {content[:200]}...")
                return []
                
        except Exception as e:
            print(f"    Claude extraction failed: {e}")
            return []
    
    def parse_finnish_price(self, price_str: str) -> Optional[float]:
        """Parse Finnish price format like '10 100,00 €'"""
        if not price_str:
            return None
        
        try:
            # Remove € and extra spaces
            clean_price = price_str.replace('€', '').strip()
            clean_price = clean_price.replace('\xa0', ' ')
            
            # Extract price pattern: digits spaces digits comma digits
            price_match = re.search(r'(\d{1,3}(?:\s\d{3})*)[,.](\d{2})', clean_price)
            if price_match:
                euros = price_match.group(1).replace(' ', '')
                cents = price_match.group(2)
                return float(f"{euros}.{cents}")
            
            return None
            
        except Exception:
            return None
    
    def process_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and clean extracted articles"""
        processed = []
        
        for article in articles:
            # Parse price
            price_str = article.get('price', '')
            article['price_float'] = self.parse_finnish_price(price_str)
            
            # Combine model + package into model_line
            model = article.get('model', '')
            package = article.get('package', '')
            if model and package:
                article['model_line'] = f"{model} {package}".strip()
            else:
                article['model_line'] = model or package or ''
            
            # Add metadata
            article['extraction_timestamp'] = datetime.now().isoformat()
            article['extraction_method'] = 'smart_extractor'
            
            processed.append(article)
        
        return processed
    
    def save_articles_to_db(self, articles: List[Dict[str, Any]], brand: str, year: int) -> int:
        """Save articles to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing data
        cursor.execute("DELETE FROM price_entries WHERE brand = ? AND model_year = ? AND extraction_method = 'smart_extractor'", (brand, year))
        print(f"    Cleared existing {brand} {year} entries")
        
        saved_count = 0
        
        for article in articles:
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
                    f"{brand}_{year}_SMART",
                    article.get('article_code', ''),
                    article.get('model', ''),
                    article.get('package', ''),
                    article.get('engine', ''),
                    article.get('track', ''),
                    article.get('starter', ''),
                    article.get('gauge', ''),
                    article.get('spring_options', ''),
                    article.get('color', ''),
                    article.get('price_float'),
                    'EUR',
                    'FINLAND',
                    brand,
                    year,
                    f"{brand}_{year}_{article.get('article_code', '')}",
                    'smart_extractor',
                    '5.0',
                    1,  # source_catalog_page
                    article.get('model', '').upper() if article.get('model') else None,
                    article.get('package', '').upper() if article.get('package') else None,
                    article.get('engine', '').upper() if article.get('engine') else None
                ))
                saved_count += 1
                
            except Exception as e:
                print(f"    Failed to save {article.get('article_code', 'UNKNOWN')}: {e}")
        
        conn.commit()
        conn.close()
        
        return saved_count
    
    def extract_price_list(self, brand: str, year: int, filename: str) -> Dict[str, Any]:
        """Extract single price list"""
        pdf_path = self.docs_folder / filename
        
        if not pdf_path.exists():
            print(f"    PDF not found: {filename}")
            return {'articles': [], 'saved': 0}
        
        print(f"  Processing {brand} {year}...")
        
        # Extract PDF text
        pdf_text = self.extract_full_pdf_text(str(pdf_path))
        if not pdf_text:
            return {'articles': [], 'saved': 0}
        
        # Extract articles with Claude
        raw_articles = self.extract_with_claude(pdf_text, brand, year)
        if not raw_articles:
            return {'articles': [], 'saved': 0}
        
        # Process articles
        processed_articles = self.process_articles(raw_articles)
        
        # Save to database
        saved = self.save_articles_to_db(processed_articles, brand, year)
        
        print(f"    SUCCESS: {len(processed_articles)} articles extracted, {saved} saved")
        
        return {
            'articles': processed_articles,
            'saved': saved,
            'brand': brand,
            'year': year
        }
    
    def extract_all_price_lists(self) -> Dict[str, Any]:
        """Extract all price lists"""
        print("=== SMART PRICE LIST EXTRACTION ===\n")
        
        results = {}
        total_articles = 0
        total_saved = 0
        
        for brand, year, filename in self.price_lists:
            result = self.extract_price_list(brand, year, filename)
            
            results[f"{brand}_{year}"] = result
            total_articles += len(result['articles'])
            total_saved += result['saved']
            
            print()  # Add spacing between price lists
        
        print(f"TOTAL: {total_articles} articles extracted, {total_saved} saved")
        
        # Save results to JSON
        with open('smart_extraction_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        return {
            'results': results,
            'total_articles': total_articles,
            'total_saved': total_saved
        }

if __name__ == "__main__":
    extractor = SmartPriceExtractor()
    results = extractor.extract_all_price_lists()
    
    if results['total_articles'] > 0:
        print(f"\nSUCCESS: {results['total_articles']} articles extracted across all price lists!")
    else:
        print(f"\nFAILED: No articles extracted")