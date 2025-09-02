"""
LLM Extractor Implementation
Handles AI-powered extraction from specification catalogs and complex documents
"""

import json
import requests
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

import sys
sys.path.append('..')
from .base_extractor import BaseExtractor
from core import ProductData, ExtractionError

logger = logging.getLogger(__name__)


class LLMExtractor(BaseExtractor):
    """
    LLM-powered extractor for specification catalogs and complex documents
    Uses Claude or GPT APIs for intelligent document processing
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize LLM extractor with configuration"""
        default_config = {
            'provider': 'claude',
            'model': 'claude-3-sonnet-20240229',
            'max_tokens': 4000,
            'temperature': 0.1,
            'api_timeout': 30,
            'retry_attempts': 3,
            'retry_delay': 1.0
        }
        
        if config:
            default_config.update(config)
            
        super().__init__(default_config)
        self.api_key = self._get_api_key()
    
    def _get_api_key(self) -> str:
        """Get API key for the configured provider"""
        import os
        
        if self.config['provider'] == 'claude':
            key = os.getenv('CLAUDE_API_KEY')
            if not key:
                raise ExtractionError("CLAUDE_API_KEY not found in environment")
        elif self.config['provider'] == 'gpt':
            key = os.getenv('OPENAI_API_KEY')
            if not key:
                raise ExtractionError("OPENAI_API_KEY not found in environment")
        else:
            raise ExtractionError(f"Unsupported provider: {self.config['provider']}")
        
        return key
    
    def extract(self, source: Path, **kwargs) -> List[ProductData]:
        """
        Extract product data using LLM processing
        
        Args:
            source: Path to document file
            **kwargs: Additional extraction parameters
            
        Returns:
            List of extracted ProductData objects
        """
        self.stats.start_time = datetime.now()
        
        try:
            # First extract text (could be PDF, text, etc.)
            document_text = self._extract_document_text(source)
            
            # Use LLM to process and structure the data
            structured_data = self._process_with_llm(document_text, **kwargs)
            
            # Convert to ProductData objects
            products = self._convert_to_product_data(structured_data)
            
            self.stats.successful = len(products)
            self.stats.total_processed = len(products)
            
            logger.info(f"Successfully extracted {len(products)} products using {self.config['provider']}")
            return products
            
        except Exception as e:
            self.stats.failed += 1
            logger.error(f"LLM extraction failed: {e}")
            raise ExtractionError(f"Failed to extract using LLM: {str(e)}")
        
        finally:
            self.stats.end_time = datetime.now()
            if self.stats.start_time:
                self.stats.processing_time = (
                    self.stats.end_time - self.stats.start_time
                ).total_seconds()
    
    def _extract_document_text(self, source: Path) -> str:
        """Extract text from source document"""
        if source.suffix.lower() == '.pdf':
            # Use PDF extraction
            from .pdf_extractor import PDFExtractor
            pdf_extractor = PDFExtractor(self.config)
            return pdf_extractor._extract_text_pypdf2(source)
        elif source.suffix.lower() == '.txt':
            # Read text file
            with open(source, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            raise ExtractionError(f"Unsupported file type: {source.suffix}")
    
    def _process_with_llm(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Process text using configured LLM provider"""
        if self.config['provider'] == 'claude':
            return self._process_with_claude(text, **kwargs)
        elif self.config['provider'] == 'gpt':
            return self._process_with_gpt(text, **kwargs)
        else:
            raise ExtractionError(f"Unsupported LLM provider: {self.config['provider']}")
    
    def _process_with_claude(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Process text using Claude API"""
        prompt = self._build_extraction_prompt(text, **kwargs)
        
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01'
        }
        
        data = {
            'model': self.config['model'],
            'max_tokens': self.config['max_tokens'],
            'temperature': self.config['temperature'],
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
        }
        
        for attempt in range(self.config['retry_attempts']):
            try:
                response = requests.post(
                    'https://api.anthropic.com/v1/messages',
                    headers=headers,
                    json=data,
                    timeout=self.config['api_timeout']
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['content'][0]['text']
                    return self._parse_llm_response(content)
                else:
                    logger.warning(f"Claude API returned status {response.status_code}: {response.text}")
                    if attempt < self.config['retry_attempts'] - 1:
                        time.sleep(self.config['retry_delay'] * (attempt + 1))
                        continue
                    else:
                        raise ExtractionError(f"Claude API error: {response.status_code}")
                        
            except requests.RequestException as e:
                if attempt < self.config['retry_attempts'] - 1:
                    time.sleep(self.config['retry_delay'] * (attempt + 1))
                    continue
                else:
                    raise ExtractionError(f"Claude API request failed: {str(e)}")
        
        raise ExtractionError("All Claude API attempts failed")
    
    def _process_with_gpt(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Process text using GPT API"""
        prompt = self._build_extraction_prompt(text, **kwargs)
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        data = {
            'model': self.config.get('model', 'gpt-4'),
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': self.config['max_tokens'],
            'temperature': self.config['temperature']
        }
        
        for attempt in range(self.config['retry_attempts']):
            try:
                response = requests.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers=headers,
                    json=data,
                    timeout=self.config['api_timeout']
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    return self._parse_llm_response(content)
                else:
                    logger.warning(f"GPT API returned status {response.status_code}: {response.text}")
                    if attempt < self.config['retry_attempts'] - 1:
                        time.sleep(self.config['retry_delay'] * (attempt + 1))
                        continue
                    else:
                        raise ExtractionError(f"GPT API error: {response.status_code}")
                        
            except requests.RequestException as e:
                if attempt < self.config['retry_attempts'] - 1:
                    time.sleep(self.config['retry_delay'] * (attempt + 1))
                    continue
                else:
                    raise ExtractionError(f"GPT API request failed: {str(e)}")
        
        raise ExtractionError("All GPT API attempts failed")
    
    def _build_extraction_prompt(self, text: str, **kwargs) -> str:
        """Build extraction prompt for LLM"""
        target_model = kwargs.get('target_model', 'any')
        
        prompt = f"""
Extract snowmobile product information from the following document text.
Focus on model codes (4-letter codes like ADTD, ADTC), specifications, and pricing.

Target model: {target_model}

Document text:
{text[:10000]}  # Limit text length

Please extract and return a JSON array of products with the following structure:
[
  {{
    "model_code": "ADTD",
    "brand": "Ski-Doo",
    "model_name": "Model name if available",
    "year": 2026,
    "specifications": {{
      "engine": {{
        "displacement": "displacement in cc",
        "power_hp": "power in HP",
        "type": "engine type"
      }},
      "track": {{
        "length_mm": "track length",
        "width_mm": "track width"
      }},
      "dimensions": {{
        "length_mm": "overall length",
        "width_mm": "overall width",
        "weight_kg": "dry weight"
      }},
      "features": ["list", "of", "key", "features"]
    }},
    "market_positioning": "Brief description of the model",
    "price": price_if_available,
    "currency": "EUR"
  }}
]

Return only valid JSON. If no products found, return empty array [].
"""
        return prompt
    
    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into structured data"""
        try:
            # Try to extract JSON from response
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                # Fallback: try to parse entire response
                return json.loads(response)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response was: {response}")
            return []
    
    def _convert_to_product_data(self, structured_data: List[Dict[str, Any]]) -> List[ProductData]:
        """Convert structured data to ProductData objects"""
        products = []
        
        for item in structured_data:
            try:
                product = ProductData(
                    model_code=item.get('model_code', ''),
                    brand=item.get('brand', 'Ski-Doo'),
                    year=item.get('year', 2026),
                    malli=item.get('model_name'),
                    price=item.get('price'),
                    currency=item.get('currency', 'EUR'),
                    market='FINLAND',
                    extraction_metadata={
                        'extractor': 'LLMExtractor',
                        'provider': self.config['provider'],
                        'model': self.config['model'],
                        'extracted_at': datetime.now().isoformat(),
                        'specifications': item.get('specifications', {}),
                        'market_positioning': item.get('market_positioning', ''),
                        'llm_confidence': item.get('confidence', 0.8)
                    }
                )
                
                products.append(product)
                
            except Exception as e:
                logger.error(f"Error converting item to ProductData: {e}")
                continue
        
        return products
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        return {
            'total_processed': self.stats.total_processed,
            'successful': self.stats.successful,
            'failed': self.stats.failed,
            'success_rate': self.stats.success_rate,
            'processing_time': self.stats.processing_time,
            'stage': self.stats.stage.value if hasattr(self.stats.stage, 'value') else str(self.stats.stage),
            'provider': self.config['provider'],
            'model': self.config['model']
        }