#!/usr/bin/env python3
"""
Optimized PRICE_LIST Extractor with Token Management
Uses proven token optimization system from global_parser.py for 10k tokens/min limit
"""

import os
import json
import re
import fitz  # PyMuPDF
import tiktoken
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI
from shared_utilities.common import AvitoDatabase, normalize_article_code

# Load environment
load_dotenv()

class OptimizedPriceListExtractor:
    """Token-optimized extraction from PRICE_LIST PDFs using proven KB system patterns"""
    
    def __init__(self, use_sqlite=True, preferred_model="Claude Sonnet 4"):
        # OpenAI rate limiting configuration (same as global_parser.py)
        self.tokens_per_minute_limit = 10000  # Your exact limit
        self.safety_buffer = 0.8  # 80% safety buffer
        self.effective_tpm_limit = int(self.tokens_per_minute_limit * self.safety_buffer)
        
        # Initialize SQLite database if enabled
        self.use_sqlite = use_sqlite
        self.db = AvitoDatabase() if use_sqlite else None
        
        # Set preferred model for extraction
        self.preferred_model = preferred_model
        
        # Token counter for GPT-4 (works for mini too)
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        self.token_usage_tracker = {
            'total_tokens': 0,
            'minute_tokens': 0,
            'minute_start': time.time(),
            'batch_tokens': 0
        }
        
        # PDF directory
        self.pdf_dir = Path("data_sources/price_lists")
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize API availability (will be tested when first needed)
        self.openai_available = False
        self.anthropic_available = False
        self._apis_tested = False
        
        # Page splitting configuration
        self.max_page_chars = 3000      # Split if page > 3000 chars
        self.overlap_chars = 200        # Overlap between chunks
        
        print(f"Initialized with {self.effective_tpm_limit} effective tokens/min limit")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using GPT-4 tokenizer (from global_parser.py:252)"""
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            print(f"Token counting error: {e}")
            # Fallback estimation: ~4 characters per token
            return len(text) // 4
    
    def estimate_request_tokens(self, system_prompt: str, user_content: str, estimated_response: int = 800) -> int:
        """Estimate total tokens for a GPT request (from global_parser.py:261)"""
        input_tokens = self.count_tokens(system_prompt) + self.count_tokens(user_content)
        return input_tokens + estimated_response
    
    def check_token_limits(self, estimated_tokens: int) -> bool:
        """Check if we can make request within rate limits (from global_parser.py:266)"""
        current_time = time.time()
        
        # Reset minute counter if a minute has passed
        if current_time - self.token_usage_tracker['minute_start'] >= 60:
            self.token_usage_tracker['minute_tokens'] = 0
            self.token_usage_tracker['minute_start'] = current_time
            print("Token minute counter reset")
        
        # Check if adding estimated tokens would exceed limit
        projected_minute_tokens = self.token_usage_tracker['minute_tokens'] + estimated_tokens
        
        if projected_minute_tokens > self.effective_tpm_limit:
            remaining_tokens = self.effective_tpm_limit - self.token_usage_tracker['minute_tokens']
            print(f"Token limit check: {estimated_tokens} needed, {remaining_tokens} available this minute")
            return False
        
        return True
    
    def update_token_usage(self, actual_tokens: int):
        """Update token usage tracking (from global_parser.py:286)"""
        self.token_usage_tracker['total_tokens'] += actual_tokens
        self.token_usage_tracker['minute_tokens'] += actual_tokens
        self.token_usage_tracker['batch_tokens'] += actual_tokens
        
        print(f"Token usage updated: +{actual_tokens} "
              f"(minute: {self.token_usage_tracker['minute_tokens']}/{self.effective_tpm_limit}, "
              f"total: {self.token_usage_tracker['total_tokens']})")
    
    def wait_for_rate_limit_reset(self):
        """Wait for rate limit to reset if needed (from global_parser.py:296)"""
        current_time = time.time()
        time_since_minute_start = current_time - self.token_usage_tracker['minute_start']
        
        if time_since_minute_start < 60:
            wait_time = 60 - time_since_minute_start
            print(f"Rate limit protection: waiting {wait_time:.1f}s for minute reset...")
            time.sleep(wait_time)
            
            # Reset counters after wait
            self.token_usage_tracker['minute_tokens'] = 0
            self.token_usage_tracker['minute_start'] = time.time()
    
    def extract_full_pdf_text(self, pdf_path: str) -> str:
        """Extract text from entire PDF file for Claude native processing"""
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                # Add page separator
                full_text += f"\n--- PAGE {page_num + 1} ---\n{page_text}\n"
            
            doc.close()
            print(f"Extracted {len(full_text)} characters from entire PDF ({len(doc)} pages)")
            
            # Clean up Unicode characters for UTF-8 compatibility  
            full_text = full_text.encode('utf-8', errors='ignore').decode('utf-8')
            
            return full_text
            
        except Exception as e:
            print(f"Error extracting PDF {pdf_path}: {e}")
            return ""

    def extract_pdf_text(self, pdf_path: str, page_number: int) -> str:
        """Extract text directly from PDF page (adapted from global_parser.py:310)"""
        try:
            doc = fitz.open(pdf_path)
            
            # Pages are 0-indexed in PyMuPDF
            page_index = page_number
            
            if page_index >= len(doc):
                print(f"Page {page_number + 1} not found in {os.path.basename(pdf_path)} ({len(doc)} pages)")
                doc.close()
                return ""
            
            page = doc[page_index]
            text = page.get_text()
            
            # Clean up Unicode characters for UTF-8 compatibility  
            text = text.encode('utf-8', errors='ignore').decode('utf-8')
            
            doc.close()
            print(f"Extracted {len(text)} characters from page {page_number + 1}")
            
            return text
            
        except Exception as e:
            print(f"Error extracting page {page_number + 1} from {pdf_path}: {e}")
            return ""
    
    def create_finnish_extraction_prompt(self, brand: str, year: str) -> str:
        """Create GPT prompt for Finnish PRICE_LIST extraction"""
        return f"""You are analyzing a {brand} {year} PRICE_LIST PDF text. Extract ALL article information with complete Finnish field mapping.

