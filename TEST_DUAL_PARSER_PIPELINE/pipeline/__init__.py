"""
Pipeline Module for Avito Data Processing
5-Stage pipeline architecture for snowmobile data processing and XML generation

Stages:
1. Data Extraction - PDF parsing and LLM-powered field extraction
2. Matching Engine - BERT semantic matching with catalog data  
3. Validation - Business rule validation and data quality checks
4. XML Generation - Template-based Avito XML generation
5. Upload Pipeline - FTP upload and processing monitoring
"""

from .stage1_extraction import *
from .stage2_matching import *
from .stage3_validation import *
from .stage4_generation import *
from .stage5_upload import *

__all__ = [
    # Stage 1 - Data Extraction
    'BaseExtractor',
    'PDFExtractor', 
    'LLMExtractor',
    
    # Stage 2 - Matching Engine
    'BaseMatcher',
    'BERTMatcher',
    'ClaudeInheritanceMatcher',
    
    # Stage 3 - Validation
    'BaseValidator',
    'InternalValidator',
    'BRPCatalogValidator',
    
    # Stage 4 - XML Generation
    'BaseGenerator',
    'AvitoXMLGenerator',
    
    # Stage 5 - Upload Pipeline
    'BaseUploader',
    'FTPUploader',
    'ProcessingMonitor'
]