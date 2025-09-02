"""
Stage 2: Matching Engine Module
BERT semantic matching and Claude inheritance matching with catalog data

Key Components:
- BaseMatcher: Abstract base class for all matchers
- BERTMatcher: BERT semantic similarity matching (98.4% success rate)
- ClaudeInheritanceMatcher: LLM-powered specification inheritance matching
"""

from .base_matcher import BaseMatcher
from .bert_matcher import BERTMatcher
from .claude_inheritance_matcher import ClaudeInheritanceMatcher

__all__ = [
    'BaseMatcher',
    'BERTMatcher',
    'ClaudeInheritanceMatcher'
]