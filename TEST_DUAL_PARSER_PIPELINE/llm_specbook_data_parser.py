#!/usr/bin/env python3
"""
LLM Specbook Data Parser - Claude API Integration for Spec Book Extraction
Uses proven page-by-page processing strategy from global_parser.py with Claude native PDF processing
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import tiktoken

# Import our LLM JSON Parser
from llm_json_parser import LLMJsonParser

# Claude API
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("WARNING: anthropic package not installed. Run: pip install anthropic")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMSpecbookParser:
    """
    Claude-powered spec book extraction using page-by-page processing
    Adapted from proven global_parser.py strategy with Claude native PDF support
    """
    
    def __init__(self, db_path: str = "dual_db.db"):
        """
        Initialize LLM Specbook Parser
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        
        # Initialize LLM JSON Parser for response handling
        self.json_parser = LLMJsonParser(db_path)
        
        # Claude API configuration
        self.anthropic_client = None
        self.claude_model = "claude-3-5-sonnet-20241022"  # Latest Claude 3.5 Sonnet
        
        # Token management (adapted from global_parser.py)
        self.tokens_per_minute_limit = 40000  # Claude API limit
        self.safety_buffer = 0.8  # 80% safety buffer
        self.effective_tpm_limit = int(self.tokens_per_minute_limit * self.safety_buffer)
        
        # Token counter (using GPT tokenizer as approximation)
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        except:
            self.tokenizer = None
        
        self.token_usage_tracker = {
            'total_tokens': 0,
            'minute_tokens': 0,
            'minute_start': time.time(),
            'batch_tokens': 0
        }
        
        # Spec book page configuration
        self.spec_page_ranges = {
            'SKIDOO': (8, 30),  # Pages 8-30 contain model specifications
            'LYNX': (8, 35)     # Pages 8-35 contain model specifications
        }
        
        # LLM prompt (will be loaded from file)
        self.llm_prompt = None
        
        # Initialize Claude API client
        self._initialize_claude_client()
        
        # Load LLM prompt from file
        self.load_llm_prompt_from_file()
        
        logger.info(f"LLMSpecbookParser initialized with {self.effective_tpm_limit} effective tokens/min limit")
    
    def _initialize_claude_client(self):
        """Initialize Claude API client"""
        if not ANTHROPIC_AVAILABLE:
            logger.error("Anthropic package not available. Please install: pip install anthropic")
            return
        
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            logger.error("ANTHROPIC_API_KEY environment variable not found")
            return
        
        try:
            self.anthropic_client = anthropic.Anthropic(api_key=api_key)
            logger.info("Claude API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Claude client: {e}")
    
    def load_llm_prompt_from_file(self) -> str:
        """
        Load the LLM prompt from LLM_promt_spec_books.md file
        
        Returns:
            str: The loaded prompt
        """
        prompt_file = Path("docs/LLM_promt_spec_books.md")
        
        if not prompt_file.exists():
            logger.error(f"LLM prompt file not found: {prompt_file}")
            return ""
        
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract the main extraction prompt (between the first set of ````  markers)
            prompt_start = content.find('````')
            if prompt_start == -1:
                logger.error("Could not find prompt start marker (````) in LLM_promt_spec_books.md")
                return ""
            
            prompt_end = content.find('````', prompt_start + 4)
            if prompt_end == -1:
                logger.error("Could not find prompt end marker (````) in LLM_promt_spec_books.md")
                return ""
            
            self.llm_prompt = content[prompt_start + 4:prompt_end].strip()
            logger.info(f"Loaded LLM prompt from {prompt_file} ({len(self.llm_prompt)} characters)")
            return self.llm_prompt
            
        except Exception as e:
            logger.error(f"Error loading LLM prompt: {e}")
            return ""
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using GPT-4 tokenizer (approximation for Claude)
        Adapted from global_parser.py
        """
        if not self.tokenizer:
            # Fallback estimation: ~4 characters per token
            return len(text) // 4
        
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.debug(f"Token counting error: {e}")
            return len(text) // 4
    
    def estimate_request_tokens(self, system_prompt: str, user_content: str, estimated_response: int = 2000) -> int:
        """
        Estimate total tokens for a Claude request
        Adapted from global_parser.py with higher response estimate for JSON
        """
        input_tokens = self.count_tokens(system_prompt) + self.count_tokens(user_content)
        return input_tokens + estimated_response
    
    def check_token_limits(self, estimated_tokens: int) -> bool:
        """
        Check if we can make request within rate limits
        Adapted from global_parser.py
        """
        current_time = time.time()
        
        # Reset minute counter if a minute has passed
        if current_time - self.token_usage_tracker['minute_start'] >= 60:
            self.token_usage_tracker['minute_tokens'] = 0
            self.token_usage_tracker['minute_start'] = current_time
            logger.debug("Token minute counter reset")
        
        # Check if adding estimated tokens would exceed limit
        projected_minute_tokens = self.token_usage_tracker['minute_tokens'] + estimated_tokens
        
        if projected_minute_tokens > self.effective_tpm_limit:
            remaining_tokens = self.effective_tpm_limit - self.token_usage_tracker['minute_tokens']
            logger.warning(f"Token limit check: {estimated_tokens} needed, {remaining_tokens} available this minute")
            return False
        
        return True
    
    def update_token_usage(self, actual_tokens: int):
        """
        Update token usage tracking
        Adapted from global_parser.py
        """
        self.token_usage_tracker['total_tokens'] += actual_tokens
        self.token_usage_tracker['minute_tokens'] += actual_tokens
        self.token_usage_tracker['batch_tokens'] += actual_tokens
        
        logger.debug(f"Token usage updated: +{actual_tokens} "
                    f"(minute: {self.token_usage_tracker['minute_tokens']}/{self.effective_tpm_limit}, "
                    f"total: {self.token_usage_tracker['total_tokens']})")
    
    def wait_for_rate_limit_reset(self):
        """
        Wait for rate limit to reset if needed
        Adapted from global_parser.py
        """
        current_time = time.time()
        time_since_minute_start = current_time - self.token_usage_tracker['minute_start']
        
        if time_since_minute_start < 60:
            wait_time = 60 - time_since_minute_start
            logger.info(f"Rate limit protection: waiting {wait_time:.1f}s for minute reset...")
            time.sleep(wait_time)
            
            # Reset counters after wait
            self.token_usage_tracker['minute_tokens'] = 0
            self.token_usage_tracker['minute_start'] = time.time()
    
    def extract_page_with_claude(self, pdf_path: str, page_number: int) -> Optional[Dict[str, Any]]:
        """
        Extract specifications from a single PDF page using Claude native PDF processing
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number to extract (1-indexed)
            
        Returns:
            dict: Parsed JSON response from Claude, or None if failed
        """
        if not self.anthropic_client:
            logger.error("Claude API client not initialized")
            return None
        
        if not self.llm_prompt:
            logger.error("LLM prompt not loaded")
            return None
        
        try:
            # Read PDF file
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
            
            # Prepare user message with PDF and page specification
            user_content = f"""Please extract snowmobile specifications from page {page_number} of this PDF document.
            
