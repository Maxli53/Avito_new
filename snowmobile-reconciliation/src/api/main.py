"""
Main FastAPI application for Snowmobile Product Reconciliation service.

Enterprise-grade API with comprehensive middleware and error handling.
"""
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.endpoints import router
from src.config.settings import get_settings, validate_settings


# Get application settings
settings = get_settings()


# Database dependency injection
async def get_database_session():
    """Get async database session for dependency injection"""
    async with app.state.async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    print("🚀 Starting Snowmobile Product Reconciliation Service...")
    
    try:
        # Validate settings
        validate_settings()
        
        # Initialize database connection
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        from src.models.database import Base
        
        # Create async database engine
        database_url = settings.database_url
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        
        engine = create_async_engine(
            database_url,
            echo=settings.debug_mode,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        
        # Create async session maker
        async_session_maker = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Create database tables if they don't exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Store database components in app state
        app.state.db_engine = engine
        app.state.async_session_maker = async_session_maker
        
        # Initialize Claude API client
        from src.services.claude_enrichment import ClaudeEnrichmentService
        from src.models.domain import PipelineConfig
        config = PipelineConfig()
        claude_service = ClaudeEnrichmentService(config.claude)
        
        # Warm up pipeline stages
        from src.pipeline.inheritance_pipeline import InheritancePipeline
        from src.repositories.product_repository import ProductRepository
        from src.repositories.base_model_repository import BaseModelRepository
        from src.pipeline.validation.multi_layer_validator import MultiLayerValidator
        from src.services.pdf_extraction_service import PDFProcessingService
        
        # Pre-initialize pipeline components for faster request processing
        # Repositories will be created per-request with database sessions
        # This initialization creates the infrastructure for real database operations
        validator = MultiLayerValidator(config.pipeline)
        pdf_service = PDFProcessingService(claude_service)
        
        # Store in app state for reuse
        app.state.claude_service = claude_service
        app.state.config = config
        app.state.validator = validator
        app.state.pdf_service = pdf_service
        
        print("✅ Service started successfully")
        
    except Exception as e:
        print(f"❌ Failed to start service: {e}")
        raise
    
    yield
    
    # Shutdown
    print("🛑 Shutting down service...")
    
    # Cleanup resources
    try:
        # Close Claude service connections if any
        if hasattr(app.state, 'claude_service'):
            claude_service = app.state.claude_service
            if hasattr(claude_service, 'close'):
                await claude_service.close()
        
        # Close database connections
        if hasattr(app.state, 'db_engine'):
            await app.state.db_engine.dispose()
        
        # Flush any pending logs
        import logging
        logging.shutdown()
        
    except Exception as e:
        print(f"⚠️ Error during shutdown: {e}")
    
    print("✅ Service shut down gracefully")


# Create FastAPI application
app = FastAPI(
    title="Snowmobile Product Reconciliation API",
    description="Enterprise-grade API for reconciling snowmobile product specifications from price lists",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug_mode else None,  # Disable in production
    redoc_url="/redoc" if settings.debug_mode else None,
    openapi_url="/openapi.json" if settings.debug_mode else None,
)


# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.cors_origins or ["*"],
    allow_credentials=settings.security.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

if settings.is_production():
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.snowmobile-recon.com", "localhost"],
    )


# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with consistent format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "status_code": exc.status_code,
                "path": str(request.url.path),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed information"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "message": "Validation error",
                "status_code": 422,
                "path": str(request.url.path),
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    # Log the full exception
    print(f"Unexpected error: {exc}")
    
    # Return generic error to client (don't expose internals)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "Internal server error",
                "status_code": 500,
                "path": str(request.url.path),
            }
        },
    )


# Include API routes
app.include_router(router)


# Root endpoint
@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with service information"""
    return {
        "service": "Snowmobile Product Reconciliation",
        "version": "1.0.0",
        "status": "operational",
        "environment": settings.environment,
        "documentation": "/docs" if settings.debug_mode else "Disabled in production",
        "health": "/api/v1/health",
        "metrics": "/api/v1/metrics",
    }


# Prometheus metrics (if enabled)
if settings.monitoring.prometheus_enabled:
    instrumentator = Instrumentator()
    instrumentator.instrument(app).expose(app, endpoint="/metrics")


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    import time
    
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log request details (in production, use proper logging)
    if settings.monitoring.performance_tracking_enabled:
        print(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    
    # Add processing time header
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# API key validation (if enabled)
if settings.security.api_key_enabled:
    from fastapi.security import APIKeyHeader
    from fastapi import Depends, HTTPException
    
    api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
    
    async def validate_api_key(api_key: str = Depends(api_key_header)):
        """Validate API key for protected endpoints"""
        if not api_key or api_key not in settings.security.api_keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
            )
        return api_key
    
    # Add dependency to protected routes
    # router.dependencies.append(Depends(validate_api_key))


if __name__ == "__main__":
    import uvicorn
    
    # Run with uvicorn for development
    uvicorn.run(
        "src.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug_mode,
        workers=settings.workers if not settings.debug_mode else 1,
        log_level=settings.monitoring.log_level.lower(),
    )