"""
Pytest configuration and fixtures
"""
import pytest
import asyncio
from typing import AsyncGenerator
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

from src.main import app
from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.mongodb.connection import MongoDBConnection


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def initialize_mongodb():
    """Initialize MongoDB connection for all tests"""
    try:
        await MongoDBConnection.connect()
        print("\n✅ MongoDB connected for tests")
        yield
    except Exception as e:
        print(f"\n⚠️  MongoDB connection failed: {e}")
        print("   Tests requiring MongoDB will be skipped")
        yield
    finally:
        try:
            await MongoDBConnection.disconnect()
        except:
            pass


@pytest.fixture
def client():
    """Test client for API testing"""
    return TestClient(app)


@pytest.fixture
async def test_db():
    """Test database connection"""
    settings = get_settings()
    try:
        client = AsyncIOMotorClient(settings.mongodb_url)
        db = client["test_ai_logistics_platform"]
        
        yield db
        
        # Cleanup
        await client.drop_database("test_ai_logistics_platform")
        client.close()
    except Exception as e:
        # If MongoDB connection fails, yield None - tests can handle it
        print(f"Warning: Could not connect to MongoDB: {e}")
        yield None


@pytest.fixture
def sample_openapi_spec():
    """Sample OpenAPI specification for testing"""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "version": "1.0.0"
        },
        "servers": [{"url": "https://api.test.com"}],
        "paths": {
            "/bookings": {
                "post": {
                    "summary": "Create Booking",
                    "parameters": [
                        {"name": "origin", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "destination", "in": "query", "required": True, "schema": {"type": "string"}}
                    ]
                }
            }
        }
    }


@pytest.fixture
def sample_partner_data():
    """Sample partner registration data"""
    return {
        "company_name": "Test Logistics",
        "company_email": "test@logistics.com",
        "contact_name": "Test User",
        "contact_email": "user@test.com"
    }

