"""
Base repository pattern implementation following Universal Development Standards.

Provides common database operations with proper error handling and type safety.
"""
from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, TypeVar
from uuid import UUID

import structlog
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

logger = structlog.get_logger(__name__)

# Type variables for generic repository
ModelType = TypeVar("ModelType", bound=BaseModel)
TableType = TypeVar("TableType", bound=DeclarativeBase)


class RepositoryError(Exception):
    """Base exception for repository operations"""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class BaseRepository(Generic[ModelType], ABC):
    """
    Abstract base repository providing common database operations.

    Implements repository pattern with:
    - Type safety with generics
    - Proper error handling
    - Structured logging
    - Consistent interface
    """

    def __init__(
        self,
        session: AsyncSession,
        table_class: type[TableType],
        model_class: type[ModelType],
    ) -> None:
        self.session = session
        self.table_class = table_class
        self.model_class = model_class
        self.logger = logger.bind(
            repository=self.__class__.__name__, table=table_class.__name__
        )

    async def get_by_id(self, entity_id: UUID) -> Optional[ModelType]:
        """
        Get entity by ID.

        Args:
            entity_id: Primary key to search for

        Returns:
            Domain model if found, None otherwise

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            query = select(self.table_class).where(self.table_class.id == entity_id)
            result = await self.session.execute(query)
            db_entity = result.scalar_one_or_none()

            if db_entity is None:
                return None

            return self._to_domain_model(db_entity)

        except Exception as e:
            self.logger.error(
                "Failed to get entity by ID", entity_id=entity_id, error=str(e)
            )
            raise RepositoryError(f"Failed to get entity by ID: {e}") from e

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[ModelType]:
        """
        List entities with pagination and optional filters.

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip
            filters: Optional filters to apply

        Returns:
            List of domain models

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            query = select(self.table_class)

            # Apply filters if provided
            if filters:
                query = self._apply_filters(query, filters)

            query = query.limit(limit).offset(offset)

            result = await self.session.execute(query)
            db_entities = result.scalars().all()

            return [self._to_domain_model(entity) for entity in db_entities]

        except Exception as e:
            self.logger.error(
                "Failed to list entities",
                limit=limit,
                offset=offset,
                filters=filters,
                error=str(e),
            )
            raise RepositoryError(f"Failed to list entities: {e}") from e

    async def create(self, entity: ModelType) -> ModelType:
        """
        Create new entity.

        Args:
            entity: Domain model to create

        Returns:
            Created domain model with database ID

        Raises:
            RepositoryError: If creation fails
        """
        try:
            db_entity = self._to_database_model(entity)
            self.session.add(db_entity)
            await self.session.flush()

            return self._to_domain_model(db_entity)

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to create entity",
                entity_type=type(entity).__name__,
                error=str(e),
            )
            raise RepositoryError(f"Failed to create entity: {e}") from e

    async def update(
        self, entity_id: UUID, updates: dict[str, Any]
    ) -> Optional[ModelType]:
        """
        Update entity by ID.

        Args:
            entity_id: ID of entity to update
            updates: Dictionary of fields to update

        Returns:
            Updated domain model if found, None otherwise

        Raises:
            RepositoryError: If update fails
        """
        try:
            # Get existing entity
            query = select(self.table_class).where(self.table_class.id == entity_id)
            result = await self.session.execute(query)
            db_entity = result.scalar_one_or_none()

            if db_entity is None:
                return None

            # Apply updates
            for field, value in updates.items():
                if hasattr(db_entity, field):
                    setattr(db_entity, field, value)

            await self.session.flush()

            return self._to_domain_model(db_entity)

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to update entity",
                entity_id=entity_id,
                updates=updates,
                error=str(e),
            )
            raise RepositoryError(f"Failed to update entity: {e}") from e

    async def delete(self, entity_id: UUID) -> bool:
        """
        Delete entity by ID.

        Args:
            entity_id: ID of entity to delete

        Returns:
            True if entity was deleted, False if not found

        Raises:
            RepositoryError: If deletion fails
        """
        try:
            query = select(self.table_class).where(self.table_class.id == entity_id)
            result = await self.session.execute(query)
            db_entity = result.scalar_one_or_none()

            if db_entity is None:
                return False

            await self.session.delete(db_entity)
            await self.session.flush()

            return True

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to delete entity", entity_id=entity_id, error=str(e)
            )
            raise RepositoryError(f"Failed to delete entity: {e}") from e

    async def count(self, filters: Optional[dict[str, Any]] = None) -> int:
        """
        Count entities with optional filters.

        Args:
            filters: Optional filters to apply

        Returns:
            Number of matching entities

        Raises:
            RepositoryError: If count operation fails
        """
        try:
            from sqlalchemy import func

            query = select(func.count(self.table_class.id))

            if filters:
                query = self._apply_filters(query, filters)

            result = await self.session.execute(query)
            count = result.scalar()

            return count or 0

        except Exception as e:
            self.logger.error("Failed to count entities", filters=filters, error=str(e))
            raise RepositoryError(f"Failed to count entities: {e}") from e

    async def exists(self, entity_id: UUID) -> bool:
        """
        Check if entity exists by ID.

        Args:
            entity_id: ID to check

        Returns:
            True if entity exists, False otherwise
        """
        try:
            entity = await self.get_by_id(entity_id)
            return entity is not None
        except RepositoryError:
            return False

    def _apply_filters(self, query: Any, filters: dict[str, Any]) -> Any:
        """
        Apply filters to query. Override in subclasses for custom filtering.

        Args:
            query: SQLAlchemy query object
            filters: Filters to apply

        Returns:
            Modified query object
        """
        # Default implementation - subclasses should override
        for field, value in filters.items():
            if hasattr(self.table_class, field):
                query = query.where(getattr(self.table_class, field) == value)

        return query

    @abstractmethod
    def _to_domain_model(self, db_entity: TableType) -> ModelType:
        """
        Convert database entity to domain model.
        Must be implemented by concrete repositories.

        Args:
            db_entity: Database entity

        Returns:
            Domain model
        """
        pass

    def _to_database_model(self, domain_entity: ModelType) -> TableType:
        """
        Convert domain model to database entity.
        Default implementation - override if needed.

        Args:
            domain_entity: Domain model

        Returns:
            Database entity
        """
        # Default implementation tries to create from dict
        # Override in concrete repositories for complex conversions
        entity_dict = domain_entity.dict()
        return self.table_class(**entity_dict)


