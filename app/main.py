from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import uvicorn
from contextlib import asynccontextmanager

from app.config import settings
from app.models.database import db_manager
from app.services.vector_store import vector_store
from app.api.routes import documents, query

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info("Starting RAG Service...")
    try:
        # Initialize database tables
        db_manager.initialize_tables()
        logger.info("Database initialized successfully")
        
        # Warm up embedding model
        logger.info("Warming up embedding model...")
        test_embedding = vector_store.embedding_service.generate_embedding("test")
        logger.info(f"Embedding model ready. Dimension: {len(test_embedding)}")
        
        logger.info("RAG Service startup completed successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG Service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down RAG Service...")

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents.router)
app.include_router(query.router)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check vector store health
        health_status = vector_store.health_check()
        
        return {
            "status": "healthy" if health_status.get('database_healthy') and health_status.get('embedding_service_healthy') else "unhealthy",
            "timestamp": "2024-01-01T00:00:00Z",  # You can use datetime.utcnow().isoformat()
            "version": settings.api_version,
            "components": health_status
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RAG Service API",
        "version": settings.api_version,
        "docs_url": "/docs",
        "health_url": "/health"
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred"
            }
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower()
    )