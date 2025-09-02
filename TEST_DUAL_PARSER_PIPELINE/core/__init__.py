"""
Core module for Avito Pipeline
Contains fundamental data models, exceptions, and database utilities
"""

from .models import ProductData, CatalogData, ValidationResult, MatchResult
from .exceptions import PipelineError, ExtractionError, ValidationError, MatchingError
from .database import DatabaseManager

__all__ = [
    'ProductData',
    'CatalogData', 
    'ValidationResult',
    'MatchResult',
    'PipelineError',
    'ExtractionError',
    'ValidationError',
    'MatchingError',
    'DatabaseManager'
]