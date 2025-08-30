"""
Main application entry point for Snowmobile Product Reconciliation system.

Implements FastAPI application with proper dependency injection, error handling,
and monitoring following Universal Development Standards.
"""
from contextlib import asynccontextmanager
from typing import Any

import structlog
import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config.settings import get_environment_info, get_settings, validate_settings
from src.models.database import Base, create_functions, create_indexes
from src.models.domain import (
    ProcessingRequest,
    ProcessingResponse,
    ProductSpecification,
)
from src.pipeline.inheritance_pipeline import InheritancePipeline
from src.pipeline.validation.multi_layer_validator import MultiLayerValidator
from src.repositories.product_repository import BaseModelRepository, ProductRepository
from src.services.claude_enrichment import ClaudeEnrichmentService

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global application state
engine = None
async_session_maker = None
claude_service = None
pipeline = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown procedures.
    Handles database connections, service initialization, and cleanup.
    """
    # Startup procedures
    logger.info("Starting Snowmobile Product Reconciliation system")

    try:
        # Validate configuration
        validate_settings()
        settings = get_settings()

        # Initialize database
        await initialize_database(settings)

        # Initialize services
        await initialize_services(settings)

        # Create database indexes and functions
        if engine:
            create_indexes(engine.sync_engine)
            create_functions(engine.sync_engine)

        logger.info(
            "Application startup completed successfully",
            environment=settings.environment,
            debug_mode=settings.debug_mode,
        )

        yield

    except Exception as e:
        logger.error("Application startup failed", error=str(e))
        raise

    finally:
        # Shutdown procedures
        logger.info("Shutting down application")

        if claude_service:
            await claude_service.close()

        if engine:
            await engine.dispose()

        logger.info("Application shutdown completed")


async def initialize_database(settings) -> None:
    """Initialize database connection and session maker"""
    global engine, async_session_maker

    try:
        # Create async engine
        engine = create_async_engine(
            str(settings.database.database_url),
            echo=settings.database.database_echo,
            echo_pool=settings.database.database_echo_pool,
            pool_size=settings.database.database_pool_size,
            max_overflow=settings.database.database_max_overflow,
            pool_timeout=settings.database.database_pool_timeout,
            pool_recycle=settings.database.database_pool_recycle,
        )

        # Create session maker
        async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        # Test database connection
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database initialized successfully")

    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        raise


async def initialize_services(settings) -> None:
    """Initialize application services"""
    global claude_service, pipeline

    try:
        # Initialize Claude service
        claude_service = ClaudeEnrichmentService(
            config=settings.claude, api_key=settings.claude.claude_api_key
        )

        # Initialize pipeline components (will need to create these)
        # For now, we'll create placeholder services
        validator = MultiLayerValidator(settings.pipeline)

        # This will need actual repository implementations
        async with get_async_session() as session:
            product_repo = ProductRepository(session)
            base_model_repo = BaseModelRepository(session)

            pipeline = InheritancePipeline(
                config=settings.pipeline,
                product_repository=product_repo,
                validator=validator,
            )

        logger.info("Services initialized successfully")

    except Exception as e:
        logger.error("Service initialization failed", error=str(e))
        raise


# Create FastAPI application
app = FastAPI(
    title="Snowmobile Product Reconciliation API",
    description="Professional snowmobile product data reconciliation with 5-stage inheritance pipeline",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not get_settings().is_production() else None,
    redoc_url="/redoc" if not get_settings().is_production() else None,
)

# Add middleware
settings = get_settings()

# CORS middleware
if settings.security.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors_origins,
        allow_credentials=settings.security.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

# Trusted host middleware for security
if settings.is_production():
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.yourdomain.com", "localhost"],  # Configure for your domain
    )


# Dependency injection
async def get_async_session() -> AsyncSession:
    """Get async database session"""
    if not async_session_maker:
        raise HTTPException(status_code=500, detail="Database not initialized")

    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_product_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ProductRepository:
    """Get product repository with database session"""
    return ProductRepository(session)


async def get_pipeline() -> InheritancePipeline:
    """Get inheritance pipeline instance"""
    if not pipeline:
        raise HTTPException(status_code=500, detail="Pipeline not initialized")
    return pipeline


# API Routes


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint for monitoring.
    Returns application status and basic metrics.
    """
    try:
        # Test database connection
        async with get_async_session() as session:
            await session.execute("SELECT 1")

        db_status = "healthy"
    except Exception as e:
        logger.warning("Database health check failed", error=str(e))
        db_status = "unhealthy"

    # Test Claude service
    claude_status = "healthy" if claude_service else "not_initialized"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "version": "1.0.0",
        "environment": settings.environment,
        "components": {
            "database": db_status,
            "claude_service": claude_status,
            "pipeline": "healthy" if pipeline else "not_initialized",
        },
        "timestamp": "2024-01-01T00:00:00Z",  # Will be replaced with actual timestamp
    }


