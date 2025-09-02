"""
Pipeline Configuration Management
Centralized configuration for all pipeline components with environment variable support
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExtractionConfig:
    """Configuration for Stage 1: Data Extraction"""
    pdf_processor: str = "pymupdf"  # or "pdfplumber"
    llm_provider: str = "claude"    # or "openai"
    max_pages: int = 100
    timeout_seconds: int = 300
    enable_ocr: bool = True
    ocr_confidence_threshold: float = 0.8
    
    # LLM Settings
    claude_model: str = "claude-3-sonnet-20241022"
    openai_model: str = "gpt-4"
    max_tokens: int = 4000
    temperature: float = 0.1
    
    # Field extraction settings
    normalize_finnish_terms: bool = True
    validate_model_codes: bool = True
    
    def get_api_key(self, provider: str) -> str:
        """Get API key for specified provider"""
        if provider.lower() == "claude":
            key = os.getenv("CLAUDE_API_KEY")
        elif provider.lower() == "openai":
            key = os.getenv("OPENAI_API_KEY")
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        if not key:
            raise ValueError(f"Missing API key for {provider}")
        return key


@dataclass
class MatchingConfig:
    """Configuration for Stage 2: Matching Engine"""
    bert_model: str = "all-MiniLM-L6-v2"
    similarity_threshold: float = 0.7
    enable_domain_boost: bool = True
    max_catalog_entries: int = 1000
    
    # Performance settings
    batch_size: int = 50
    use_gpu: bool = False
    cache_embeddings: bool = True
    cache_duration_hours: int = 24
    
    # Fallback settings
    fallback_to_fuzzy: bool = True
    fuzzy_threshold: float = 0.6
    enable_exact_matching: bool = True
    
    # Brand filtering
    enable_brand_filtering: bool = True
    brand_boost_factor: float = 0.1


@dataclass 
class ValidationConfig:
    """Configuration for Stage 3: Validation"""
    strict_mode: bool = True
    model_validation: bool = True
    field_validation: bool = True
    business_rules: bool = True
    
    # Validation thresholds
    min_confidence_score: float = 0.5
    max_error_count: int = 10
    allow_warnings: bool = True
    
    # BRP model database settings
    brp_models_cache_hours: int = 24
    enable_fuzzy_model_matching: bool = True
    model_fuzzy_threshold: float = 0.8
    
    # Field validation settings
    price_min: int = 100000  # RUB
    price_max: int = 10000000  # RUB
    year_min: int = 2015
    year_max: int = 2030
    model_code_length: int = 4
    
    # External validation
    enable_avito_api_validation: bool = False
    avito_api_timeout: int = 10


@dataclass
class PipelineConfig:
    """Main pipeline configuration container"""
    
    # Stage configurations
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)
    matching: MatchingConfig = field(default_factory=MatchingConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    
    # General pipeline settings
    environment: str = field(default_factory=lambda: os.getenv("PIPELINE_ENV", "development"))
    debug_mode: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    worker_count: int = field(default_factory=lambda: int(os.getenv("WORKER_COUNT", "1")))
    
    # Performance settings
    processing_batch_size: int = field(default_factory=lambda: int(os.getenv("BATCH_SIZE", "50")))
    max_memory_usage_mb: int = 1024
    enable_profiling: bool = False


class ConfigManager:
    """Configuration manager with environment override support"""
    
    def __init__(self, config_file: Optional[Path] = None):
        """Initialize configuration manager"""
        self.config_file = config_file
        self._config: Optional[PipelineConfig] = None
        
    @property
    def config(self) -> PipelineConfig:
        """Get pipeline configuration (lazy loaded)"""
        if self._config is None:
            self._config = self._load_config()
        return self._config
    
    def _load_config(self) -> PipelineConfig:
        """Load configuration from environment and files"""
        try:
            config = PipelineConfig()
            config = self._apply_env_overrides(config)
            self._validate_config(config)
            logger.info(f"Configuration loaded successfully (env: {config.environment})")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _apply_env_overrides(self, config: PipelineConfig) -> PipelineConfig:
        """Apply environment variable overrides"""
        
        # Environment variable mapping
        env_mappings = {
            "EXTRACTION_PDF_PROCESSOR": ("extraction", "pdf_processor"),
            "EXTRACTION_LLM_PROVIDER": ("extraction", "llm_provider"),
            "BERT_MODEL": ("matching", "bert_model"),
            "SIMILARITY_THRESHOLD": ("matching", "similarity_threshold"),
            "VALIDATION_STRICT_MODE": ("validation", "strict_mode"),
        }
        
        for env_var, (section, key) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                section_obj = getattr(config, section)
                field_type = type(getattr(section_obj, key))
                if field_type == bool:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif field_type == int:
                    value = int(value)
                elif field_type == float:
                    value = float(value)
                
                setattr(section_obj, key, value)
        
        return config
    
    def _validate_config(self, config: PipelineConfig) -> None:
        """Validate configuration values"""
        if config.extraction.llm_provider not in ['claude', 'openai']:
            raise ValueError(f"Invalid LLM provider: {config.extraction.llm_provider}")
        
        if not 0.0 <= config.matching.similarity_threshold <= 1.0:
            raise ValueError("Similarity threshold must be between 0.0 and 1.0")


# Global configuration instance
_config_manager: Optional[ConfigManager] = None


def get_config() -> PipelineConfig:
    """Get global pipeline configuration"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager()
    
    return _config_manager.config