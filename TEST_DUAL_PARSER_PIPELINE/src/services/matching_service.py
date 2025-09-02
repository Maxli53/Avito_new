import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID

from ..models.domain import (
    PriceEntry, BaseModel, MatchingResult, ProcessingStatus
)
from ..repositories.database import DatabaseRepository


logger = logging.getLogger(__name__)


class MatchingService:
    """Deterministic matching service between price entries and base models"""
    
    def __init__(self, db_repo: DatabaseRepository):
        self.db_repo = db_repo
    
    async def match_price_entry(self, price_entry_id: UUID) -> MatchingResult:
        """
        Match a single price entry to a base model using deterministic matching
        
        Args:
            price_entry_id: UUID of the price entry to match
            
        Returns:
            MatchingResult with match information
        """
        try:
            # Get price entry
            price_entry = await self.db_repo.get_price_entry(price_entry_id)
            if not price_entry:
                return MatchingResult(
                    price_entry_id=price_entry_id,
                    base_model_id=None,
                    matched=False,
                    confidence_score=Decimal("0.0"),
                    match_method="none",
                    error_message="Price entry not found"
                )
            
            # Try deterministic matching first
            base_model = await self._deterministic_match(price_entry)
            
            if base_model:
                # Update price entry status to matched
                await self.db_repo.update_price_entry_status(
                    price_entry_id, 
                    ProcessingStatus.MATCHED
                )
                
                return MatchingResult(
                    price_entry_id=price_entry_id,
                    base_model_id=base_model.id,
                    matched=True,
                    confidence_score=Decimal("1.0"),  # Perfect match for deterministic
                    match_method="deterministic"
                )
            
            # Try fuzzy matching as fallback
            base_model, confidence = await self._fuzzy_match(price_entry)
            
            if base_model and confidence >= Decimal("0.8"):
                await self.db_repo.update_price_entry_status(
                    price_entry_id, 
                    ProcessingStatus.MATCHED
                )
                
                return MatchingResult(
                    price_entry_id=price_entry_id,
                    base_model_id=base_model.id,
                    matched=True,
                    confidence_score=confidence,
                    match_method="fuzzy"
                )
            
            # No match found
            logger.warning(f"No match found for price entry {price_entry.model_code} with lookup key {price_entry.catalog_lookup_key}")
            
            return MatchingResult(
                price_entry_id=price_entry_id,
                base_model_id=None,
                matched=False,
                confidence_score=confidence if confidence else Decimal("0.0"),
                match_method="none",
                error_message=f"No matching base model found for lookup key: {price_entry.catalog_lookup_key}"
            )
            
        except Exception as e:
            logger.error(f"Matching failed for price entry {price_entry_id}: {e}")
            return MatchingResult(
                price_entry_id=price_entry_id,
                base_model_id=None,
                matched=False,
                confidence_score=Decimal("0.0"),
                match_method="error",
                error_message=str(e)
            )
    
    async def batch_match_price_entries(self, price_entry_ids: List[UUID]) -> List[MatchingResult]:
        """
        Match multiple price entries in batch
        
        Args:
            price_entry_ids: List of price entry UUIDs to match
            
        Returns:
            List of MatchingResult objects
        """
        results = []
        
        logger.info(f"Starting batch matching for {len(price_entry_ids)} price entries")
        
        for price_entry_id in price_entry_ids:
            try:
                result = await self.match_price_entry(price_entry_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Batch matching failed for entry {price_entry_id}: {e}")
                results.append(MatchingResult(
                    price_entry_id=price_entry_id,
                    base_model_id=None,
                    matched=False,
                    confidence_score=Decimal("0.0"),
                    match_method="error",
                    error_message=str(e)
                ))
        
        # Log statistics
        matched_count = sum(1 for r in results if r.matched)
        logger.info(f"Batch matching completed: {matched_count}/{len(results)} matches ({(matched_count/len(results)*100):.1f}%)")
        
        return results
    
    async def match_all_unmatched_entries(self) -> List[MatchingResult]:
        """
        Match all unmatched price entries in the database
        
        Returns:
            List of MatchingResult objects
        """
        # Get all unmatched price entries
        unmatched_entries = await self.db_repo.get_unmatched_price_entries()
        
        if not unmatched_entries:
            logger.info("No unmatched price entries found")
            return []
        
        logger.info(f"Found {len(unmatched_entries)} unmatched price entries")
        
        # Extract IDs
        entry_ids = [entry.id for entry in unmatched_entries]
        
        # Batch match
        return await self.batch_match_price_entries(entry_ids)
    
    async def _deterministic_match(self, price_entry: PriceEntry) -> Optional[BaseModel]:
        """
        Perform deterministic matching using catalog_lookup_key
        
        Args:
            price_entry: PriceEntry to match
            
        Returns:
            BaseModel if found, None otherwise
        """
        try:
            logger.debug(f"Attempting deterministic match for {price_entry.model_code} with key {price_entry.catalog_lookup_key}")
            
            # Direct lookup by catalog_lookup_key
            base_model = await self.db_repo.get_base_model_by_lookup_key(price_entry.catalog_lookup_key)
            
            if base_model:
                logger.debug(f"Deterministic match found: {price_entry.model_code} -> {base_model.model_family}")
                return base_model
            
            # Try variations of the lookup key
            variations = self._generate_lookup_key_variations(price_entry)
            
            for variation in variations:
                logger.debug(f"Trying lookup key variation: {variation}")
                base_model = await self.db_repo.get_base_model_by_lookup_key(variation)
                if base_model:
                    logger.debug(f"Match found with variation: {price_entry.model_code} -> {base_model.model_family}")
                    return base_model
            
            return None
            
        except Exception as e:
            logger.error(f"Deterministic matching failed: {e}")
            return None
    
    async def _fuzzy_match(self, price_entry: PriceEntry) -> tuple[Optional[BaseModel], Decimal]:
        """
        Perform fuzzy matching when deterministic matching fails
        
        Args:
            price_entry: PriceEntry to match
            
        Returns:
            Tuple of (BaseModel or None, confidence_score)
        """
        try:
            # Get all base models for the same brand and year
            candidates = await self.db_repo.get_base_models_by_brand_year(
                price_entry.brand, 
                price_entry.model_year
            )
            
            if not candidates:
                logger.debug(f"No base model candidates found for {price_entry.brand} {price_entry.model_year}")
                return None, Decimal("0.0")
            
            best_match = None
            best_score = Decimal("0.0")
            
            for candidate in candidates:
                score = self._calculate_similarity_score(price_entry, candidate)
                
                if score > best_score:
                    best_score = score
                    best_match = candidate
            
            if best_match:
                logger.debug(f"Fuzzy match found: {price_entry.model_code} -> {best_match.model_family} (score: {best_score})")
            
            return best_match, best_score
            
        except Exception as e:
            logger.error(f"Fuzzy matching failed: {e}")
            return None, Decimal("0.0")
    
    def _generate_lookup_key_variations(self, price_entry: PriceEntry) -> List[str]:
        """
        Generate variations of the lookup key to try
        
        Args:
            price_entry: PriceEntry to generate variations for
            
        Returns:
            List of lookup key variations
        """
        variations = []
        
        # Original key is already tried in deterministic match
        original_key = price_entry.catalog_lookup_key
        
        # Remove package if present (in case catalog doesn't have package-specific entries)
        if price_entry.paketti:
            without_package = f"{price_entry.brand}_{price_entry.malli.replace(' ', '_')}_{price_entry.model_year}"
            if without_package != original_key:
                variations.append(without_package)
        
        # Try with different casing
        variations.append(original_key.upper())
        variations.append(original_key.lower())
        
        # Try replacing underscores with spaces and vice versa
        variations.append(original_key.replace('_', ' '))
        variations.append(original_key.replace(' ', '_'))
        
        # Try without model year (in case it's implicit)
        without_year = '_'.join(original_key.split('_')[:-1])
        if without_year and without_year != original_key:
            variations.append(without_year)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for variation in variations:
            if variation not in seen and variation != original_key:
                seen.add(variation)
                unique_variations.append(variation)
        
        return unique_variations
    
    def _calculate_similarity_score(self, price_entry: PriceEntry, base_model: BaseModel) -> Decimal:
        """
        Calculate similarity score between price entry and base model
        
        Args:
            price_entry: PriceEntry to compare
            base_model: BaseModel to compare against
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        score = 0.0
        total_weight = 0.0
        
        # Model name similarity (highest weight)
        if price_entry.malli and base_model.model_family:
            model_similarity = self._text_similarity(price_entry.malli, base_model.model_family)
            score += model_similarity * 0.4
            total_weight += 0.4
        
        # Brand match (must match)
        if price_entry.brand == base_model.brand:
            score += 0.3
        else:
            return Decimal("0.0")  # Different brands can't match
        total_weight += 0.3
        
        # Year match (must match)
        if price_entry.model_year == base_model.model_year:
            score += 0.2
        else:
            return Decimal("0.0")  # Different years can't match
        total_weight += 0.2
        
        # Engine compatibility
        if price_entry.moottori and base_model.engine_options:
            engine_match = self._engine_compatibility_score(price_entry.moottori, base_model.engine_options)
            score += engine_match * 0.1
        total_weight += 0.1
        
        if total_weight > 0:
            final_score = score / total_weight
            return Decimal(str(round(final_score, 3)))
        
        return Decimal("0.0")
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity using simple string matching
        
        Args:
            text1: First text to compare
            text2: Second text to compare
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts
        t1 = text1.lower().strip()
        t2 = text2.lower().strip()
        
        # Exact match
        if t1 == t2:
            return 1.0
        
        # Substring match
        if t1 in t2 or t2 in t1:
            return 0.8
        
        # Word overlap
        words1 = set(t1.split())
        words2 = set(t2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        # Jaccard similarity
        return len(intersection) / len(union) if union else 0.0
    
    def _engine_compatibility_score(self, price_engine: str, available_engines: Dict[str, Any]) -> float:
        """
        Check if price entry engine is compatible with available engines
        
        Args:
            price_engine: Engine from price entry
            available_engines: Available engines from base model
            
        Returns:
            Compatibility score between 0.0 and 1.0
        """
        if not price_engine or not available_engines:
            return 0.0
        
        price_engine_clean = price_engine.lower().strip()
        
        for engine_key, engine_data in available_engines.items():
            if isinstance(engine_data, dict):
                # Check full name
                if 'full_name' in engine_data:
                    if price_engine_clean in engine_data['full_name'].lower():
                        return 1.0
                
                # Check displacement and type
                if 'displacement' in engine_data and 'type' in engine_data:
                    engine_desc = f"{engine_data['displacement']} {engine_data['type']}".lower()
                    if engine_desc in price_engine_clean or price_engine_clean in engine_desc:
                        return 1.0
            
            # Check engine key itself
            if price_engine_clean.replace(' ', '_').upper() in engine_key.upper():
                return 1.0
        
        return 0.0
    
    async def get_matching_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about matching performance
        
        Returns:
            Dictionary with matching statistics
        """
        try:
            total_entries = await self.db_repo.count_price_entries()
            matched_entries = await self.db_repo.count_matched_price_entries()
            unmatched_entries = await self.db_repo.count_unmatched_price_entries()
            
            match_rate = (matched_entries / total_entries * 100) if total_entries > 0 else 0.0
            
            # Get match method breakdown
            match_methods = await self.db_repo.get_match_method_statistics()
            
            return {
                'total_price_entries': total_entries,
                'matched_entries': matched_entries,
                'unmatched_entries': unmatched_entries,
                'match_rate_percentage': round(match_rate, 2),
                'match_methods': match_methods,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get matching statistics: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }