"""
Product repository for database operations.

Implements repository pattern with proper error handling and type safety.
Follows Universal Development Standards.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import AuditTrailTable, BaseModelTable, ProductTable
from src.models.domain import (
    BaseModelSpecification,
    ConfidenceLevel,
    ProcessingStage,
    ProductSpecification,
)
from src.repositories.base import BaseRepository, RepositoryError

logger = structlog.get_logger(__name__)


class ProductRepository(BaseRepository[ProductSpecification]):
    """Repository for product data operations with full audit trail support"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProductTable, ProductSpecification)
        self.logger = logger.bind(repository="product")

    async def create_product(
        self, product: ProductSpecification, audit_user: str = "system"
    ) -> ProductSpecification:
        """
        Create new product with full audit trail.

        Args:
            product: Product specification to create
            audit_user: User/system creating the product

        Returns:
            Created product with database ID

        Raises:
            RepositoryError: If creation fails
        """
        try:
            self.logger.info(
                "Creating product",
                model_code=product.model_code,
                base_model_id=product.base_model_id,
            )

            # Convert Pydantic model to database record
            db_product = ProductTable(
                id=product.product_id,
                model_code=product.model_code,
                base_model_id=product.base_model_id,
                brand=product.brand,
                model_name=product.model_name,
                model_year=product.model_year,
                price=product.price,
                currency=product.currency,
                specifications=product.specifications,
                spring_options=[opt.dict() for opt in product.spring_options],
                pipeline_results=[result.dict() for result in product.pipeline_results],
                overall_confidence=product.overall_confidence,
                confidence_level=product.confidence_level,
                created_at=product.created_at,
                processed_by=product.processed_by,
            )

            self.session.add(db_product)
            await self.session.flush()  # Get the ID without committing

            # Create audit trail entry
            await self._create_audit_entry(
                product_id=db_product.id,
                stage=ProcessingStage.FINAL_VALIDATION,
                action="product_created",
                after_data=product.dict(),
                user_id=audit_user,
            )

            await self.session.commit()

            self.logger.info(
                "Product created successfully",
                product_id=db_product.id,
                model_code=product.model_code,
            )

            return await self.get_by_id(db_product.id)

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to create product", model_code=product.model_code, error=str(e)
            )
            raise RepositoryError(f"Failed to create product: {e}") from e

    async def get_by_model_code(
        self, model_code: str, model_year: Optional[int] = None
    ) -> Optional[ProductSpecification]:
        """
        Get product by model code and optionally model year.

        Args:
            model_code: Model code to search for
            model_year: Optional model year filter

        Returns:
            Product specification if found, None otherwise
        """
        try:
            query = select(ProductTable).where(
                ProductTable.model_code == model_code.upper()
            )

            if model_year:
                query = query.where(ProductTable.model_year == model_year)

            # Get most recent if multiple matches
            query = query.order_by(desc(ProductTable.created_at))

            result = await self.session.execute(query)
            db_product = result.scalar_one_or_none()

            if db_product is None:
                return None

            return self._to_domain_model(db_product)

        except Exception as e:
            self.logger.error(
                "Failed to get product by model code",
                model_code=model_code,
                model_year=model_year,
                error=str(e),
            )
            raise RepositoryError(f"Failed to get product: {e}") from e

    async def update_confidence_score(
        self,
        product_id: UUID,
        new_confidence: float,
        stage: ProcessingStage,
        audit_user: str = "system",
    ) -> ProductSpecification:
        """
        Update product confidence score with audit trail.

        Args:
            product_id: Product ID to update
            new_confidence: New confidence score
            stage: Pipeline stage making the update
            audit_user: User/system making the update

        Returns:
            Updated product specification

        Raises:
            RepositoryError: If update fails
        """
        try:
            # Get current product
            current_product = await self.get_by_id(product_id)
            if not current_product:
                raise RepositoryError(f"Product not found: {product_id}")

            old_confidence = current_product.overall_confidence

            # Update confidence and derived confidence level
            from src.models.domain import ConfidenceLevel

            if new_confidence >= 0.9:
                confidence_level = ConfidenceLevel.HIGH
            elif new_confidence >= 0.7:
                confidence_level = ConfidenceLevel.MEDIUM
            else:
                confidence_level = ConfidenceLevel.LOW

            # Update in database
            query = (
                ProductTable.__table__.update()
                .where(ProductTable.id == product_id)
                .values(
                    overall_confidence=new_confidence,
                    confidence_level=confidence_level,
                    updated_at=datetime.utcnow(),
                )
            )

            await self.session.execute(query)

            # Create audit trail
            await self._create_audit_entry(
                product_id=product_id,
                stage=stage,
                action="confidence_updated",
                before_data={"confidence": old_confidence},
                after_data={"confidence": new_confidence},
                confidence_change=new_confidence - old_confidence,
                user_id=audit_user,
            )

            await self.session.commit()

            return await self.get_by_id(product_id)

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to update confidence score",
                product_id=product_id,
                new_confidence=new_confidence,
                error=str(e),
            )
            raise RepositoryError(f"Failed to update confidence: {e}") from e

    async def get_products_by_confidence(
        self, confidence_level: ConfidenceLevel, limit: int = 100, offset: int = 0
    ) -> list[ProductSpecification]:
        """
        Get products by confidence level for review workflows.

        Args:
            confidence_level: Confidence level to filter by
            limit: Maximum number of products to return
            offset: Number of products to skip

        Returns:
            List of products matching confidence level
        """
        try:
            query = (
                select(ProductTable)
                .where(ProductTable.confidence_level == confidence_level)
                .order_by(desc(ProductTable.created_at))
                .limit(limit)
                .offset(offset)
            )

            result = await self.session.execute(query)
            db_products = result.scalars().all()

            return [self._to_domain_model(db_product) for db_product in db_products]

        except Exception as e:
            self.logger.error(
                "Failed to get products by confidence",
                confidence_level=confidence_level,
                error=str(e),
            )
            raise RepositoryError(f"Failed to get products: {e}") from e

    async def get_processing_statistics(self) -> dict[str, int]:
        """
        Get processing statistics for monitoring dashboard.

        Returns:
            Dictionary with processing counts by confidence level
        """
        try:
            query = select(
                ProductTable.confidence_level,
                func.count(ProductTable.id).label("count"),
            ).group_by(ProductTable.confidence_level)

            result = await self.session.execute(query)
            rows = result.all()

            stats = {
                "total": 0,
                "high_confidence": 0,
                "medium_confidence": 0,
                "low_confidence": 0,
            }

            for row in rows:
                stats["total"] += row.count

                if row.confidence_level == ConfidenceLevel.HIGH:
                    stats["high_confidence"] = row.count
                elif row.confidence_level == ConfidenceLevel.MEDIUM:
                    stats["medium_confidence"] = row.count
                elif row.confidence_level == ConfidenceLevel.LOW:
                    stats["low_confidence"] = row.count

            return stats

        except Exception as e:
            self.logger.error("Failed to get processing statistics", error=str(e))
            raise RepositoryError(f"Failed to get statistics: {e}") from e

    async def search_products(
        self,
        search_term: str,
        filters: Optional[dict[str, any]] = None,
        limit: int = 50,
    ) -> list[ProductSpecification]:
        """
        Search products with full-text search and filters.

        Args:
            search_term: Text to search in model names and codes
            filters: Additional filters (brand, model_year, etc.)
            limit: Maximum results to return

        Returns:
            List of matching products
        """
        try:
            # Build search query with PostgreSQL full-text search
            query = select(ProductTable)

            if search_term.strip():
                search_vector = func.to_tsvector(
                    "english", ProductTable.model_name + " " + ProductTable.model_code
                )
                search_query = func.plainto_tsquery("english", search_term)

                query = query.where(search_vector.match(search_query))

            # Apply filters
            if filters:
                if filters.get("brand"):
                    query = query.where(ProductTable.brand == filters["brand"])
                if filters.get("model_year"):
                    query = query.where(
                        ProductTable.model_year == filters["model_year"]
                    )
                if filters.get("confidence_level"):
                    query = query.where(
                        ProductTable.confidence_level == filters["confidence_level"]
                    )

            query = query.limit(limit).order_by(desc(ProductTable.overall_confidence))

            result = await self.session.execute(query)
            db_products = result.scalars().all()

            return [self._to_domain_model(db_product) for db_product in db_products]

        except Exception as e:
            self.logger.error(
                "Failed to search products", search_term=search_term, error=str(e)
            )
            raise RepositoryError(f"Failed to search products: {e}") from e

    async def _create_audit_entry(
        self,
        product_id: UUID,
        stage: ProcessingStage,
        action: str,
        before_data: Optional[dict] = None,
        after_data: Optional[dict] = None,
        confidence_change: Optional[float] = None,
        user_id: str = "system",
    ) -> None:
        """Create audit trail entry for transparency"""
        try:
            audit_entry = AuditTrailTable(
                product_id=product_id,
                stage=stage,
                action=action,
                before_data=before_data,
                after_data=after_data,
                confidence_change=confidence_change,
                timestamp=datetime.utcnow(),
                processing_node="main",  # Will be extracted from config when settings are fully connected
                user_id=user_id,
            )

            self.session.add(audit_entry)

        except Exception as e:
            self.logger.error(
                "Failed to create audit entry",
                product_id=product_id,
                stage=stage,
                action=action,
                error=str(e),
            )
            # Don't raise - audit failure shouldn't break main operation

    def _to_domain_model(self, db_product: ProductTable) -> ProductSpecification:
        """Convert database model to domain model"""
        from src.models.domain import PipelineStageResult, SpringOption

        return ProductSpecification(
            product_id=db_product.id,
            model_code=db_product.model_code,
            base_model_id=db_product.base_model_id,
            brand=db_product.brand,
            model_name=db_product.model_name,
            model_year=db_product.model_year,
            price=db_product.price,
            currency=db_product.currency,
            specifications=db_product.specifications or {},
            spring_options=[
                SpringOption(**opt) for opt in (db_product.spring_options or [])
            ],
            pipeline_results=[
                PipelineStageResult(**result)
                for result in (db_product.pipeline_results or [])
            ],
            overall_confidence=db_product.overall_confidence,
            confidence_level=db_product.confidence_level,
            created_at=db_product.created_at,
            processed_by=db_product.processed_by or "system",
        )