Finnish column headers may include: Tuotenro, Malli, Paketti, Moottori, Telamatto, Käynnistin, Kevätoptiot, Mittaristo, Väri, Suositushinta (sis ALV:n)

NOTE: Mittaristo (gauge) field is only available in 2026+ price lists. For 2024-2025 price lists, this field will be empty.

English field mapping:
- Tuotenro → article_code
- Malli → model  
- Paketti → package
- Moottori → engine
- Telamatto → track
- Käynnistin → starter
- Kevätoptiot → spring_options
- Mittaristo → gauge (empty for years before 2026)
- Väri → color
- Suositushinta → price_fi

CRITICAL INSTRUCTION: You MUST return ONLY a valid JSON array. No explanations, no markdown blocks, no additional text before or after. Start with [ and end with ]. If no articles found, return empty array [].

[
  {{
    "article_code": "exact_text_from_Tuotenro_column",
    "model": "exact_text_from_Malli_column",
    "package": "exact_text_from_Paketti_column", 
    "engine": "exact_text_from_Moottori_column",
    "track": "exact_text_from_Telamatto_column",
    "starter": "exact_text_from_Käynnistin_column",
    "spring_options": "exact_text_from_Kevätoptiot_column",
    "gauge": "exact_text_from_Mittaristo_column_or_empty_if_not_present",
    "color": "exact_text_from_Väri_column",
    "price_fi": "exact_text_from_price_column",
    "brand": "{brand}",
    "year": "{year}",
    "source_pdf": "{brand}_{year}_PRICE_LIST"
  }}
]

Extract ALL visible rows. Use empty string "" for missing data or fields not present in this year's format. NO inventions. ONLY what you see. 

