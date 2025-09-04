"""
FastAPI Production Server for Mistral Snowmobile Model
Serves the fine-tuned model via REST API
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import uvicorn
import torch
from pathlib import Path
import json
import asyncio
from contextlib import asynccontextmanager

from inference import SnowmobileMistral

# Global model instance
model_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global model_instance
    model_path = "../models/checkpoints/final_model"
    
    if not Path(model_path).exists():
        print(f"ERROR: Model not found at {model_path}")
        print("Please train the model first using: python scripts/train.py")
        yield
        return
    
    print("Loading Mistral model...")
    model_instance = SnowmobileMistral(model_path)
    model_instance.load_model()
    print("Model loaded successfully!")
    
    yield
    
    # Shutdown
    print("Shutting down...")

app = FastAPI(
    title="Mistral Snowmobile API",
    description="Fine-tuned Mistral 7B for snowmobile specification extraction",
    version="1.0.0",
    lifespan=lifespan
)

# Request/Response Models
class SpecExtractionRequest(BaseModel):
    text: str
    brand: Optional[str] = ""
    year: Optional[str] = ""

class PriceExtractionRequest(BaseModel):
    text: str
    brand: Optional[str] = ""
    year: Optional[str] = ""

class SimilarModelsRequest(BaseModel):
    query: str
    context: str

class ExtractionResponse(BaseModel):
    result: str
    processing_time: float

@app.get("/")
async def root():
    return {
        "message": "Mistral Snowmobile API",
        "status": "running",
        "gpu_available": torch.cuda.is_available(),
        "model_loaded": model_instance is not None
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "gpu_memory": torch.cuda.get_device_properties(0).total_memory / 1e9 if torch.cuda.is_available() else 0,
        "model_ready": model_instance is not None
    }

@app.post("/extract/specifications", response_model=ExtractionResponse)
async def extract_specifications(request: SpecExtractionRequest):
    """Extract technical specifications from snowmobile text"""
    if model_instance is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        import time
        start_time = time.time()
        
        result = model_instance.extract_specifications(
            request.text,
            request.brand,
            request.year
        )
        
        processing_time = time.time() - start_time
        
        return ExtractionResponse(
            result=result,
            processing_time=processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract/pricing", response_model=ExtractionResponse)
async def extract_pricing(request: PriceExtractionRequest):
    """Extract pricing information from price list text"""
    if model_instance is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        import time
        start_time = time.time()
        
        result = model_instance.extract_pricing(
            request.text,
            request.brand,
            request.year
        )
        
        processing_time = time.time() - start_time
        
        return ExtractionResponse(
            result=result,
            processing_time=processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/find/similar", response_model=ExtractionResponse)
async def find_similar_models(request: SimilarModelsRequest):
    """Find models matching specific criteria"""
    if model_instance is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        import time
        start_time = time.time()
        
        result = model_instance.find_similar_models(
            request.query,
            request.context
        )
        
        processing_time = time.time() - start_time
        
        return ExtractionResponse(
            result=result,
            processing_time=processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get model and system statistics"""
    stats = {
        "model_loaded": model_instance is not None,
        "gpu_available": torch.cuda.is_available(),
    }
    
    if torch.cuda.is_available():
        stats.update({
            "gpu_name": torch.cuda.get_device_name(),
            "gpu_memory_total": torch.cuda.get_device_properties(0).total_memory / 1e9,
            "gpu_memory_allocated": torch.cuda.memory_allocated() / 1e9,
            "gpu_memory_reserved": torch.cuda.memory_reserved() / 1e9,
        })
    
    return stats

if __name__ == "__main__":
    print("Starting Mistral Snowmobile API Server...")
    print("RTX 3090 optimized for production inference")
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload for production
        workers=1,     # Single worker for GPU model
    )