class DatabaseSession:
    """Database session management with proper error handling"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.logger = logger.bind(component="database_session")

    async def __aenter__(self) -> AsyncSession:
        """Async context manager entry"""
        return self.session

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit with transaction handling"""
        if exc_type is not None:
            # Exception occurred - rollback transaction
            await self.session.rollback()
            self.logger.error(
                "Transaction rolled back due to exception",
                exception_type=exc_type.__name__ if exc_type else None,
                exception_message=str(exc_val) if exc_val else None,
            )
        else:
            # Success - commit transaction
            try:
                await self.session.commit()
                self.logger.debug("Transaction committed successfully")
            except Exception as e:
                await self.session.rollback()
                self.logger.error("Failed to commit transaction", error=str(e))
                raise

        await self.session.close()


# Utility functions for repository operations


async def with_transaction(
    session: AsyncSession, operation: callable, *args, **kwargs
) -> Any:
    """
    Execute operation within database transaction with proper error handling.

    Args:
        session: Database session
        operation: Async function to execute
        *args: Positional arguments for operation
        **kwargs: Keyword arguments for operation

    Returns:
        Operation result

    Raises:
        RepositoryError: If operation fails
    """
    try:
        async with DatabaseSession(session) as db_session:
            result = await operation(db_session, *args, **kwargs)
            return result
    except Exception as e:
        logger.error(
            "Transaction operation failed", operation=operation.__name__, error=str(e)
        )
        raise RepositoryError(f"Transaction failed: {e}") from e
