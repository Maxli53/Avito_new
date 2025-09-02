"""
BERT-Enhanced Matching Engine with Pure Semantic Tier 3
Replaces traditional fuzzy matching with BERT-based semantic similarity
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher
from dataclasses import asdict
import numpy as np
from data_models import (
    PriceListEntry, CatalogVehicle, MatchingResult, 
    ModelCodeMapping, DualParserConfig
)

# BERT imports
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    BERT_AVAILABLE = True
    print("BERT libraries available - semantic matching enabled")
except ImportError:
    BERT_AVAILABLE = False
    print("BERT libraries not available - falling back to traditional fuzzy matching")
    print("Install: pip install sentence-transformers scikit-learn")

class TextNormalizer:
    """Utility class for text normalization operations"""
    
    @staticmethod
    def normalize_model_name(text: str) -> str:
        """Normalize model names for matching"""
        if not text:
            return ""
        
        # Remove trademark symbols
        text = re.sub(r'[®™©]', '', text)
        
        # Standardize spacing
        text = ' '.join(text.split())
        
        # Handle common variations
        replacements = {
            'X-RS': 'XRS',
            'X RS': 'XRS',
            'E-TEC': 'ETEC',
            'E TEC': 'ETEC',
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text.strip().upper()
    
    @staticmethod
    def normalize_package_name(text: str) -> str:
        """Normalize package names for matching"""
        if not text:
            return ""
        
        # Remove common package words
        text = re.sub(r'\b(PACKAGE|WITH|AND)\b', '', text, flags=re.IGNORECASE)
        
        # Standardize spacing
        text = ' '.join(text.split())
        
        return text.strip().upper()
    
    @staticmethod
    def normalize_engine_spec(text: str) -> str:
        """Normalize engine specifications for matching"""
        if not text:
            return ""
        
        # Extract key engine info
        pattern = r'(\d{3,4})\s*([R]?)\s*(E-TEC|ACE|ETEC)\s*(TURBO\s*R?)?'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            displacement = match.group(1)
            r_variant = match.group(2) or ""
            engine_type = match.group(3).replace('-', '').upper()
            turbo = match.group(4) or ""
            
            normalized = f"{displacement}{r_variant} {engine_type}"
            if turbo:
                normalized += f" {turbo.strip().upper()}"
            
            return normalized.strip()
        
        return text.strip().upper()

class BERTSemanticMatcher:
    """BERT-based semantic matching for snowmobile terminology"""
    
    def __init__(self):
        self.model = None
        self.available = BERT_AVAILABLE
        
        if BERT_AVAILABLE:
            try:
                # Use a lightweight but effective model
                print("Loading BERT model: all-MiniLM-L6-v2...")
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                print("BERT model loaded successfully!")
            except Exception as e:
                print(f"Failed to load BERT model: {e}")
                self.available = False
        
        # Fallback domain-specific mappings for when BERT isn't available
        self.domain_mappings = {
            'PKG': 'PACKAGE',
            'PKG.': 'PACKAGE', 
            'EXPERT PKG': 'EXPERT PACKAGE',
            'X-RS': 'XRS',
            'E-TEC': 'ETEC',
            'TURBO R': 'TURBO',
            'NEO+': 'NEO PLUS',
            'SE': 'SPECIAL EDITION',
            'LE': 'LIMITED EDITION',
        }
    
    def semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts"""
        
        if not self.available or not self.model:
            # Fallback to domain-specific similarity
            return self._domain_similarity(text1, text2)
        
        try:
            # Clean and prepare texts
            clean_text1 = self._prepare_text_for_bert(text1)
            clean_text2 = self._prepare_text_for_bert(text2)
            
            if not clean_text1 or not clean_text2:
                return 0.0
            
            # Generate BERT embeddings
            embeddings = self.model.encode([clean_text1, clean_text2])
            
            # Calculate cosine similarity
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            
            # Apply domain-specific boosting
            domain_boost = self._domain_boost(clean_text1, clean_text2)
            
            # Combine BERT similarity with domain knowledge
            final_similarity = min(1.0, similarity + domain_boost)
            
            return float(final_similarity)
            
        except Exception as e:
            print(f"BERT similarity calculation failed: {e}")
            return self._domain_similarity(text1, text2)
    
    def _prepare_text_for_bert(self, text: str) -> str:
        """Prepare text for BERT processing"""
        if not text:
            return ""
        
        # Clean up the text but preserve semantic meaning
        text = text.strip()
        
        # Replace domain abbreviations for better BERT understanding
        for abbrev, full in self.domain_mappings.items():
            text = re.sub(rf'\b{re.escape(abbrev)}\b', full, text, flags=re.IGNORECASE)
        
        # Remove trademark symbols but preserve semantic content
        text = re.sub(r'[®™©]', '', text)
        
        # Normalize spacing
        text = ' '.join(text.split())
        
        return text.lower()  # BERT models typically work better with lowercase
    
    def _domain_boost(self, text1: str, text2: str) -> float:
        """Apply domain-specific similarity boosting"""
        boost = 0.0
        
        # Boost for model family matches
        families = ['summit', 'expedition', 'renegade', 'mxz', 'backcountry', 'freeride']
        for family in families:
            if family in text1.lower() and family in text2.lower():
                boost += 0.1
        
        # Boost for engine matches
        engines = ['850', '600', '900', 'etec', 'ace', 'turbo']
        for engine in engines:
            if engine in text1.lower() and engine in text2.lower():
                boost += 0.05
        
        # Boost for package indicators
        packages = ['expert', 'competition', 'sport', 'adrenaline', 'xtreme']
        for package in packages:
            if package in text1.lower() and package in text2.lower():
                boost += 0.05
        
        return min(0.2, boost)  # Cap boost at 0.2
    
    def _domain_similarity(self, text1: str, text2: str) -> float:
        """Fallback domain-specific similarity when BERT is unavailable"""
        
        # Apply domain mappings
        processed_text1 = text1.upper()
        processed_text2 = text2.upper()
        
        for abbrev, full in self.domain_mappings.items():
            processed_text1 = processed_text1.replace(abbrev, full)
            processed_text2 = processed_text2.replace(abbrev, full)
        
        # Use SequenceMatcher on processed text
        similarity = SequenceMatcher(None, processed_text1, processed_text2).ratio()
        
        # Apply domain boosting
        boost = self._domain_boost(processed_text1, processed_text2)
        
        return min(1.0, similarity + boost)

