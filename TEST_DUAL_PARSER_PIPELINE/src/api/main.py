import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from ..repositories.database import DatabaseRepository
from ..services.price_extractor import PriceListExtractor
from ..services.catalog_extractor import CatalogExtractor
from ..services.matching_service import MatchingService
from ..services.claude_inheritance import ClaudeInheritanceService
from ..pipeline.main_pipeline import MainPipeline


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for services
db_repo: DatabaseRepository = None
main_pipeline: MainPipeline = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global db_repo, main_pipeline
    
    logger.info("Starting up Snowmobile Dual Parser Pipeline API")
    
    try:
        # Initialize database repository
        db_repo = DatabaseRepository()
        await db_repo.initialize()
        
        # Initialize services
        price_extractor = PriceListExtractor(db_repo)
        catalog_extractor = CatalogExtractor(db_repo)
        matching_service = MatchingService(db_repo)
        claude_service = ClaudeInheritanceService(db_repo)
        
        # Initialize main pipeline
        main_pipeline = MainPipeline(
            db_repo=db_repo,
            price_extractor=price_extractor,
            catalog_extractor=catalog_extractor,
            matching_service=matching_service,
            claude_service=claude_service
        )
        
        logger.info("All services initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    finally:
        # Cleanup
        if db_repo:
            await db_repo.close()
        logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Snowmobile Dual Parser Pipeline API",
    description="Intelligent PDF-to-Product Pipeline with Claude-Powered Inheritance",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with API documentation"""
    return """
    <html>
        <head>
            <title>Snowmobile Dual Parser Pipeline API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #333; }
                .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
                .method { font-weight: bold; color: #007cba; }
            </style>
        </head>
        <body>
            <h1>🛷 Snowmobile Dual Parser Pipeline API</h1>
            <p>Intelligent PDF-to-Product Pipeline with Claude-Powered Inheritance</p>
            
            <h2>Available Endpoints:</h2>
            
            <div class="endpoint">
                <span class="method">POST</span> /api/price-lists/upload - Upload new price list PDF
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> /api/catalogs/upload - Upload new catalog PDF
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> /api/products/generate - Trigger product generation
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> /api/products/{sku} - Get product details
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> /api/products/{sku}/html - Get HTML specification sheet
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> /api/status - Get pipeline status and statistics
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> /api/jobs/{job_id}/status - Check processing job status
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> /docs - Interactive API documentation (Swagger UI)
            </div>
        </body>
    </html>
    """


@app.post("/api/price-lists/upload")
async def upload_price_list(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    brand: str = Form(...),
    market: str = Form(...),
    model_year: int = Form(...)
):
    """Upload and process a new price list PDF"""
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Create data directory if it doesn't exist
        pdf_dir = Path("data/pdfs")
        pdf_dir.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded file
        file_path = pdf_dir / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"Uploaded price list: {file.filename} ({len(content)} bytes)")
        
        # Upload and process using pipeline
        price_list_id = await main_pipeline.upload_and_process_price_list(
            file_path, brand, market, model_year
        )
        
        return {
            "message": "Price list uploaded successfully",
            "price_list_id": str(price_list_id),
            "filename": file.filename,
            "brand": brand,
            "market": market,
            "model_year": model_year,
            "status": "queued_for_processing"
        }
        
    except Exception as e:
        logger.error(f"Failed to upload price list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/catalogs/upload")
async def upload_catalog(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    brand: str = Form(...),
    model_year: int = Form(...),
    document_type: str = Form("product_spec_book"),
    language: str = Form("FI")
):
    """Upload and process a new catalog PDF"""
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Create data directory if it doesn't exist
        pdf_dir = Path("data/pdfs")
        pdf_dir.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded file
        file_path = pdf_dir / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"Uploaded catalog: {file.filename} ({len(content)} bytes)")
        
        # Upload and process using pipeline
        catalog_id = await main_pipeline.upload_and_process_catalog(
            file_path, brand, model_year, document_type, language
        )
        
        return {
            "message": "Catalog uploaded successfully",
            "catalog_id": str(catalog_id),
            "filename": file.filename,
            "brand": brand,
            "model_year": model_year,
            "document_type": document_type,
            "language": language,
            "status": "queued_for_processing"
        }
        
    except Exception as e:
        logger.error(f"Failed to upload catalog: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/products/generate")
async def generate_products(background_tasks: BackgroundTasks):
    """Trigger product generation for all matched price entries"""
    
    try:
        # Run product generation in background
        background_tasks.add_task(main_pipeline.generate_all_products)
        
        return {
            "message": "Product generation started",
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Failed to start product generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/run")
async def run_full_pipeline(background_tasks: BackgroundTasks):
    """Run the complete processing pipeline"""
    
    try:
        # Run full pipeline in background
        background_tasks.add_task(main_pipeline.process_new_documents)
        
        return {
            "message": "Full pipeline started",
            "status": "processing",
            "description": "Processing price lists, catalogs, matching, and product generation"
        }
        
    except Exception as e:
        logger.error(f"Failed to start pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products/{sku}")
async def get_product(sku: str):
    """Get product details by SKU"""
    
    try:
        product = await db_repo.get_product_by_sku(sku)
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        return {
            "sku": product.sku,
            "model_code": product.model_code,
            "brand": product.brand,
            "model_family": product.model_family,
            "model_year": product.model_year,
            "market": product.market,
            "price": float(product.price),
            "currency": product.currency,
            "specifications": product.resolved_specifications,
            "confidence_score": float(product.confidence_score) if product.confidence_score else None,
            "validation_status": product.validation_status.value,
            "auto_approved": product.auto_approved,
            "created_at": product.created_at.isoformat() if product.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get product {sku}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products/{sku}/html")
async def get_product_html(sku: str):
    """Get HTML specification sheet for a product"""
    
    try:
        product = await db_repo.get_product_by_sku(sku)
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        if not product.html_content:
            raise HTTPException(status_code=404, detail="HTML content not available for this product")
        
        return HTMLResponse(content=product.html_content, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get product HTML {sku}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_pipeline_status():
    """Get current pipeline status and statistics"""
    
    try:
        status = await main_pipeline.get_pipeline_status()
        return status
        
    except Exception as e:
        logger.error(f"Failed to get pipeline status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """Check processing job status"""
    
    try:
        from uuid import UUID
        job_uuid = UUID(job_id)
        
        job = await db_repo.get_processing_job(job_uuid)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "job_id": str(job.id),
            "job_type": job.job_type.value,
            "status": job.status.value,
            "progress_percentage": job.progress_percentage,
            "total_items": job.total_items,
            "processed_items": job.processed_items,
            "successful_items": job.successful_items,
            "failed_items": job.failed_items,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "duration_ms": job.duration_ms,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat() if job.created_at else None
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    
    try:
        # Check database connection
        db_status = "ok" if db_repo.connection_pool else "error"
        
        return {
            "status": "healthy",
            "database": db_status,
            "api_version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


# Additional utility endpoints
@app.get("/api/statistics")
async def get_statistics():
    """Get detailed statistics about the pipeline"""
    
    try:
        stats = {
            "price_lists": await db_repo.get_price_list_statistics(),
            "catalogs": await db_repo.get_catalog_statistics(),
            "products": await db_repo.get_product_statistics(),
            "matching": {
                "total_entries": await db_repo.count_price_entries(),
                "matched_entries": await db_repo.count_matched_price_entries(),
                "unmatched_entries": await db_repo.count_unmatched_price_entries()
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Configuration
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    # Run the API
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )