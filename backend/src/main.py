"""
Main FastAPI application entry point
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infrastructure.config.settings import settings
# Use MongoDB - tested and verified with read/write access
from src.infrastructure.database.mongodb.connection import MongoDBConnection
from src.infrastructure.middleware.tenant_middleware import TenantMiddleware
from src.presentation.rest.health import router as health_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting AI Logistics Platform with MongoDB...")
    
    # Connect to MongoDB
    await MongoDBConnection.connect()
    
    logger.info("Application started successfully with MongoDB")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await MongoDBConnection.disconnect()
    logger.info("Application stopped")


# Create FastAPI app
app = FastAPI(
    title="AI Logistics Integration Platform",
    description="Multi-tenant AI-powered logistics integration platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add request logging middleware first (before everything)
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"[SEARCH] REQUEST: {request.method} {request.url.path}")
    logger.info(f"   Headers: {dict(request.headers)}")
    try:
        response = await call_next(request)
        logger.info(f"[OK] RESPONSE: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"[ERROR] MIDDLEWARE ERROR: {e}", exc_info=True)
        raise

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Tenant middleware (must be added after CORS)
app.add_middleware(TenantMiddleware)

# Include routers
app.include_router(health_router, prefix="/api", tags=["Health"])

# Import and include routers
from src.presentation.rest.partners import router as partners_router
from src.presentation.rest.documentation import router as documentation_router
from src.presentation.rest.chat import router as chat_router
from src.presentation.rest.webhooks import router as webhooks_router
from src.presentation.rest.vision import router as vision_router
from src.presentation.rest.ocr import router as ocr_router
from src.presentation.rest.vector_db import router as vector_db_router
from src.presentation.rest.simple_testing import router as simple_testing_router
from src.presentation.rest.discovery import router as discovery_router
from src.presentation.rest.autonomous_api import router as autonomous_router

app.include_router(partners_router, prefix="/api", tags=["Partners"])
app.include_router(documentation_router, prefix="/api", tags=["Documentation"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(webhooks_router, prefix="/api", tags=["Webhooks"])
app.include_router(vision_router, prefix="/api", tags=["Vision OCR"])
app.include_router(ocr_router, prefix="/api", tags=["OCR"])
app.include_router(vector_db_router, tags=["Vector DB"])
app.include_router(simple_testing_router, tags=["Simple Testing - Clean & Working [START]"])
app.include_router(discovery_router, prefix="/api", tags=["🚀 AI Discovery System"])
app.include_router(autonomous_router, tags=["🤖 Autonomous Orchestration [Phase 3 & 4]"])

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "AI Logistics Integration Platform",
        "version": "1.0.0",
        "status": "operational"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        limit_max_requests=1000,
        timeout_keep_alive=5,
        h11_max_incomplete_event_size=16777216  # 16MB for headers/body
    )