@app.get("/info")
async def application_info() -> dict[str, Any]:
    """
    Get application information and configuration.
    Excludes sensitive information in production.
    """
    info = get_environment_info()

    # Add runtime information
    info.update(
        {
            "database_connected": bool(engine),
            "claude_service_initialized": bool(claude_service),
            "pipeline_initialized": bool(pipeline),
        }
    )

    # Add service statistics if available
    if claude_service:
        info["claude_usage"] = claude_service.get_usage_statistics()

    return info


@app.post("/api/v1/process", response_model=ProcessingResponse)
async def process_price_entries(
    request: ProcessingRequest,
    background_tasks: BackgroundTasks,
    pipeline_instance: InheritancePipeline = Depends(get_pipeline),
) -> ProcessingResponse:
    """
    Process price entries through the 5-stage inheritance pipeline.

    This is the main API endpoint for product reconciliation.
    """
    logger.info(
        "Processing request received",
        entry_count=len(request.price_entries),
        priority=request.priority,
    )

    try:
        # Process through pipeline
        result = await pipeline_instance.process_price_entries(request.price_entries)

        # Create response
        response = ProcessingResponse(
            status="completed" if result.success else "partial_failure",
            products_processed=result.products_processed,
            products_successful=result.products_successful,
            products_failed=result.products_failed,
            products=result.products,
            processing_errors=result.errors,
            total_processing_time_ms=result.total_processing_time_ms,
            claude_tokens_total=result.claude_tokens_used,
            claude_cost_total=result.claude_cost_total,
        )

        # Send webhook notification if provided
        if request.callback_url:
            background_tasks.add_task(
                send_webhook_notification, request.callback_url, response
            )

        logger.info(
            "Processing completed",
            request_id=response.request_id,
            successful_products=response.products_successful,
            processing_time_ms=response.total_processing_time_ms,
        )

        return response

    except Exception as e:
        logger.error("Processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.get("/api/v1/products/{product_id}", response_model=ProductSpecification)
async def get_product(
    product_id: str, product_repo: ProductRepository = Depends(get_product_repository)
) -> ProductSpecification:
    """Get product by ID"""
    try:
        from uuid import UUID

        product_uuid = UUID(product_id)

        product = await product_repo.get_by_id(product_uuid)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        return product

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product ID format")
    except Exception as e:
        logger.error("Failed to get product", product_id=product_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/products")
async def list_products(
    limit: int = 50,
    offset: int = 0,
    confidence_level: str = None,
    product_repo: ProductRepository = Depends(get_product_repository),
):
    """List products with pagination and filtering"""
    try:
        if confidence_level:
            from src.models.domain import ConfidenceLevel

            confidence_filter = ConfidenceLevel(confidence_level)
            products = await product_repo.get_products_by_confidence(
                confidence_filter, limit, offset
            )
        else:
            products = await product_repo.list_all(limit, offset)

        return {
            "products": products,
            "limit": limit,
            "offset": offset,
            "total": len(products),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to list products", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/statistics")
async def get_statistics(
    product_repo: ProductRepository = Depends(get_product_repository),
):
    """Get processing statistics for monitoring dashboard"""
    try:
        stats = await product_repo.get_processing_statistics()
        return stats

    except Exception as e:
        logger.error("Failed to get statistics", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


# Background tasks
async def send_webhook_notification(
    callback_url: str, response: ProcessingResponse
) -> None:
    """Send webhook notification for completed processing"""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            await client.post(callback_url, json=response.dict(), timeout=10.0)

        logger.info("Webhook notification sent", callback_url=callback_url)

    except Exception as e:
        logger.warning(
            "Failed to send webhook notification",
            callback_url=callback_url,
            error=str(e),
        )


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with proper logging"""
    logger.warning(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url.path),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions with logging"""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "path": str(request.url.path),
        },
    )


def main() -> None:
    """Main entry point for running the application"""
    settings = get_settings()

    # Configure logging based on environment
    log_config = uvicorn.config.LOGGING_CONFIG
    if settings.monitoring.log_format == "json":
        # Configure JSON logging for production
        log_config["formatters"]["default"][
            "fmt"
        ] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Run the application
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        workers=1 if settings.is_development() else settings.workers,
        reload=settings.is_development(),
        log_level=settings.monitoring.log_level.lower(),
        access_log=True,
        log_config=log_config,
    )


if __name__ == "__main__":
    main()
