"""
Health check endpoints
"""
from fastapi import APIRouter, status
from datetime import datetime

# Using MongoDB - tested and verified
from src.infrastructure.database.mongodb.connection import MongoDBConnection

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/db", status_code=status.HTTP_200_OK)
async def database_health():
    """Database connectivity health check"""
    try:
        # Check if MongoDB connection is alive
        if MongoDBConnection.client is not None:
            # Ping MongoDB to verify connection
            await MongoDBConnection.client.admin.command('ping')
            
            # Get database stats
            db = MongoDBConnection.get_database()
            stats = await db.command('dbStats')
            
            return {
                "status": "healthy",
                "database": "connected",
                "database_type": "mongodb",
                "database_name": db.name,
                "collections": stats.get('collections', 0),
                "data_size": f"{stats.get('dataSize', 0) / 1024:.2f} KB",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "unhealthy",
                "database": "not_initialized",
                "error": "MongoDB client is None",
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


