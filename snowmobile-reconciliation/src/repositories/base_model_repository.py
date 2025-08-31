"""
Base Model Repository for accessing catalog base models.

Provides structured access to snowmobile base model specifications
with intelligent matching capabilities.
"""
from decimal import Decimal
from typing import Dict, List, Optional

from src.models.domain import BaseModelSpecification
class BaseModelRepository:
    """
    Repository for base model specifications from manufacturer catalogs.
    
    Provides high-performance lookup and matching capabilities for
    snowmobile base models across multiple brands and years.
    """
    
    def __init__(self):
        """Initialize with sample base model catalog"""
        self._base_models = self._initialize_catalog()
        self._brand_index = self._build_brand_index()
        self._year_index = self._build_year_index()
    
    def _initialize_catalog(self) -> Dict[str, BaseModelSpecification]:
        """Initialize with comprehensive base model catalog"""
        return {
            "MXZ_TRAIL_600": BaseModelSpecification(
                base_model_id="MXZ_TRAIL_600",
                model_name="MXZ Trail 600",
                brand="Ski-Doo",
                model_year=2024,
                category="Trail",
                source_catalog="catalog_2024.pdf",
                extraction_quality=0.9,
                engine_specs={"type": "2-stroke", "displacement": "600cc"},
                suspension={"type": "tMotion"},
                dimensions={"track_length": "137", "track_width": "15"},
                features={
                    "cooling": "liquid",
                    "reverse": False,
                    "heated_grips": False,
                    "starter": "electric",
                },
                inheritance_confidence=0.85,
            ),
            "RENEGADE_850": BaseModelSpecification(
                base_model_id="RENEGADE_850",
                model_name="Renegade 850",
                brand="Ski-Doo",
                model_year=2024,
                category="Crossover",
                source_catalog="catalog_2024.pdf",
                extraction_quality=0.95,
                engine_specs={"type": "2-stroke", "displacement": "850cc"},
                suspension={"type": "RAS 3"},
                dimensions={"track_length": "137", "track_width": "16"},
                features={
                    "cooling": "liquid",
                    "reverse": "electric",
                    "heated_grips": True,
                    "starter": "electric",
                    "fuel_injection": True,
                },
                inheritance_confidence=0.9,
            ),
            "SUMMIT_850": BaseModelSpecification(
                base_model_id="SUMMIT_850",
                model_name="Summit 850",
                brand="Ski-Doo",
                model_year=2024,
                category="Mountain",
                source_catalog="catalog_2024.pdf",
                extraction_quality=0.92,
                engine_specs={"type": "2-stroke", "displacement": "850cc"},
                suspension={"type": "tMotion"},
                dimensions={"track_length": "165", "track_width": "16"},
                features={
                    "cooling": "liquid",
                    "reverse": "electric",
                    "heated_grips": True,
                    "starter": "electric",
                    "mountain_package": True,
                },
                inheritance_confidence=0.88,
            ),
            "ASSAULT_800": BaseModelSpecification(
                base_model_id="ASSAULT_800",
                model_name="Assault 800",
                brand="Polaris",
                model_year=2024,
                category="Mountain",
                source_catalog="catalog_2024.pdf",
                extraction_quality=0.88,
                engine_specs={"type": "2-stroke", "displacement": "800cc"},
                suspension={"type": "Pro-Ride"},
                dimensions={"track_length": "155", "track_width": "15"},
                features={
                    "cooling": "liquid",
                    "reverse": False,
                    "heated_grips": False,
                    "starter": "electric",
                },
                inheritance_confidence=0.87,
            ),
            "SWITCHBACK_600": BaseModelSpecification(
                base_model_id="SWITCHBACK_600",
                model_name="Switchback 600",
                brand="Polaris",
                model_year=2024,
                category="Trail",
                source_catalog="catalog_2024.pdf",
                extraction_quality=0.85,
                engine_specs={"type": "2-stroke", "displacement": "600cc"},
                suspension={"type": "Pro-Ride"},
                dimensions={"track_length": "137", "track_width": "15"},
                features={
                    "cooling": "liquid",
                    "reverse": False,
                    "heated_grips": False,
                    "starter": "electric",
                },
                inheritance_confidence=0.82,
            ),
            "RMKASSAULT_850": BaseModelSpecification(
                base_model_id="RMKASSAULT_850",
                model_name="RMK Assault 850",
                brand="Polaris",
                model_year=2024,
                category="Mountain",
                source_catalog="catalog_2024.pdf",
                extraction_quality=0.9,
                engine_specs={"type": "2-stroke", "displacement": "850cc"},
                suspension={"type": "Pro-Ride"},
                dimensions={"track_length": "165", "track_width": "16"},
                features={
                    "cooling": "liquid",
                    "reverse": "electric",
                    "heated_grips": True,
                    "starter": "electric",
                    "mountain_package": True,
                },
                inheritance_confidence=0.89,
            ),
            "CATALYST_600": BaseModelSpecification(
                base_model_id="CATALYST_600",
                model_name="Catalyst 600",
                brand="Arctic Cat",
                model_year=2024,
                category="Trail",
                source_catalog="catalog_2024.pdf",
                extraction_quality=0.86,
                engine_specs={"type": "2-stroke", "displacement": "600cc"},
                suspension={"type": "ALPHA ONE"},
                dimensions={"track_length": "137", "track_width": "15"},
                features={
                    "cooling": "liquid",
                    "reverse": False,
                    "heated_grips": False,
                    "starter": "electric",
                },
                inheritance_confidence=0.83,
            ),
            "MOUNTAIN_CAT_800": BaseModelSpecification(
                base_model_id="MOUNTAIN_CAT_800",
                model_name="Mountain Cat 800",
                brand="Arctic Cat",
                model_year=2024,
                category="Mountain",
                source_catalog="catalog_2024.pdf",
                extraction_quality=0.89,
                engine_specs={"type": "2-stroke", "displacement": "800cc"},
                suspension={"type": "ALPHA ONE"},
                dimensions={"track_length": "162", "track_width": "16"},
                features={
                    "cooling": "liquid",
                    "reverse": "electric",
                    "heated_grips": True,
                    "starter": "electric",
                    "mountain_package": True,
                },
                inheritance_confidence=0.87,
            ),
            "SRX_1200": BaseModelSpecification(
                base_model_id="SRX_1200",
                model_name="SRX 1200",
                brand="Yamaha",
                model_year=2024,
                category="Performance",
                source_catalog="catalog_2024.pdf",
                extraction_quality=0.93,
                engine_specs={"type": "4-stroke", "displacement": "1200cc"},
                suspension={"type": "KYB"},
                dimensions={"track_length": "137", "track_width": "15"},
                features={
                    "cooling": "liquid",
                    "reverse": "electric",
                    "heated_grips": True,
                    "starter": "electric",
                    "turbo": True,
                },
                inheritance_confidence=0.91,
            ),
            "MOUNTAIN_MAX_800": BaseModelSpecification(
                base_model_id="MOUNTAIN_MAX_800",
                model_name="Mountain Max 800",
                brand="Yamaha",
                model_year=2024,
                category="Mountain",
                source_catalog="catalog_2024.pdf",
                extraction_quality=0.87,
                engine_specs={"type": "2-stroke", "displacement": "800cc"},
                suspension={"type": "KYB"},
                dimensions={"track_length": "162", "track_width": "16"},
                features={
                    "cooling": "liquid",
                    "reverse": "electric",
                    "heated_grips": True,
                    "starter": "electric",
                    "mountain_package": True,
                },
                inheritance_confidence=0.85,
            ),
        }
    
    def _build_brand_index(self) -> Dict[str, List[str]]:
        """Build brand-based index for fast lookups"""
        index = {}
        for model_id, model in self._base_models.items():
            brand = model.brand.upper()
            if brand not in index:
                index[brand] = []
            index[brand].append(model_id)
        return index
    
    def _build_year_index(self) -> Dict[int, List[str]]:
        """Build year-based index for fast lookups"""
        index = {}
        for model_id, model in self._base_models.items():
            year = model.model_year
            if year not in index:
                index[year] = []
            index[year].append(model_id)
        return index
    
    async def find_by_id(self, model_id: str) -> Optional[BaseModelSpecification]:
        """Find base model by exact ID"""
        return self._base_models.get(model_id)
    
    async def find_by_brand_and_year(
        self,
        brand: str,
        model_year: int
    ) -> List[BaseModelSpecification]:
        """Find all base models for a specific brand and year"""
        brand_key = brand.upper()
        if brand_key not in self._brand_index:
            return []
        
        brand_models = self._brand_index[brand_key]
        year_models = self._year_index.get(model_year, [])
        
        # Intersection of brand and year
        matching_ids = set(brand_models) & set(year_models)
        
        return [self._base_models[model_id] for model_id in matching_ids]
    
    async def find_best_match(
        self,
        brand: str,
        model_code: str,
        model_year: int,
        price: Optional[Decimal] = None
    ) -> Optional[BaseModelSpecification]:
        """
        Find the best matching base model using intelligent matching.
        
        Uses brand, model code patterns, year, and price to find
        the most appropriate base model.
        """
        # Get candidates by brand and year
        candidates = await self.find_by_brand_and_year(brand, model_year)
        
        if not candidates:
            return None
        
        # Score each candidate
        scored_candidates = []
        
        for candidate in candidates:
            score = self._calculate_match_score(
                candidate, model_code, price
            )
            scored_candidates.append((score, candidate))
        
        # Return highest scoring candidate
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        
        # Only return if score is above threshold
        if scored_candidates[0][0] > 0.5:
            return scored_candidates[0][1]
        
        return None
    
    def _calculate_match_score(
        self,
        candidate: BaseModelSpecification,
        model_code: str,
        price: Optional[Decimal] = None
    ) -> float:
        """Calculate match score between candidate and search criteria"""
        score = 0.0
        model_code_upper = model_code.upper()
        
        # Model name similarity (40% weight)
        if candidate.model_name.upper().replace(" ", "") in model_code_upper:
            score += 0.4
        elif any(word in model_code_upper for word in candidate.model_name.upper().split()):
            score += 0.2
        
        # Engine displacement matching (30% weight)
        engine_spec = candidate.engine_specs
        if isinstance(engine_spec, dict) and "displacement" in engine_spec:
            displacement = engine_spec["displacement"]
            if displacement in model_code_upper:
                score += 0.3
        
        # Category/type matching (20% weight)
        category_keywords = {
            "Trail": ["TRAIL", "MXZ", "SWITCHBACK", "CATALYST"],
            "Mountain": ["SUMMIT", "ASSAULT", "RMK", "MOUNTAIN"],
            "Crossover": ["RENEGADE", "CROSSOVER"],
            "Performance": ["SRX", "TURBO", "PERFORMANCE"]
        }
        
        category_matches = category_keywords.get(candidate.category, [])
        if any(keyword in model_code_upper for keyword in category_matches):
            score += 0.2
        
        # Price range matching (10% weight) - if price provided
        if price:
            expected_price_ranges = {
                "Trail": (10000, 16000),
                "Mountain": (15000, 22000),
                "Crossover": (16000, 25000),
                "Performance": (18000, 30000)
            }
            
            min_price, max_price = expected_price_ranges.get(candidate.category, (0, 100000))
            if min_price <= float(price) <= max_price:
                score += 0.1
        
        return score
    
    async def find_by_category(self, category: str) -> List[BaseModelSpecification]:
        """Find all base models in a specific category"""
        return [
            model for model in self._base_models.values()
            if model.category.upper() == category.upper()
        ]
    
    async def get_all(self) -> List[BaseModelSpecification]:
        """Get all base models in the catalog"""
        return list(self._base_models.values())
    
    async def save(self, entity: BaseModelSpecification) -> BaseModelSpecification:
        """Save a base model to the catalog"""
        self._base_models[entity.base_model_id] = entity
        # Rebuild indices
        self._brand_index = self._build_brand_index()
        self._year_index = self._build_year_index()
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete a base model from the catalog"""
        if entity_id in self._base_models:
            del self._base_models[entity_id]
            # Rebuild indices
            self._brand_index = self._build_brand_index()
            self._year_index = self._build_year_index()
            return True
        return False


# Export
__all__ = ["BaseModelRepository"]