class BERTEnhancedMatchingEngine:
    """Enhanced matching engine with BERT-based Tier 3 semantic matching"""
    
    def __init__(self, config: DualParserConfig):
        self.config = config
        self.normalizer = TextNormalizer()
        self.bert_matcher = BERTSemanticMatcher()
        
        print(f"BERT-Enhanced Matching Engine (Tier 2) initialized:")
        print(f"  BERT available: {self.bert_matcher.available}")
        print(f"  Tier 1 (Exact) threshold: 0.95")
        print(f"  Tier 2 (BERT Semantic) threshold: 0.80") 
        print(f"  Tier 3 (Fuzzy Fallback) threshold: 0.60")
    
    def match_price_to_catalog(
        self, 
        price_entry: PriceListEntry, 
        catalog_vehicles: List[CatalogVehicle]
    ) -> Tuple[Optional[CatalogVehicle], MatchingResult]:
        """
        Match a price list entry to catalog vehicles using 3-tier strategy with BERT Tier 2
        Returns the best match and detailed matching result
        """
        
        result = MatchingResult()
        best_match = None
        
        # Tier 1: Basic exact matching
        exact_match, tier1_confidence = self._tier1_exact_match(price_entry, catalog_vehicles)
        if exact_match and tier1_confidence >= 0.95:  # High threshold for exact matches
            result.tier_1_exact_match = True
            result.tier_1_confidence = tier1_confidence
            result.final_matching_method = "EXACT"
            result.overall_confidence = tier1_confidence
            best_match = exact_match
        
        # Tier 2: BERT-based semantic matching (if Tier 1 failed)
        if not best_match:
            bert_match, tier2_confidence, algorithms = self._tier2_bert_semantic_match(
                price_entry, catalog_vehicles
            )
            if bert_match and tier2_confidence >= 0.80:  # Medium threshold for BERT semantic
                result.tier_2_normalized_match = True  # Keep field name for compatibility
                result.tier_2_confidence = tier2_confidence
                result.tier_2_transformations = algorithms
                result.final_matching_method = "BERT_SEMANTIC"
                result.overall_confidence = tier2_confidence
                best_match = bert_match
        
        # Tier 3: Traditional fuzzy fallback (if Tier 1 & 2 failed)
        if not best_match:
            fuzzy_match, tier3_confidence, algorithms = self._tier3_traditional_fuzzy_match(
                price_entry, catalog_vehicles
            )
            if fuzzy_match and tier3_confidence >= 0.60:  # Lower threshold for fuzzy fallback
                result.tier_3_fuzzy_match = True
                result.tier_3_confidence = tier3_confidence
                result.tier_3_algorithms = algorithms
                result.final_matching_method = "FUZZY_FALLBACK"
                result.overall_confidence = tier3_confidence
                best_match = fuzzy_match
        
        # Set final method if no match found
        if not best_match:
            result.final_matching_method = "NO_MATCH"
        
        # Set human review flag
        result.requires_human_review = (
            result.overall_confidence < self.config.auto_accept_threshold or
            not best_match
        )
        
        return best_match, result
    
    def _tier1_exact_match(
        self, 
        price_entry: PriceListEntry, 
        catalog_vehicles: List[CatalogVehicle]
    ) -> Tuple[Optional[CatalogVehicle], float]:
        """Tier 1: Basic exact string matching only"""
        
        price_model = price_entry.malli or ""
        
        for vehicle in catalog_vehicles:
            # Simple exact match with model family
            if price_model.upper() == vehicle.model_family.upper():
                return vehicle, 1.0
            
            # Simple exact match with vehicle name (contains check)
            if price_model.upper() in vehicle.name.upper():
                return vehicle, 0.95
        
        return None, 0.0
    
    def _tier2_bert_semantic_match(
        self, 
        price_entry: PriceListEntry, 
        catalog_vehicles: List[CatalogVehicle]
    ) -> Tuple[Optional[CatalogVehicle], float, Dict[str, Any]]:
        """Tier 2: BERT-based semantic matching"""
        
        # Construct semantic text for price entry
        price_text = f"{price_entry.malli or ''} {price_entry.paketti or ''}".strip()
        
        best_match = None
        best_confidence = 0.0
        bert_results = []
        
        for vehicle in catalog_vehicles:
            # Construct semantic text for catalog vehicle
            catalog_text = f"{vehicle.model_family} {vehicle.package_name or ''}".strip()
            
            # Calculate BERT semantic similarity
            similarity = self.bert_matcher.semantic_similarity(price_text, catalog_text)
            
            # Same model family check (less strict than old fuzzy)
            same_family = self._check_same_family(price_entry.malli or "", vehicle.model_family)
            
            # Apply family penalty but not as harsh as before
            if not same_family:
                similarity *= 0.8  # Reduced penalty for cross-family matches
            
            bert_results.append({
                "vehicle_name": vehicle.name,
                "similarity": similarity,
                "same_family": same_family,
                "price_text": price_text,
                "catalog_text": catalog_text
            })
            
            if similarity > best_confidence:
                best_confidence = similarity
                best_match = vehicle
        
        algorithms_data = {
            "method": "BERT_SEMANTIC",
            "bert_available": self.bert_matcher.available,
            "results": bert_results,
            "best_similarity": best_confidence
        }
        
        return best_match, best_confidence, algorithms_data
    
    def _tier3_traditional_fuzzy_match(
        self, 
        price_entry: PriceListEntry, 
        catalog_vehicles: List[CatalogVehicle]
    ) -> Tuple[Optional[CatalogVehicle], float, Dict[str, Any]]:
        """Tier 3: Traditional fuzzy matching fallback"""
        
        price_text = f"{price_entry.malli or ''} {price_entry.paketti or ''}".strip()
        
        best_match = None
        best_confidence = 0.0
        algorithms_used = []
        
        for vehicle in catalog_vehicles:
            catalog_text = f"{vehicle.model_family} {vehicle.package_name or ''}".strip()
            
            # Algorithm 1: SequenceMatcher
            seq_similarity = SequenceMatcher(None, price_text.upper(), catalog_text.upper()).ratio()
            
            # Algorithm 2: Word-based similarity
            price_words = set(price_text.upper().split())
            catalog_words = set(catalog_text.upper().split())
            if price_words and catalog_words:
                word_similarity = len(price_words & catalog_words) / len(price_words | catalog_words)
            else:
                word_similarity = 0.0
            
            # Algorithm 3: Length similarity (penalty for very different lengths)
            len_ratio = min(len(price_text), len(catalog_text)) / max(len(price_text), len(catalog_text), 1)
            length_penalty = 0.8 if len_ratio < 0.5 else 1.0
            
            # Combine algorithms
            combined_confidence = (seq_similarity * 0.5 + word_similarity * 0.5) * length_penalty
            
            # Same model family requirement (strict for fallback)
            same_family = self._check_same_family(price_entry.malli or "", vehicle.model_family)
            if not same_family:
                combined_confidence *= 0.3  # Heavy penalty for cross-family matches
            
            if combined_confidence > best_confidence:
                best_confidence = combined_confidence
                best_match = vehicle
                algorithms_used = [
                    {"name": "sequence_matcher", "score": seq_similarity},
                    {"name": "word_similarity", "score": word_similarity},
                    {"name": "length_penalty", "score": length_penalty},
                    {"name": "same_family_check", "passed": same_family}
                ]
        
        algorithms_data = {"algorithms": algorithms_used, "combined_score": best_confidence}
        
        return best_match, best_confidence, algorithms_data
    
    def _check_same_family(self, price_model: str, catalog_family: str) -> bool:
        """Check if price list model and catalog vehicle are from same family"""
        
        family_keywords = {
            'SUMMIT': ['SUMMIT'],
            'RENEGADE': ['RENEGADE'],
            'MXZ': ['MXZ'],
            'EXPEDITION': ['EXPEDITION'],
            'BACKCOUNTRY': ['BACKCOUNTRY'],
            'FREERIDE': ['FREERIDE'],
            'SKANDIC': ['SKANDIC'],
            'TUNDRA': ['TUNDRA'],
            'GRAND TOURING': ['GRAND TOURING', 'GT']
        }
        
        price_upper = price_model.upper()
        catalog_upper = catalog_family.upper()
        
        for family, keywords in family_keywords.items():
            price_has_family = any(keyword in price_upper for keyword in keywords)
            catalog_has_family = any(keyword in catalog_upper for keyword in keywords)
            
            if price_has_family and catalog_has_family:
                return True
        
        return False