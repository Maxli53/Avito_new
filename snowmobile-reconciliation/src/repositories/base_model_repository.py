"""
Base Model Repository for accessing catalog base models from database.

FIXED: Now queries BaseModelTable instead of hardcoded catalog data.
Provides structured access to snowmobile base model specifications
with intelligent matching capabilities.
"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import structlog

from src.models.domain import BaseModelSpecification
from src.models.database import BaseModelTable

logger = structlog.get_logger(__name__)


class BaseModelRepository:
    """
    Repository for base model specifications from manufacturer catalogs.
    
    FIXED: Now queries database instead of hardcoded data.
    Provides high-performance lookup and matching capabilities for
    snowmobile base models across multiple brands and years.
    """
    
    def __init__(self, session: Session):
        """Initialize with database session"""
        self.session = session
        self.logger = logger.bind(component="BaseModelRepository")
    
    def _convert_to_domain_model(self, db_model: BaseModelTable) -> BaseModelSpecification:
        """Convert database model to domain model"""
        try:
            return BaseModelSpecification(
                base_model_id=db_model.base_model_id,
                model_name=db_model.model_name,
                brand=db_model.brand,
                model_year=db_model.model_year,
                category=db_model.category,
                
                # JSONB fields with complete specifications
                engine_specs=db_model.engine_specs or {},
                dimensions=db_model.dimensions or {},
                suspension=db_model.suspension or {},
                features=db_model.features or {},
                available_colors=db_model.available_colors or [],
                track_options=db_model.track_options or [],
                
                source_catalog=db_model.source_catalog or "",
                extraction_quality=float(db_model.extraction_quality or 0.0),
                inheritance_confidence=0.9  # Default confidence
            )
        except Exception as e:
            self.logger.error("Failed to convert database model", error=str(e))
            raise

    async def find_by_id(self, model_id: str) -> Optional[BaseModelSpecification]:
        """Find base model by exact ID from database"""
        try:
            db_model = self.session.query(BaseModelTable).filter(
                BaseModelTable.base_model_id == model_id
            ).first()
            
            if db_model:
                self.logger.info("Base model found by ID", model_id=model_id)
                return self._convert_to_domain_model(db_model)
            
            self.logger.info("Base model not found by ID", model_id=model_id)
            return None
            
        except SQLAlchemyError as e:
            self.logger.error("Database error finding by ID", model_id=model_id, error=str(e))
            return None

    async def find_by_brand_and_name(
        self, brand: str, model_name: str, year: Optional[int] = None
    ) -> Optional[BaseModelSpecification]:
        """Find base model by brand and model name from database"""
        try:
            query = self.session.query(BaseModelTable).filter(
                BaseModelTable.brand.ilike(f"%{brand}%"),
                BaseModelTable.model_name.ilike(f"%{model_name}%")
            )
            
            if year:
                query = query.filter(BaseModelTable.model_year == year)
                
            db_model = query.order_by(BaseModelTable.model_year.desc()).first()
            
            if db_model:
                self.logger.info("Base model found by brand/name", brand=brand, model_name=model_name)
                return self._convert_to_domain_model(db_model)
            
            self.logger.info("Base model not found by brand/name", brand=brand, model_name=model_name)
            return None
            
        except SQLAlchemyError as e:
            self.logger.error("Database error finding by brand/name", brand=brand, model_name=model_name, error=str(e))
            return None

    async def find_matching_base_models(
        self, search_criteria: dict, similarity_threshold: float = 0.8
    ) -> List[BaseModelSpecification]:
        """Find base models matching search criteria with similarity scoring"""
        try:
            query = self.session.query(BaseModelTable)
            
            # Apply exact filters
            if search_criteria.get("brand"):
                query = query.filter(BaseModelTable.brand.ilike(f"%{search_criteria['brand']}%"))
            if search_criteria.get("model_year"):
                query = query.filter(BaseModelTable.model_year == search_criteria["model_year"])
            if search_criteria.get("base_model_id"):
                query = query.filter(BaseModelTable.base_model_id.ilike(f"%{search_criteria['base_model_id']}%"))
                
            # Handle base_model_pattern from pipeline
            if search_criteria.get("base_model_pattern"):
                pattern = search_criteria["base_model_pattern"]
                query = query.filter(
                    BaseModelTable.base_model_id.ilike(f"%{pattern}%") |
                    BaseModelTable.model_name.ilike(f"%{pattern}%")
                )
            
            db_models = query.order_by(
                BaseModelTable.brand,
                BaseModelTable.model_name,
                BaseModelTable.model_year.desc()
            ).all()
            
            domain_models = [self._convert_to_domain_model(db_model) for db_model in db_models]
            
            self.logger.info("Found matching base models", criteria=search_criteria, count=len(domain_models))
            return domain_models
            
        except Exception as e:
            self.logger.error("Database error finding matching base models", criteria=search_criteria, error=str(e))
            return []

    async def get_all_base_models(self, brand: Optional[str] = None, year: Optional[int] = None) -> List[BaseModelSpecification]:
        """Get all base models from database"""
        try:
            query = self.session.query(BaseModelTable)
            
            if brand:
                query = query.filter(BaseModelTable.brand == brand)
            if year:
                query = query.filter(BaseModelTable.model_year == year)
                
            db_models = query.order_by(
                BaseModelTable.brand,
                BaseModelTable.model_name,
                BaseModelTable.model_year.desc()
            ).all()
            
            domain_models = [self._convert_to_domain_model(db_model) for db_model in db_models]
            
            self.logger.info("Retrieved base models from database", count=len(domain_models))
            return domain_models
            
        except SQLAlchemyError as e:
            self.logger.error("Database error getting base models", error=str(e))
            return []

    async def search_by_brand(self, brand: str) -> List[BaseModelSpecification]:
        """Get all models for a specific brand from database"""
        try:
            db_models = self.session.query(BaseModelTable).filter(
                BaseModelTable.brand.ilike(f"%{brand}%")
            ).order_by(
                BaseModelTable.model_name,
                BaseModelTable.model_year.desc()
            ).all()
            
            domain_models = [self._convert_to_domain_model(db_model) for db_model in db_models]
            
            self.logger.info("Found models by brand", brand=brand, count=len(domain_models))
            return domain_models
            
        except SQLAlchemyError as e:
            self.logger.error("Database error searching by brand", brand=brand, error=str(e))
            return []

    async def search_by_year(self, year: int) -> List[BaseModelSpecification]:
        """Get all models for a specific year from database"""
        try:
            db_models = self.session.query(BaseModelTable).filter(
                BaseModelTable.model_year == year
            ).order_by(
                BaseModelTable.brand,
                BaseModelTable.model_name
            ).all()
            
            domain_models = [self._convert_to_domain_model(db_model) for db_model in db_models]
            
            self.logger.info("Found models by year", year=year, count=len(domain_models))
            return domain_models
            
        except SQLAlchemyError as e:
            self.logger.error("Database error searching by year", year=year, error=str(e))
            return []

    async def get_model_count(self) -> int:
        """Get total number of base models in database"""
        try:
            count = self.session.query(BaseModelTable).count()
            self.logger.info("Retrieved model count from database", count=count)
            return count
        except SQLAlchemyError as e:
            self.logger.error("Database error getting model count", error=str(e))
            return 0

    async def get_brands(self) -> List[str]:
        """Get list of all available brands from database"""
        try:
            brands = self.session.query(BaseModelTable.brand).distinct().all()
            brand_list = [brand[0] for brand in brands]
            self.logger.info("Retrieved brands from database", brands=brand_list)
            return brand_list
        except SQLAlchemyError as e:
            self.logger.error("Database error getting brands", error=str(e))
            return []

    async def get_years(self) -> List[int]:
        """Get list of all available model years from database"""
        try:
            years = self.session.query(BaseModelTable.model_year).distinct().order_by(BaseModelTable.model_year.desc()).all()
            year_list = [year[0] for year in years]
            self.logger.info("Retrieved years from database", years=year_list)
            return year_list
        except SQLAlchemyError as e:
            self.logger.error("Database error getting years", error=str(e))
            return []

    async def create_base_model(self, specification: BaseModelSpecification) -> BaseModelSpecification:
        """Create new base model in database"""
        try:
            db_model = BaseModelTable(
                base_model_id=specification.base_model_id,
                model_name=specification.model_name,
                brand=specification.brand,
                model_year=specification.model_year,
                category=specification.category,
                engine_specs=specification.engine_specs,
                dimensions=specification.dimensions,
                suspension=specification.suspension,
                features=specification.features,
                available_colors=specification.available_colors,
                track_options=specification.track_options,
                source_catalog=specification.source_catalog,
                extraction_quality=specification.extraction_quality
            )
            
            self.session.add(db_model)
            self.session.flush()  # Get ID without committing
            
            created_model = self._convert_to_domain_model(db_model)
            
            self.logger.info("Created base model in database", model_id=specification.base_model_id)
            return created_model
            
        except SQLAlchemyError as e:
            self.session.rollback()
            self.logger.error("Database error creating base model", model_id=specification.base_model_id, error=str(e))
            raise

    async def update_base_model(self, model_id: str, updates: dict) -> Optional[BaseModelSpecification]:
        """Update existing base model in database"""
        try:
            db_model = self.session.query(BaseModelTable).filter(
                BaseModelTable.base_model_id == model_id
            ).first()
            
            if not db_model:
                self.logger.warning("Base model not found for update", model_id=model_id)
                return None
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(db_model, key):
                    setattr(db_model, key, value)
            
            self.session.flush()
            updated_model = self._convert_to_domain_model(db_model)
            
            self.logger.info("Updated base model in database", model_id=model_id)
            return updated_model
            
        except SQLAlchemyError as e:
            self.session.rollback()
            self.logger.error("Database error updating base model", model_id=model_id, error=str(e))
            raise