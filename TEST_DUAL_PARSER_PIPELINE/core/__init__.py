"""
Core module for Avito Pipeline
Contains fundamental data models, exceptions, and database utilities
"""

from .models import ProductData, CatalogData, ValidationResult, MatchResult, PipelineStats, PipelineStage, MatchType, ValidationLevel
from .exceptions import PipelineError, ExtractionError, ValidationError, MatchingError
from .database import DatabaseManager

__all__ = [
    'ProductData',
    'CatalogData', 
    'ValidationResult',
    'MatchResult',
    'PipelineStats',
    'PipelineStage',
    'MatchType',
    'ValidationLevel',
    'PipelineError',
    'ExtractionError',
    'ValidationError',
    'MatchingError',
    'DatabaseManager'
]