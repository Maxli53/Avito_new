#!/usr/bin/env python3
"""
Model Catalog Fetcher - Production-ready model management
Fetches and caches Avito's snowmobile model catalog
"""

import requests
import xml.etree.ElementTree as ET
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import logging
from typing import List, Optional
import hashlib

# Moscow timezone for Avito processing times
MOSCOW_TZ = timezone(timedelta(hours=3))

class ModelCatalogFetcher:
    """
    Production-ready model catalog management with intelligent caching
    """
    
    def __init__(self, cache_dir: str = "./cache/models"):
        self.catalog_url = "https://www.avito.ru/web/1/catalogs/content/feed/snegohod.xml"
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / "snegohod_models.xml"
        self.models_json = self.cache_dir / "brp_models.json"
        self.metadata_file = self.cache_dir / "fetch_metadata.json"
        
        # Cache settings
        self.cache_duration = 86400  # 24 hours
        self.daily_refresh_hour = 2  # 02:00 MSK
        
        # Rate limiting
        self.retry_attempts = 3
        self.base_wait_time = 10  # seconds
        
        # Initialize logging
        self.setup_logging()
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load cached models on init
        self.models = self.load_models()
        
    def setup_logging(self):
        """Setup logging for model catalog operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - ModelCatalog - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def should_refresh_cache(self) -> bool:
        """Determine if cache should be refreshed"""
        
        # Check if cache exists
        if not self.cache_file.exists():
            self.logger.info("No cache file exists - refresh needed")
            return True
        
        # Get current time in Moscow timezone
        moscow_now = datetime.now(MOSCOW_TZ)
        
        # Get cache metadata
        metadata = self.get_cache_metadata()
        
        if not metadata:
            self.logger.info("No cache metadata - refresh needed")
            return True
        
        last_fetch = datetime.fromisoformat(metadata.get('last_fetch', '2000-01-01T00:00:00+03:00'))
        cache_age_hours = (moscow_now - last_fetch).total_seconds() / 3600
        
        # Check if it's daily refresh time (02:00 MSK) and we haven't fetched today
        if (moscow_now.hour == self.daily_refresh_hour and 
            last_fetch.date() < moscow_now.date()):
            self.logger.info("Daily refresh time reached")
            return True
        
        # Check if cache is older than duration
        if cache_age_hours > (self.cache_duration / 3600):
            self.logger.info(f"Cache is {cache_age_hours:.1f} hours old - refresh needed")
            return True
        
        self.logger.info(f"Cache is fresh ({cache_age_hours:.1f} hours old)")
        return False
    
    def get_cache_metadata(self) -> Optional[dict]:
        """Get cache metadata"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Error reading cache metadata: {e}")
        return None
    
    def save_cache_metadata(self, metadata: dict):
        """Save cache metadata"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            self.logger.error(f"Error saving cache metadata: {e}")
    
    def fetch_catalog_from_avito(self) -> bool:
        """Fetch catalog from Avito with rate limit handling"""
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/xml,text/xml,*/*;q=0.9',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        for attempt in range(self.retry_attempts):
            try:
                self.logger.info(f"Fetching catalog from Avito (attempt {attempt + 1}/{self.retry_attempts})")
                
                response = requests.get(
                    self.catalog_url,
                    headers=headers,
                    timeout=30,
                    allow_redirects=True
                )
                
                self.logger.info(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    # Save raw XML
                    with open(self.cache_file, 'wb') as f:
                        f.write(response.content)
                    
                    # Parse and save models
                    brp_models = self.parse_xml_content(response.content)
                    
                    if brp_models:
                        self.save_brp_models(brp_models)
                        
                        # Save metadata
                        metadata = {
                            'last_fetch': datetime.now(MOSCOW_TZ).isoformat(),
                            'fetch_status': 'success',
                            'models_count': len(brp_models),
                            'xml_size': len(response.content),
                            'content_hash': hashlib.md5(response.content).hexdigest()
                        }
                        self.save_cache_metadata(metadata)
                        
                        self.logger.info(f"Successfully fetched {len(brp_models)} BRP models")
                        self.models = brp_models
                        return True
                
                elif response.status_code == 429:
                    # Rate limited
                    wait_time = self.base_wait_time * (2 ** attempt)
                    self.logger.warning(f"Rate limited (429) - waiting {wait_time} seconds")
                    time.sleep(wait_time)
                    
                elif response.status_code in [301, 302, 303, 307, 308]:
                    # Redirect - requests should handle this automatically
                    self.logger.warning(f"Redirect response: {response.status_code}")
                    
                else:
                    self.logger.error(f"HTTP error {response.status_code}: {response.text[:200]}")
                    
            except Exception as e:
                self.logger.error(f"Error fetching catalog (attempt {attempt + 1}): {e}")
                
                if attempt < self.retry_attempts - 1:
                    wait_time = self.base_wait_time * (2 ** attempt)
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
        
        # All attempts failed
        self.logger.error("All fetch attempts failed")
        
        # Update metadata with failure
        metadata = {
            'last_fetch_attempt': datetime.now(MOSCOW_TZ).isoformat(),
            'fetch_status': 'failed',
            'error': 'Max retry attempts exceeded'
        }
        self.save_cache_metadata(metadata)
        
        return False
    
    def parse_xml_content(self, xml_content: bytes) -> List[str]:
        """Parse XML content to extract BRP models"""
        
        try:
            # Parse XML
            root = ET.fromstring(xml_content)
            self.logger.info(f"XML root: {root.tag}")
            
            models = []
            brp_models = []
            
            # Extract all text content from XML
            for elem in root.iter():
                if elem.text and len(elem.text.strip()) > 3:
                    text = elem.text.strip()
                    models.append(text)
            
            # Remove duplicates
            models = list(set(models))
            
            # Filter for BRP models
            brp_brands = [
                'ski-doo', 'lynx', 'expedition', 'mxz', 'renegade', 
                'summit', 'skandic', 'tundra', 'brp', 'bombardier'
            ]
            
            for model_name in models:
                model_lower = model_name.lower()
                
                # Check if contains BRP brand terms
                is_brp = any(brand in model_lower for brand in brp_brands)
                
                if is_brp:
                    brp_models.append(model_name)
            
            self.logger.info(f"Parsed {len(models)} total models, {len(brp_models)} BRP models")
            
            return sorted(brp_models)
            
        except ET.ParseError as e:
            self.logger.error(f"XML parsing error: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error parsing XML content: {e}")
            return []
    
    def save_brp_models(self, models: List[str]):
        """Save BRP models to JSON file"""
        
        models_data = {
            'source': 'Avito XML Catalog',
            'source_url': self.catalog_url,
            'extracted_date': datetime.now(MOSCOW_TZ).isoformat(),
            'total_brp_models': len(models),
            'brp_models': models
        }
        
        try:
            with open(self.models_json, 'w', encoding='utf-8') as f:
                json.dump(models_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved {len(models)} BRP models to {self.models_json}")
            
        except Exception as e:
            self.logger.error(f"Error saving BRP models: {e}")
    
    def load_models(self) -> List[str]:
        """Load models from cache"""
        
        # Try to load from JSON cache first
        if self.models_json.exists():
            try:
                with open(self.models_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    models = data.get('brp_models', [])
                    self.logger.info(f"Loaded {len(models)} BRP models from cache")
                    return models
            except Exception as e:
                self.logger.error(f"Error loading cached models: {e}")
        
        # Fallback: try to parse XML cache
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'rb') as f:
                    xml_content = f.read()
                    models = self.parse_xml_content(xml_content)
                    if models:
                        self.save_brp_models(models)  # Save for next time
                        return models
            except Exception as e:
                self.logger.error(f"Error parsing cached XML: {e}")
        
        self.logger.warning("No cached models found")
        return []
    
    def get_models(self, force_refresh: bool = False) -> List[str]:
        """Get BRP models with intelligent caching"""
        
        # Force refresh if requested
        if force_refresh or self.should_refresh_cache():
            self.logger.info("Refreshing model catalog")
            
            if self.fetch_catalog_from_avito():
                self.logger.info("Successfully refreshed model catalog")
            else:
                self.logger.warning("Failed to refresh - using cached models")
                if not self.models:
                    self.models = self.load_models()
        
        # Ensure we have models
        if not self.models:
            self.models = self.load_models()
        
        return self.models
    
    def is_valid_model(self, model_name: str) -> bool:
        """Check if model name is valid"""
        models = self.get_models()
        return model_name in models
    
    def find_similar_models(self, model_name: str, limit: int = 5) -> List[str]:
        """Find similar model names"""
        models = self.get_models()
        
        if not model_name:
            return []
        
        model_lower = model_name.lower()
        similar_models = []
        
        # Exact substring matches
        for model in models:
            if model_lower in model.lower() or model.lower() in model_lower:
                similar_models.append(model)
        
        # Remove exact match if exists
        if model_name in similar_models:
            similar_models.remove(model_name)
        
        return similar_models[:limit]
    
    def get_cache_status(self) -> dict:
        """Get cache status information"""
        metadata = self.get_cache_metadata() or {}
        cache_exists = self.cache_file.exists()
        models_count = len(self.models)
        
        moscow_now = datetime.now(MOSCOW_TZ)
        last_fetch = metadata.get('last_fetch')
        
        cache_age_hours = None
        if last_fetch:
            try:
                last_fetch_dt = datetime.fromisoformat(last_fetch)
                cache_age_hours = (moscow_now - last_fetch_dt).total_seconds() / 3600
            except:
                pass
        
        return {
            'cache_exists': cache_exists,
            'cache_file_size': self.cache_file.stat().st_size if cache_exists else 0,
            'models_loaded': models_count,
            'last_fetch': last_fetch,
            'cache_age_hours': cache_age_hours,
            'fetch_status': metadata.get('fetch_status'),
            'should_refresh': self.should_refresh_cache(),
            'next_refresh_time': f"{self.daily_refresh_hour:02d}:00 MSK daily"
        }

def main():
    """Test the model catalog fetcher"""
    
    print("=== AVITO MODEL CATALOG FETCHER TEST ===")
    
    fetcher = ModelCatalogFetcher()
    
    # Get cache status
    status = fetcher.get_cache_status()
    print(f"\nCache Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # Get models
    print(f"\nFetching models...")
    models = fetcher.get_models()
    
    print(f"\nResults:")
    print(f"  Total BRP models: {len(models)}")
    
    if models:
        print(f"\nFirst 10 models:")
        for i, model in enumerate(models[:10], 1):
            print(f"  {i:2d}. {model}")
        
        # Test validation
        test_models = [
            "Ski-Doo MXZ X 600R E-TEC",
            "Invalid Model Name",
            "Lynx 49 Ranger"
        ]
        
        print(f"\nModel validation test:")
        for test_model in test_models:
            is_valid = fetcher.is_valid_model(test_model)
            print(f"  '{test_model}': {'✓ Valid' if is_valid else '✗ Invalid'}")
            
            if not is_valid:
                similar = fetcher.find_similar_models(test_model, 3)
                if similar:
                    print(f"    Similar: {', '.join(similar)}")
    
    print(f"\nModel catalog fetcher test complete!")

if __name__ == "__main__":
    main()