RESPONSE FORMAT: Pure JSON array only. No other text."""
    
    def parse_filename(self, filename: str) -> tuple[str, str]:
        """Parse brand and year from PRICE_LIST filename"""
        try:
            # Extract brand (LYNX or SKI-DOO)
            if filename.startswith("LYNX"):
                brand = "LYNX"
            elif filename.startswith("SKI-DOO"):
                brand = "SKIDOO"  # Normalize to SKIDOO for consistency
            else:
                raise ValueError(f"Unknown brand in filename: {filename}")
            
            # Extract year (MY24, MY25, MY26 or direct year format)
            if "MY24" in filename or "_2024" in filename:
                year = "2024"
            elif "MY25" in filename or "_2025" in filename:
                year = "2025"
            elif "MY26" in filename or "_2026" in filename:
                year = "2026"
            else:
                raise ValueError(f"Unknown year format in filename: {filename}")
            
            return brand, year
            
        except Exception as e:
            print(f" Error parsing filename {filename}: {e}")
            raise
    
    def test_openai_connection(self) -> bool:
        """Test OpenAI API connectivity"""
        try:
            from openai import OpenAI
            client = OpenAI()
            
            print("Testing OpenAI API connection...")
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Test connection. Reply 'OK'."}],
                max_tokens=10,
                timeout=30
            )
            
            if response.choices[0].message.content.strip():
                print("OpenAI API Connection: SUCCESS")
                return True
            else:
                print("OpenAI API Connection: FAILED - No response")
                return False
                
        except Exception as e:
            print(f"OpenAI API Connection: FAILED")
            print(f"  Error Type: {type(e).__name__}")
            print(f"  Error Message: {str(e)}")
            return False
    
    def test_anthropic_connection(self) -> bool:
        """Test Anthropic Claude API connectivity"""
        try:
            import anthropic
            
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                print("Anthropic API Connection: FAILED - No ANTHROPIC_API_KEY found")
                return False
            
            client = anthropic.Anthropic(api_key=api_key)
            
            print("Testing Anthropic Claude API connection...")
            response = client.messages.create(
                model="claude-sonnet-4-20250514",  # Latest Claude Sonnet 4
                max_tokens=10,
                messages=[{"role": "user", "content": "Test connection. Reply 'OK'."}]
            )
            
            if response.content[0].text.strip():
                print("Anthropic Claude API Connection: SUCCESS")
                return True
            else:
                print("Anthropic Claude API Connection: FAILED - No response")
                return False
                
        except Exception as e:
            print(f"Anthropic Claude API Connection: FAILED")
            print(f"  Error Type: {type(e).__name__}")
            print(f"  Error Message: {str(e)}")
            return False
    
    def test_api_connections(self) -> tuple[bool, bool]:
        """Test both API connections and return availability"""
        openai_ok = self.test_openai_connection()
        anthropic_ok = self.test_anthropic_connection()
        
        if not openai_ok and not anthropic_ok:
            print("ERROR: Neither OpenAI nor Anthropic APIs are available")
            return False, False
        elif openai_ok and anthropic_ok:
            print("SUCCESS: Both OpenAI and Anthropic APIs available - will use Claude first with OpenAI fallback")
        elif openai_ok:
            print("SUCCESS: OpenAI API available - Anthropic not configured")
        else:
            print("SUCCESS: Only Anthropic Claude API available - will use Claude")
        
        return openai_ok, anthropic_ok
    
    def split_large_page(self, page_text: str) -> List[str]:
        """Split large pages into smaller chunks of max 3000 chars"""
        if len(page_text) <= self.max_page_chars:
            return [page_text]
        
        chunks = []
        start = 0
        while start < len(page_text):
            end = start + self.max_page_chars
            if end >= len(page_text):
                chunks.append(page_text[start:])
                break
            
            # Try to split at a natural break (newline, space)
            split_point = page_text.rfind('\n', start, end)
            if split_point == -1:
                split_point = page_text.rfind(' ', start, end)
            if split_point == -1:
                split_point = end
            
            chunks.append(page_text[start:split_point])
            start = split_point - self.overlap_chars if split_point > self.overlap_chars else 0
        
        return chunks
    
    def _process_chunk_with_api(self, system_prompt: str, user_content: str, chunk_display: str) -> tuple[List[Dict], bool]:
        """Process a single chunk with API call and return articles and success status"""
        # Estimate token usage
        estimated_tokens = self.estimate_request_tokens(system_prompt, user_content)
        print(f"       Estimated tokens: {estimated_tokens}")
        
        # Check rate limits before making request
        if not self.check_token_limits(estimated_tokens):
            print(f"       Rate limit protection triggered")
            self.wait_for_rate_limit_reset()
        
        try:
            # Use the dual API approach (Claude first, OpenAI fallback)
            api_success, content, actual_tokens = self.call_api_with_fallback(system_prompt, user_content)
            
            if api_success:
                # Track token usage
                self.update_token_usage(actual_tokens)
                
                # Parse JSON response
                try:
                    # Clean up any potential markdown formatting
                    clean_content = content.strip()
                    if clean_content.startswith('```json'):
                        clean_content = clean_content.replace('```json', '').replace('```', '').strip()
                    
                    articles_data = json.loads(clean_content)
                    
                    # Handle both direct list and wrapped object formats
                    if isinstance(articles_data, list):
                        articles = articles_data
                    else:
                        articles = articles_data.get("articles", [])
                    
                    if articles:
                        print(f"       SUCCESS: Extracted {len(articles)} articles")
                        return articles, True
                    else:
                        print(f"       No articles found in chunk")
                        return [], True
                        
                except json.JSONDecodeError as e:
                    print(f"       JSON parsing failed: {e}")
                    print(f"       Content preview: {content[:200]}...")
                    return [], False
            else:
                print(f"       BOTH APIs FAILED for chunk {chunk_display}")
                return [], False
                
        except Exception as e:
            print(f"       ERROR processing chunk {chunk_display}: {e}")
            return [], False
    
    def ensure_api_availability(self):
        """Ensure API availability has been tested"""
        if not self._apis_tested:
            self.openai_available, self.anthropic_available = self.test_api_connections()
            self._apis_tested = True
    
    def call_api_with_fallback(self, system_prompt: str, user_content: str) -> tuple[bool, str, int]:
        """Call API based on preferred model with fallback"""
        # Ensure API availability has been tested
        self.ensure_api_availability()
        
        # Use Claude Sonnet 4 first (default), then fall back to GPT-4o-mini
        if self.anthropic_available:
            try:
                import anthropic
                
                api_key = os.getenv("ANTHROPIC_API_KEY")
                client = anthropic.Anthropic(api_key=api_key)
                
                print(f"       Trying Claude Sonnet 4... (Preferred: {self.preferred_model})")
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",  # Latest Claude Sonnet 4
                    max_tokens=8000,  # Increased for large JSON responses
                    temperature=0.1,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_content}]
                )
                
                # Estimate tokens for Claude (rough approximation)
                estimated_tokens = (len(system_prompt) + len(user_content) + len(response.content[0].text)) // 4
                content = response.content[0].text.strip()
                print(f"       Claude SUCCESS: ~{estimated_tokens} tokens used (estimated)")
                return True, content, estimated_tokens
                
            except Exception as claude_error:
                print(f"       Claude FAILED: {type(claude_error).__name__}: {str(claude_error)}")
                if not self.openai_available:
                    raise claude_error
        
        # Fall back to GPT-4o-mini if Claude fails
        if self.openai_available:
            try:
                from openai import OpenAI
                client = OpenAI()
                
                print(f"       Falling back to GPT-4o-mini... (Preferred: {self.preferred_model})")
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=0.1,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    max_tokens=4000,
                    timeout=120
                )
                
                actual_tokens = response.usage.total_tokens
                content = response.choices[0].message.content.strip()
                print(f"       GPT-4o-mini SUCCESS: {actual_tokens} tokens used")
                return True, content, actual_tokens
                
            except Exception as openai_error:
                print(f"       GPT-4o-mini FAILED: {type(openai_error).__name__}: {str(openai_error)}")
                raise openai_error
        
        # If we get here, no APIs worked
        raise Exception("Both Claude and OpenAI APIs failed")
    
    def load_or_create_registry(self, registry_file: str, price_lists: List[Path]) -> Dict[str, Any]:
        """Load existing registry or create new one for crash-safe processing"""
        if os.path.exists(registry_file):
            try:
                with open(registry_file, 'r', encoding='utf-8') as f:
                    existing_registry = json.load(f)
                
                articles_count = len(existing_registry.get("articles", {}))
                print(f" RESUMING: Loaded existing registry with {articles_count} articles")
                
                # Ensure all metadata fields exist
                if "metadata" not in existing_registry:
                    existing_registry["metadata"] = {}
                if "processing_progress" not in existing_registry["metadata"]:
                    existing_registry["metadata"]["processing_progress"] = {}
                if "brands_processed" not in existing_registry["metadata"]:
                    existing_registry["metadata"]["brands_processed"] = []
                if "years_processed" not in existing_registry["metadata"]:
                    existing_registry["metadata"]["years_processed"] = []
                
                return existing_registry
                
            except Exception as e:
                print(f" Warning: Could not load existing registry: {e}")
                print(" Starting fresh registry...")
        
        # Create new registry
        print(" Creating new registry...")
        return {
            "metadata": {
                "build_timestamp": datetime.now().isoformat(),
                "total_pdfs_processed": len(price_lists),
                "total_articles": 0,
                "extraction_api": "gpt-4o-mini_fallback",
                "field_mapping": {
                    "Tuotenro": "article_code",
                    "Malli": "model",
                    "Paketti": "package", 
                    "Moottori": "engine",
                    "Telamatto": "track",
                    "Käynnistin": "starter",
                    "Kevätoptiot": "spring_options",
                    "Mittaristo": "gauge",
                    "Väri": "color",
                    "Suositushinta": "price_fi"
                },
                "brands_processed": [],
                "years_processed": [],
                "processing_progress": {}
            },
            "articles": {},
            "lookup_indexes": {
                "by_brand": {},
                "by_year": {},
                "by_model": {},
                "by_model_line": {},
                "by_engine": {}
            }
        }
    
    def is_page_processed(self, registry: Dict[str, Any], pdf_name: str, page_num: int) -> bool:
        """Check if a specific PDF page has already been processed"""
        progress = registry["metadata"]["processing_progress"]
        if pdf_name in progress:
            completed_pages = progress[pdf_name].get("completed_pages", [])
            return page_num in completed_pages
        return False
    
    def mark_page_completed(self, registry: Dict[str, Any], pdf_name: str, page_num: int, 
                          total_pages: int, articles_extracted: int) -> Dict[str, int]:
        """Mark a page as completed and save progress, returns detailed statistics"""
        progress = registry["metadata"]["processing_progress"]
        
        if pdf_name not in progress:
            progress[pdf_name] = {
                "total_pages": total_pages,
                "completed_pages": [],
                "articles_extracted": 0,
                "status": "in_progress"
            }
        
        # Add page to completed list
        if page_num not in progress[pdf_name]["completed_pages"]:
            progress[pdf_name]["completed_pages"].append(page_num)
            progress[pdf_name]["completed_pages"].sort()
        
        # Update article count
        progress[pdf_name]["articles_extracted"] += articles_extracted
        
        # Mark PDF as completed if all pages done
        if len(progress[pdf_name]["completed_pages"]) == total_pages:
            progress[pdf_name]["status"] = "completed"
            print(f"       PDF COMPLETED: {pdf_name}")
        
        # Save progress immediately (crash-safe)
        page_stats = self.save_registry_progress(registry)
        return page_stats
    
    def save_registry_progress(self, registry: Dict[str, Any]) -> Dict[str, int]:
        """Save registry progress to both JSON and SQLite (crash-safe), returns detailed statistics"""
        # MERGE FIX: Load existing registry and merge instead of overwriting
        registry_file = "master_article_registry.json"
        merged_registry = registry.copy()  # Start with current registry
        
        if os.path.exists(registry_file):
            try:
                with open(registry_file, 'r', encoding='utf-8') as f:
                    existing_registry = json.load(f)
                
                # Merge existing articles that aren't in current registry
                existing_articles = existing_registry.get("articles", {})
                current_articles = merged_registry.get("articles", {})
                
                # Add existing articles that aren't being updated
                for article_code, article_data in existing_articles.items():
                    if article_code not in current_articles:
                        merged_registry["articles"][article_code] = article_data
                
                # Merge lookup indexes
                existing_indexes = existing_registry.get("lookup_indexes", {})
                current_indexes = merged_registry.get("lookup_indexes", {})
                for index_type, index_data in existing_indexes.items():
                    if index_type not in current_indexes:
                        merged_registry["lookup_indexes"][index_type] = index_data
                    else:
                        # Merge index data
                        for key, values in index_data.items():
                            if key not in current_indexes[index_type]:
                                current_indexes[index_type][key] = values
                            else:
                                # Merge lists and remove duplicates
                                current_indexes[index_type][key] = list(set(current_indexes[index_type][key] + values))
                
                print(f"    Merged with existing registry: {len(existing_articles)} existing + {len(current_articles)} new = {len(merged_registry['articles'])} total")
                
            except Exception as e:
                print(f"    Warning: Could not load existing registry for merge: {e}")
                print("    Saving current registry only...")
        
        merged_registry["metadata"]["total_articles"] = len(merged_registry["articles"])
        merged_registry["metadata"]["last_update"] = datetime.now().isoformat()
        
        # Save merged registry to JSON
        with open(registry_file, 'w', encoding='utf-8') as f:
            json.dump(merged_registry, f, indent=2, ensure_ascii=False)
        
        # Save to SQLite database if enabled
        stats = {
            'total_articles': len(registry["articles"]),
            'new_articles': 0,
            'updated_articles': 0,
            'failed_articles': 0,
            'sqlite_enabled': self.use_sqlite
        }
        
        if self.use_sqlite and self.db:
            for article_code, article_data in registry["articles"].items():
                try:
                    # Normalize article code
                    normalized_code = normalize_article_code(article_code)
                    
                    # Check if article already exists
                    existing_article = self.db.get_article(normalized_code)
                    is_new_article = existing_article is None
                    
                    # Prepare article data for SQLite
                    sqlite_data = {
                        'article_code': normalized_code,
                        'brand': article_data.get('brand', ''),
                        'year': int(article_data.get('year', 2024)) if article_data.get('year') else 2024,
                        'model': article_data.get('model', ''),
                        'package': article_data.get('package', ''),
                        'engine': article_data.get('engine', ''),
                        'track': article_data.get('track', ''),
                        'starter': article_data.get('starter', ''),
                        'gauge': article_data.get('gauge', ''),
                        'spring_options': article_data.get('spring_options', ''),
                        'color': article_data.get('color', ''),
                        'price_fi': article_data.get('price_fi', ''),
                        'source_pdf': article_data.get('source_pdf', ''),
                        'model_line': article_data.get('model_line', ''),
                        '_extraction_metadata': article_data.get('_extraction_metadata', {})
                    }
                    
                    # Insert into database (will replace if exists)
                    try:
                        self.db.insert_article(sqlite_data)
                        
                        # Track statistics
                        if is_new_article:
                            stats['new_articles'] += 1
                        else:
                            stats['updated_articles'] += 1
                        
                        # Update processing status only if article insertion succeeded
                        self.db.update_processing_status(normalized_code, phase=1, status='completed')
                        
                    except Exception as insert_error:
                        stats['failed_articles'] += 1
                        error_msg = str(insert_error)
                        if "UNIQUE constraint" in error_msg:
                            print(f"    Article {article_code} already exists - this should not happen with INSERT OR REPLACE")
                        elif "FOREIGN KEY constraint" in error_msg:
                            print(f"    Foreign key error for {article_code}: {insert_error}")
                        else:
                            print(f"    Failed to save article {article_code} to SQLite: {insert_error}")
                        
                        # Try to update processing status to failed if possible
                        try:
                            self.db.update_processing_status(normalized_code, phase=1, status='failed', 
                                                           error_data={'error': str(insert_error)})
                        except Exception:
                            pass  # Ignore if we can't update status either
                    
                except Exception as e:
                    print(f"    General error processing {article_code}: {e}")
            
            # Display detailed statistics
            print(f"    SQLite Statistics:")
            print(f"      • Total articles: {stats['total_articles']}")
            print(f"      • New articles: {stats['new_articles']}")
            print(f"      • Updated articles: {stats['updated_articles']}")
            if stats['failed_articles'] > 0:
                print(f"      • Failed articles: {stats['failed_articles']}")
            
            return stats
        else:
            return stats
    
    def extract_pdf_with_claude_native(self, pdf_path: Path, brand: str, year: str, 
                                     registry: Dict[str, Any]) -> Dict[str, int]:
        """Extract articles from PDF using Claude native PDF processing"""
        # Initialize statistics
        total_stats = {
            'total_articles': 0,
            'new_articles': 0,
            'updated_articles': 0,
            'failed_articles': 0,
            'sqlite_enabled': False
        }
        
        try:
            pdf_name = pdf_path.name
            print(f"    Processing {pdf_name} ({brand} {year}) with Claude native PDF processing")
            
            # Check if already processed
            progress = registry["metadata"]["processing_progress"].get(pdf_name, {})
            if progress.get("status") == "completed":
                print(f"    SKIPPING: {pdf_name} already fully processed")
                return total_stats
            
            # Convert PDF to base64 for Claude
            import base64
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
                pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            
            print(f"    PDF encoded: {len(pdf_base64)} base64 characters")
            
            # Create system prompt for Claude native processing
            system_prompt = self.create_finnish_extraction_prompt(brand, year)
            
            # Create user content for Claude
            user_content = f"""Please analyze this entire {brand} {year} PRICE_LIST PDF and extract ALL article information.

