"""
Stage 4: XML Generation Module
Template-based XML generation for Avito marketplace

Key Components:
- BaseGenerator: Abstract base class for all generators
- AvitoXMLGenerator: Avito marketplace XML generation with field mapping
"""

from .base_generator import BaseGenerator
from .avito_xml_generator import AvitoXMLGenerator

__all__ = [
    'BaseGenerator',
    'AvitoXMLGenerator'
]