"""
MongoDB connection management - Simple Motor-only implementation
No Beanie, no index issues - just pure MongoDB access
"""
import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class MongoDBConnection:
    """MongoDB connection manager using Motor directly"""
    
    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect(cls):
        """Initialize MongoDB connection"""
        try:
            logger.info(f"Connecting to MongoDB...")
            logger.info(f"Database: {settings.mongodb_database}")
            
            cls.client = AsyncIOMotorClient(
                settings.mongodb_url,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=10,
                minPoolSize=1
            )
            
            # Verify connection
            await cls.client.admin.command('ping')
            logger.info("[INFO] MongoDB connection successful")
            
            cls.database = cls.client[settings.mongodb_database]
            
            # List existing collections
            collections = await cls.database.list_collection_names()
            logger.info(f"[INFO] Connected to database '{settings.mongodb_database}'")
            logger.info(f"[INFO] Found {len(collections)} collections: {', '.join(collections)}")
            
        except Exception as e:
            logger.error(f"[INFO] Failed to connect to MongoDB: {e}")
            raise
    
    @classmethod
    async def disconnect(cls):
        """Close MongoDB connection"""
        if cls.client is not None:
            cls.client.close()
            logger.info("MongoDB connection closed")
    
    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if cls.database is None:
            raise RuntimeError("Database not initialized. Call connect() first.")
        return cls.database
    
    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        """Get MongoDB client"""
        if cls.client is None:
            raise RuntimeError("Client not initialized. Call connect() first.")
        return cls.client


# Global function to get database
async def get_mongodb() -> AsyncIOMotorDatabase:
    """Get MongoDB database instance"""
    return MongoDBConnection.get_database()