This PDF contains multiple pages of article data. Extract every single article from all pages in the PDF.

BRAND: {brand}
YEAR: {year}
PDF: {pdf_name}

Please process the entire PDF and return a complete JSON array with ALL articles found across ALL pages."""
            
            # Call Claude with PDF
            try:
                import anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                client = anthropic.Anthropic(api_key=api_key)
                
                print(f"    Sending entire PDF to Claude...")
                
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=8000,
                    temperature=0.1,
                    system=system_prompt,
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "text", 
                                "text": user_content
                            },
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": pdf_base64
                                }
                            }
                        ]
                    }]
                )
                
                content = response.content[0].text.strip()
                print(f"    Claude processed PDF successfully")
                
                # Parse JSON response
                try:
                    # Clean up any potential markdown formatting
                    clean_content = content.strip()
                    if clean_content.startswith('```json'):
                        clean_content = clean_content.replace('```json', '').replace('```', '').strip()
                    
                    articles_data = json.loads(clean_content)
                    
                    # Handle both direct list and wrapped object formats
                    if isinstance(articles_data, list):
                        articles = articles_data
                    else:
                        articles = articles_data.get("articles", [])
                    
                    print(f"    SUCCESS: Extracted {len(articles)} articles from entire PDF")
                    
                    # Process articles with metadata
                    if articles:
                        for article in articles:
                            # Synthesize model_line from model + package
                            model = article.get("model", "")
                            package = article.get("package", "")
                            
                            if model and package:
                                article["model_line"] = f"{model} {package}"
                            elif model:
                                article["model_line"] = model
                            else:
                                article["model_line"] = ""
                            
                            article["_extraction_metadata"] = {
                                "source_pdf": pdf_name,
                                "extracted_timestamp": datetime.now().isoformat(),
                                "extraction_method": "claude_native_pdf"
                            }
                        
                        # Add articles to registry
                        for article in articles:
                            article_code = article.get("article_code", "")
                            if article_code:
                                # Store in main articles dict (duplicates automatically replaced)
                                registry["articles"][article_code] = article
                                
                                # Build lookup indexes
                                self.add_to_index(registry["lookup_indexes"]["by_brand"], 
                                               brand, article_code)
                                self.add_to_index(registry["lookup_indexes"]["by_year"], 
                                               year, article_code)
                                
                                model = article.get("model", "")
                                if model:
                                    self.add_to_index(registry["lookup_indexes"]["by_model"], 
                                                   model, article_code)
                                
                                model_line = article.get("model_line", "")
                                if model_line:
                                    self.add_to_index(registry["lookup_indexes"]["by_model_line"], 
                                                   model_line, article_code)
                                
                                engine = article.get("engine", "")
                                if engine:
                                    self.add_to_index(registry["lookup_indexes"]["by_engine"], 
                                                   engine, article_code)
                        
                        # Mark as completed (entire PDF processed at once)
                        doc = fitz.open(pdf_path)
                        total_pages = len(doc)
                        doc.close()
                        
                        progress = {
                            "total_pages": total_pages,
                            "completed_pages": list(range(total_pages)),
                            "articles_extracted": len(articles),
                            "status": "completed"
                        }
                        registry["metadata"]["processing_progress"][pdf_name] = progress
                        
                        # Save progress and get statistics
                        page_stats = self.save_registry_progress(registry)
                        
                        total_stats['total_articles'] = len(articles)
                        total_stats['new_articles'] = page_stats.get('new_articles', 0)
                        total_stats['updated_articles'] = page_stats.get('updated_articles', 0)
                        total_stats['failed_articles'] = page_stats.get('failed_articles', 0)
                        total_stats['sqlite_enabled'] = page_stats.get('sqlite_enabled', False)
                        
                        print(f"    COMPLETED {pdf_name}: {len(articles)} articles extracted with Claude native processing")
                        return total_stats
                    
                except json.JSONDecodeError as e:
                    print(f"    JSON parsing failed: {e}")
                    print(f"    Content preview: {content[:200]}...")
                    return total_stats
                    
            except Exception as e:
                print(f"    Claude native processing failed: {e}")
                # Return failure stats with sqlite_enabled flag
                total_stats['sqlite_enabled'] = self.use_sqlite
                return total_stats
            
        except Exception as e:
            print(f"    ERROR processing {pdf_path.name}: {e}")
            # Return failure stats with sqlite_enabled flag
            total_stats['sqlite_enabled'] = self.use_sqlite
            return total_stats

    def extract_pdf_with_crash_safety(self, pdf_path: Path, brand: str, year: str, 
                                    registry: Dict[str, Any]) -> Dict[str, int]:
        """Extract articles from PDF with page-level crash safety, returns detailed statistics"""
        # Initialize cumulative statistics
        total_stats = {
            'total_articles': 0,
            'new_articles': 0,
            'updated_articles': 0,
            'failed_articles': 0,
            'sqlite_enabled': False
        }
        try:
            pdf_name = pdf_path.name
            print(f"    Processing {pdf_name} ({brand} {year})")
            
            # Get total pages
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            doc.close()
            
            print(f"    {total_pages} pages total")
            
            # Check existing progress
            progress = registry["metadata"]["processing_progress"].get(pdf_name, {})
            completed_pages = progress.get("completed_pages", [])
            
            if completed_pages:
                print(f"    RESUMING: Pages {completed_pages} already completed")
            
            system_prompt = self.create_finnish_extraction_prompt(brand, year)
            total_articles_extracted = 0
            
            # Process each page individually (crash-safe)
            for page_num in range(total_pages):
                page_display = page_num + 1
                
                # Skip if page already processed
                if self.is_page_processed(registry, pdf_name, page_num):
                    print(f"    SKIPPING page {page_display} - already completed")
                    continue
                
                print(f"    Processing page {page_display}/{total_pages}...")
                
                # Extract text from this page
                page_text = self.extract_pdf_text(str(pdf_path), page_num)
                
                if not page_text.strip():
                    print(f"       Empty page text, skipping this page")
                    continue
                
                print(f"Extracted {len(page_text)} characters from page {page_display}")
                
                # Split large pages into chunks
                page_articles = []
                success = False
                
                if len(page_text) > self.max_page_chars:
                    print(f"       Large page detected ({len(page_text)} chars), splitting into chunks...")
                    chunks = self.split_large_page(page_text)
                    print(f"       Split into {len(chunks)} chunks")
                    
                    # Process each chunk
                    for chunk_idx, chunk_text in enumerate(chunks):
                        chunk_display = f"{page_display}.{chunk_idx + 1}"
                        print(f"       Processing chunk {chunk_idx + 1}/{len(chunks)} ({len(chunk_text)} chars)...")
                        
                        # Prepare user content for this chunk
                        user_content = f"""BRAND: {brand}
