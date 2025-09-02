"""
Modular matching engine for dual parser pipeline
Handles 3-tier matching strategy between Finnish price lists and English catalogs
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher
from dataclasses import asdict
from data_models import (
    PriceListEntry, CatalogVehicle, MatchingResult, 
    ModelCodeMapping, DualParserConfig
)

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
        # Match patterns like "850 E-TEC", "600R E-TEC", "900 ACE TURBO R"
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

class MatchingEngine:
    """Core matching engine implementing 3-tier matching strategy"""
    
    def __init__(self, config: DualParserConfig):
        self.config = config
        self.normalizer = TextNormalizer()
    
    def match_price_to_catalog(
        self, 
        price_entry: PriceListEntry, 
        catalog_vehicles: List[CatalogVehicle]
    ) -> Tuple[Optional[CatalogVehicle], MatchingResult]:
        """
        Match a price list entry to catalog vehicles using 3-tier strategy
        Returns the best match and detailed matching result
        """
        
        result = MatchingResult()
        best_match = None
        
        # Tier 1: Exact matching
        exact_match, tier1_confidence = self._tier1_exact_match(price_entry, catalog_vehicles)
        if exact_match and tier1_confidence >= self.config.exact_match_threshold:
            result.tier_1_exact_match = True
            result.tier_1_confidence = tier1_confidence
            result.final_matching_method = "EXACT"
            result.overall_confidence = tier1_confidence
            best_match = exact_match
        
        # Tier 2: Normalized matching (if Tier 1 failed)
        if not best_match:
            normalized_match, tier2_confidence, transformations = self._tier2_normalized_match(
                price_entry, catalog_vehicles
            )
            if normalized_match and tier2_confidence >= self.config.normalized_match_threshold:
                result.tier_2_normalized_match = True
                result.tier_2_confidence = tier2_confidence
                result.tier_2_transformations = transformations
                result.final_matching_method = "NORMALIZED"
                result.overall_confidence = tier2_confidence
                best_match = normalized_match
        
        # Tier 3: Fuzzy matching (if Tier 1 & 2 failed)
        if not best_match:
            fuzzy_match, tier3_confidence, algorithms = self._tier3_fuzzy_match(
                price_entry, catalog_vehicles
            )
            if fuzzy_match and tier3_confidence >= self.config.fuzzy_match_threshold:
                result.tier_3_fuzzy_match = True
                result.tier_3_confidence = tier3_confidence
                result.tier_3_algorithms = algorithms
                result.final_matching_method = "FUZZY"
                result.overall_confidence = tier3_confidence
                best_match = fuzzy_match
        
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
        """Tier 1: Exact string matching"""
        
        price_model = price_entry.malli or ""
        price_package = price_entry.paketti or ""
        
        for vehicle in catalog_vehicles:
            # Try exact match with model family
            if price_model.upper() in vehicle.model_family.upper():
                # Check package match if available
                if not price_package or (
                    vehicle.package_name and 
                    price_package.upper() in vehicle.package_name.upper()
                ):
                    return vehicle, 0.95
            
            # Try exact match with vehicle name
            if price_model.upper() in vehicle.name.upper():
                return vehicle, 0.90
        
        return None, 0.0
    
    def _tier2_normalized_match(
        self, 
        price_entry: PriceListEntry, 
        catalog_vehicles: List[CatalogVehicle]
    ) -> Tuple[Optional[CatalogVehicle], float, Dict[str, Any]]:
        """Tier 2: Normalized matching with transformations"""
        
        # Normalize price list data
        norm_price_model = self.normalizer.normalize_model_name(price_entry.malli or "")
        norm_price_package = self.normalizer.normalize_package_name(price_entry.paketti or "")
        norm_price_engine = self.normalizer.normalize_engine_spec(price_entry.moottori or "")
        
        transformations = {
            "normalized_model": norm_price_model,
            "normalized_package": norm_price_package,
            "normalized_engine": norm_price_engine
        }
        
        best_match = None
        best_confidence = 0.0
        
        for vehicle in catalog_vehicles:
            # Normalize catalog data
            norm_catalog_model = self.normalizer.normalize_model_name(vehicle.model_family)
            norm_catalog_name = self.normalizer.normalize_model_name(vehicle.name)
            norm_catalog_package = self.normalizer.normalize_package_name(vehicle.package_name or "")
            
            confidence = 0.0
            
            # Model name matching
            if norm_price_model in norm_catalog_model or norm_price_model in norm_catalog_name:
                confidence += 0.4
            
            # Package matching
            if not norm_price_package or norm_price_package in norm_catalog_package:
                confidence += 0.3
            
            # Engine matching if available
            if norm_price_engine and vehicle.specifications.engine:
                norm_catalog_engine = self.normalizer.normalize_engine_spec(vehicle.specifications.engine)
                if norm_price_engine in norm_catalog_engine:
                    confidence += 0.3
            else:
                confidence += 0.2  # No engine conflict
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = vehicle
        
        return best_match, best_confidence, transformations
    
    def _tier3_fuzzy_match(
        self, 
        price_entry: PriceListEntry, 
        catalog_vehicles: List[CatalogVehicle]
    ) -> Tuple[Optional[CatalogVehicle], float, Dict[str, Any]]:
        """Tier 3: Fuzzy matching with similarity algorithms"""
        
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
            
            # Same model family requirement (strict)
            same_family = self._check_same_family(price_entry.malli or "", vehicle.model_family)
            if not same_family:
                combined_confidence *= 0.3  # Heavy penalty for cross-family matches
            
            if combined_confidence > best_confidence and combined_confidence >= self.config.fuzzy_match_threshold:
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

class ModelCodeMappingService:
    """Service for managing model code mappings between Finnish and English"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def create_mapping(
        self, 
        price_entry: PriceListEntry, 
        catalog_vehicle: CatalogVehicle, 
        matching_result: MatchingResult
    ) -> ModelCodeMapping:
        """Create a model code mapping from successful match"""
        
        mapping = ModelCodeMapping(
            model_code=price_entry.model_code,
            malli=price_entry.malli or "",
            paketti=price_entry.paketti,
            english_model_name=catalog_vehicle.name,
            english_package_name=catalog_vehicle.package_name,
            base_model_id=catalog_vehicle.id,
            matching_method=matching_result.final_matching_method,
            matching_confidence=matching_result.overall_confidence,
            verification_status="auto_matched" if matching_result.overall_confidence >= 0.9 else "needs_review"
        )
        
        return mapping
    
    def save_mapping(self, mapping: ModelCodeMapping) -> bool:
        """Save model code mapping to database"""
        import sqlite3
        from datetime import datetime
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO model_code_mappings (
                    id, model_code, malli, paketti, english_model_name,
                    english_package_name, base_model_id, matching_method,
                    matching_confidence, matching_algorithm_version, created_by,
                    verification_status, manual_override, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mapping.id, mapping.model_code, mapping.malli, mapping.paketti,
                mapping.english_model_name, mapping.english_package_name,
                mapping.base_model_id, mapping.matching_method, mapping.matching_confidence,
                mapping.matching_algorithm_version, mapping.created_by,
                mapping.verification_status, mapping.manual_override,
                datetime.now(), datetime.now()
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error saving model code mapping: {e}")
            return False
        finally:
            conn.close()
    
    def get_existing_mapping(self, model_code: str) -> Optional[ModelCodeMapping]:
        """Retrieve existing mapping for model code"""
        import sqlite3
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM model_code_mappings WHERE model_code = ?
                ORDER BY matching_confidence DESC LIMIT 1
            """, (model_code,))
            
            row = cursor.fetchone()
            if row:
                # Convert row to ModelCodeMapping (simplified)
                # In production, you'd want proper ORM mapping
                return ModelCodeMapping(
                    id=row[0], model_code=row[1], malli=row[2],
                    # ... map other fields
                )
            
            return None
            
        except Exception as e:
            print(f"Error retrieving model code mapping: {e}")
            return None
        finally:
            conn.close()