Focus specifically on page {page_number} which should contain model specifications.

{self.llm_prompt}"""
            
            # Estimate token usage (rough approximation)
            estimated_tokens = self.estimate_request_tokens(
                system_prompt="You are an expert snowmobile specification extraction AI.",
                user_content=user_content,
                estimated_response=2000
            )
            
            logger.info(f"Processing page {page_number} (estimated {estimated_tokens} tokens)")
            
            # Check rate limits
            if not self.check_token_limits(estimated_tokens):
                logger.info("Rate limit protection triggered")
                self.wait_for_rate_limit_reset()
            
            # Make Claude API call with PDF
            response = self.anthropic_client.messages.create(
                model=self.claude_model,
                max_tokens=4000,
                temperature=0.1,
                system="You are an expert snowmobile specification extraction AI with deep technical knowledge of powersports vehicles.",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": pdf_data
                                }
                            },
                            {
                                "type": "text",
                                "text": user_content
                            }
                        ]
                    }
                ]
            )
            
            # Update token usage (Claude returns actual usage)
            actual_tokens = response.usage.input_tokens + response.usage.output_tokens
            self.update_token_usage(actual_tokens)
            
            # Extract JSON response
            response_text = response.content[0].text.strip()
            
            # Try to parse JSON
            try:
                json_response = json.loads(response_text)
                logger.info(f"Successfully extracted JSON from page {page_number}")
                return json_response
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response from page {page_number}: {e}")
                logger.debug(f"Response text: {response_text[:500]}...")
                return None
        
        except Exception as e:
            logger.error(f"Error processing page {page_number}: {e}")
            return None
    
    def process_pdf_pages(self, pdf_path: str, brand: str, page_range: Tuple[int, int] = None) -> List[Dict[str, Any]]:
        """
        Process multiple pages from a PDF
        
        Args:
            pdf_path: Path to PDF file
            brand: Brand name (SKIDOO, LYNX)
            page_range: Optional tuple of (start_page, end_page). If None, uses brand default.
            
        Returns:
            list: List of successfully extracted JSON responses
        """
        if page_range is None:
            page_range = self.spec_page_ranges.get(brand.upper(), (8, 30))
        
        start_page, end_page = page_range
        logger.info(f"Processing {brand} PDF pages {start_page}-{end_page}: {pdf_path}")
        
        extracted_data = []
        
        for page_num in range(start_page, end_page + 1):
            logger.info(f"Processing page {page_num}...")
            
            json_response = self.extract_page_with_claude(pdf_path, page_num)
            
            if json_response:
                # Try to store in database using LLMJsonParser
                success = self.json_parser.insert_llm_response(json_response)
                
                if success:
                    extracted_data.append(json_response)
                    logger.info(f"✅ Page {page_num} processed and stored successfully")
                else:
                    logger.warning(f"⚠️ Page {page_num} extracted but failed to store in database")
            else:
                logger.warning(f"⚠️ Page {page_num} extraction failed")
        
        logger.info(f"Completed processing: {len(extracted_data)} pages successfully processed")
        return extracted_data
    
    def extract_specbook_data(self, pdf_path: str, brand: str = None) -> Dict[str, Any]:
        """
        Extract all specification data from a spec book PDF
        
        Args:
            pdf_path: Path to spec book PDF
            brand: Brand name (SKIDOO, LYNX). If None, will try to detect from filename.
            
        Returns:
            dict: Summary of extraction results
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return {'success': False, 'error': 'PDF file not found'}
        
        # Auto-detect brand from filename if not provided
        if not brand:
            filename = pdf_path.name.upper()
            if 'SKIDOO' in filename:
                brand = 'SKIDOO'
            elif 'LYNX' in filename:
                brand = 'LYNX'
            else:
                logger.error(f"Could not detect brand from filename: {pdf_path.name}")
                return {'success': False, 'error': 'Could not detect brand from filename'}
        
        logger.info(f"Starting {brand} spec book extraction: {pdf_path.name}")
        
        # Process all pages
        start_time = time.time()
        extracted_data = self.process_pdf_pages(str(pdf_path), brand)
        end_time = time.time()
        
        # Return summary
        result = {
            'success': True,
            'brand': brand,
            'pdf_file': pdf_path.name,
            'pages_processed': len(extracted_data),
            'processing_time': round(end_time - start_time, 2),
            'total_tokens_used': self.token_usage_tracker['total_tokens'],
            'extracted_data': extracted_data
        }
        
        logger.info(f"Extraction complete: {result['pages_processed']} pages processed in {result['processing_time']}s")
        return result


def main():
    """Main function for testing"""
    parser = LLMSpecbookParser()
    
    # Test with SKIDOO spec book
    skidoo_pdf = Path("docs/SKIDOO_2026 PRODUCT SPEC BOOK - 1-30.pdf")
    if skidoo_pdf.exists():
        logger.info("Testing SKIDOO spec book extraction...")
        result = parser.extract_specbook_data(skidoo_pdf, "SKIDOO")
        logger.info(f"SKIDOO extraction result: {result}")
    else:
        logger.warning(f"SKIDOO PDF not found: {skidoo_pdf}")
    
    # Test with LYNX spec book
    lynx_pdf = Path("docs/LYNX_2026 PRODUCT SPEC BOOK - 1-35.pdf")
    if lynx_pdf.exists():
        logger.info("Testing LYNX spec book extraction...")
        result = parser.extract_specbook_data(lynx_pdf, "LYNX")
        logger.info(f"LYNX extraction result: {result}")
    else:
        logger.warning(f"LYNX PDF not found: {lynx_pdf}")


if __name__ == "__main__":
    main()