YEAR: {year}
PAGE: {page_display}
CHUNK: {chunk_idx + 1}/{len(chunks)}

PDF PAGE TEXT:
{chunk_text}

Extract ALL article information from this page chunk following the Finnish field mapping. Return pure JSON only."""
                        
                        # Process chunk with API call
                        chunk_articles, chunk_success = self._process_chunk_with_api(system_prompt, user_content, chunk_display)
                        if chunk_success:
                            page_articles.extend(chunk_articles)
                            success = True
                else:
                    # Process as single chunk
                    print(f"       Processing single chunk ({len(page_text)} chars)...")
                    user_content = f"""BRAND: {brand}
YEAR: {year}
PAGE: {page_display}

PDF PAGE TEXT:
{page_text}

Extract ALL article information from this page following the Finnish field mapping. Return pure JSON only."""
                    
                    # Process with API call
                    page_articles, success = self._process_chunk_with_api(system_prompt, user_content, str(page_display))
                
                # Now process the articles with metadata
                if success and page_articles:
                    # Add extraction metadata and synthesize model_line for all articles
                    for article in page_articles:
                        # Synthesize model_line from model + package
                        model = article.get("model", "")
                        package = article.get("package", "")
                        
                        if model and package:
                            article["model_line"] = f"{model} {package}"
                        elif model:
                            article["model_line"] = model
                        else:
                            article["model_line"] = ""
                        
                        article["_extraction_metadata"] = {
                            "source_pdf": pdf_name,
                            "source_page": page_display,
                            "extracted_timestamp": datetime.now().isoformat(),
                            "extraction_method": "chunked" if len(page_text) > self.max_page_chars else "single"
                        }
                
                # Add extracted articles to registry
                page_article_count = 0
                if success and page_articles:
                    for article in page_articles:
                        article_code = article.get("article_code", "")
                        if article_code:
                            # Store in main articles dict (duplicates automatically replaced)
                            registry["articles"][article_code] = article
                            
                            # Build lookup indexes
                            self.add_to_index(registry["lookup_indexes"]["by_brand"], 
                                           brand, article_code)
                            self.add_to_index(registry["lookup_indexes"]["by_year"], 
                                           year, article_code)
                            
                            model = article.get("model", "")
                            if model:
                                self.add_to_index(registry["lookup_indexes"]["by_model"], 
                                               model, article_code)
                            
                            model_line = article.get("model_line", "")
                            if model_line:
                                self.add_to_index(registry["lookup_indexes"]["by_model_line"], 
                                               model_line, article_code)
                            
                            engine = article.get("engine", "")
                            if engine:
                                self.add_to_index(registry["lookup_indexes"]["by_engine"], 
                                               engine, article_code)
                            
                            page_article_count += 1
                
                # Only mark page as completed if API call was successful (even with 0 articles)
                if success:
                    page_stats = self.mark_page_completed(registry, pdf_name, page_num, total_pages, page_article_count)
                    
                    # Accumulate statistics
                    total_stats['new_articles'] += page_stats.get('new_articles', 0)
                    total_stats['updated_articles'] += page_stats.get('updated_articles', 0)
                    total_stats['failed_articles'] += page_stats.get('failed_articles', 0)
                    total_stats['sqlite_enabled'] = page_stats.get('sqlite_enabled', False)
                    
                    total_articles_extracted += page_article_count
                    print(f"       PAGE COMPLETED: {page_article_count} articles extracted")
                else:
                    print(f"       PAGE FAILED: Will retry this page on next run")
            
            # Update final statistics
            total_stats['total_articles'] = total_articles_extracted
            
            print(f"    COMPLETED {pdf_name}: {total_articles_extracted} articles extracted")
            return total_stats
            
        except Exception as e:
            print(f"    ERROR processing {pdf_path.name}: {e}")
            return total_stats
    
    def extract_all_articles_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Extract all articles from a PDF file"""
        # Ensure API availability has been tested
        self.ensure_api_availability()
        
        articles = []
        total_sqlite_saved = 0
        extraction_stats = {
            'total_articles': 0,
            'new_articles': 0,
            'updated_articles': 0,
            'failed_articles': 0,
            'sqlite_enabled': self.use_sqlite
        }
        
        try:
            # Load existing registry or create new one (FIX: merge instead of overwrite)
            registry_file = "master_article_registry.json"
            if os.path.exists(registry_file):
                try:
                    with open(registry_file, 'r', encoding='utf-8') as f:
                        temp_registry = json.load(f)
                    print(f"    Loaded existing registry with {len(temp_registry.get('articles', {}))} articles")
                except Exception as e:
                    print(f"    Warning: Could not load existing registry: {e}")
                    print("    Starting fresh registry...")
                    temp_registry = {
                        "articles": {},
                        "lookup_indexes": {
                            "by_brand": {},
                            "by_year": {},
                            "by_model": {},
                            "by_model_line": {},
                            "by_engine": {}
                        },
                        "metadata": {
                            "processing_progress": {}
                        }
                    }
            else:
                print("    No existing registry found, creating new one...")
                temp_registry = {
                    "articles": {},
                    "lookup_indexes": {
                        "by_brand": {},
                        "by_year": {},
                        "by_model": {},
                        "by_model_line": {},
                        "by_engine": {}
                    },
                    "metadata": {
                        "processing_progress": {}
                    }
                }
            
            # Ensure metadata structure exists
            if "metadata" not in temp_registry:
                temp_registry["metadata"] = {}
            if "processing_progress" not in temp_registry["metadata"]:
                temp_registry["metadata"]["processing_progress"] = {}
            
            # Determine brand and year from filename
            filename = os.path.basename(pdf_path)
            brand = "UNKNOWN"
            year = "2024"
            
            # Try to parse brand and year from filename
            if "LYNX" in filename.upper():
                brand = "LYNX"
            elif "SKIDOO" in filename.upper() or "SKI-DOO" in filename.upper():
                brand = "SKIDOO"
            
            # Extract year
            import re
            year_match = re.search(r'20\d{2}', filename)
            if year_match:
                year = year_match.group()
            
            # Try Claude native PDF processing first
            extraction_stats = self.extract_pdf_with_claude_native(Path(pdf_path), brand, year, temp_registry)
            
            # If Claude native failed (0 articles), fall back to page-by-page
            if extraction_stats['total_articles'] == 0:
                print(f"    Falling back to page-by-page extraction...")
                extraction_stats = self.extract_pdf_with_crash_safety(Path(pdf_path), brand, year, temp_registry)
            
            # Convert articles dict to list
            for article_code, article_data in temp_registry["articles"].items():
                article_data["article_code"] = article_code
                article_data["brand"] = brand
                article_data["year"] = year
                articles.append(article_data)
            
        except Exception as e:
            print(f"Error extracting articles from {pdf_path}: {e}")
        
        return {
            'articles': articles,
            'total_extracted': len(articles),
            'sqlite_stats': extraction_stats,
            'use_sqlite': self.use_sqlite
        }
    
    def build_optimized_master_registry(self) -> Dict[str, Any]:
        """Build master registry using token-optimized extraction"""
        print("=" * 80)
        print(" BUILDING OPTIMIZED MASTER ARTICLE REGISTRY")
        print("=" * 80)
        
        # Check API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print(" ERROR: OPENAI_API_KEY not set")
            return None
        
        print(f" OpenAI API key found ({len(api_key)} chars)")
        
        # Test both API connections
        self.openai_available, self.anthropic_available = self.test_api_connections()
        if not self.openai_available and not self.anthropic_available:
            print(" ERROR: No working APIs available")
            return None
        
        # Find PRICE_LIST PDFs
        price_lists = list(self.pdf_dir.glob("*PRICE_LIST*.pdf"))
        
        print(f" Found {len(price_lists)} PRICE_LIST PDFs:")
        for pdf in price_lists:
            print(f"   - {pdf.name}")
        
        if not price_lists:
            print(" ERROR: No PRICE_LIST PDFs found")
            return None
        
        # Load existing registry or create new one (crash-safe resume)
        registry_file = "master_article_registry.json"
        master_registry = self.load_or_create_registry(registry_file, price_lists)
        
        # Process each PDF with crash-safe page-level processing
        for i, pdf_path in enumerate(price_lists):
            print(f"\n[{i+1}/{len(price_lists)}] Processing: {pdf_path.name}")
            
            try:
                # Parse brand and year
                brand, year = self.parse_filename(pdf_path.name)
                print(f"    Brand: {brand}, Year: {year}")
                
                # Track processed brands/years
                if brand not in master_registry["metadata"]["brands_processed"]:
                    master_registry["metadata"]["brands_processed"].append(brand)
                if year not in master_registry["metadata"]["years_processed"]:
                    master_registry["metadata"]["years_processed"].append(year)
                
                # Try Claude native PDF processing first, fallback to page-by-page
                stats = self.extract_pdf_with_claude_native(pdf_path, brand, year, master_registry)
                
                # If Claude native failed (0 articles), fall back to page-by-page
                if stats['total_articles'] == 0:
                    print(f"    Falling back to page-by-page extraction...")
                    stats = self.extract_pdf_with_crash_safety(pdf_path, brand, year, master_registry)
            
            except Exception as e:
                print(f"    ERROR processing {pdf_path.name}: {e}")
                continue
        
        # Finalize registry
        master_registry["metadata"]["total_articles"] = len(master_registry["articles"])
        
        # Save master registry to JSON (legacy format)
        output_file = "master_article_registry.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(master_registry, f, indent=2, ensure_ascii=False)
        
        # Final save to SQLite database
        if self.use_sqlite and self.db:
            print("\n Final SQLite database sync...")
            self.save_registry_progress(master_registry)
        
        # Print final summary
        print("\n" + "=" * 80)
        print(" OPTIMIZED MASTER REGISTRY BUILT SUCCESSFULLY!")
        print("=" * 80)
        print(f" Final Statistics:")
        print(f"   Total articles: {master_registry['metadata']['total_articles']}")
        print(f"   Brands: {', '.join(master_registry['metadata']['brands_processed'])}")
        print(f"   Years: {', '.join(master_registry['metadata']['years_processed'])}")
        print(f"   Models: {len(master_registry['lookup_indexes']['by_model'])}")
        print(f"   Engines: {len(master_registry['lookup_indexes']['by_engine'])}")
        print(f"   Saved to: {output_file}")
        
        # Token usage summary
        total_tokens = self.token_usage_tracker['total_tokens']
        print(f"    Total tokens used: {total_tokens:,}")
        print(f"    Average tokens/PDF: {total_tokens // len(price_lists):,}")
        
        # Show sample articles
        if master_registry["articles"]:
            print(f"\n Sample articles extracted:")
            for i, (code, article) in enumerate(list(master_registry["articles"].items())[:5]):
                print(f"   {i+1}. {code}: {article.get('model', 'N/A')} - {article.get('engine', 'N/A')}")
        
        print("=" * 80)
        return master_registry
    
    def add_to_index(self, index_dict: Dict, key: str, article_code: str):
        """Helper to add article_code to lookup index"""
        if key not in index_dict:
            index_dict[key] = []
        if article_code not in index_dict[key]:
            index_dict[key].append(article_code)

if __name__ == "__main__":
    extractor = OptimizedPriceListExtractor()
    registry = extractor.build_optimized_master_registry()
    
    if registry:
        print(f"\n SUCCESS: Master article registry ready with {registry['metadata']['total_articles']} real articles!")
        print(" Ready for Phase 2: Image processing lookup")
        print(" Ready for GUI: Article registry browsing")
    else:
        print("\n FAILED: Master registry not built")