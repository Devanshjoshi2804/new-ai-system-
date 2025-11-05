"""
Discovery Result Entity
Stores results of API discovery process
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from beanie import Document


class DiscoveredEndpoint(BaseModel):
    """Single discovered endpoint"""
    path: str
    method: str
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: List[Dict[str, Any]] = Field(default_factory=list)
    auth_required: bool = False
    source: str  # 'documentation', 'probe', 'crawl', etc.


class AuthConfiguration(BaseModel):
    """Detected authentication configuration"""
    auth_type: str  # 'bearer', 'api_key', 'basic', 'oauth2', 'custom'
    header_name: Optional[str] = None
    token_location: Optional[str] = None
    scheme: Optional[str] = None
    login_endpoint: Optional[str] = None
    token_format: Optional[str] = None
    confidence: float = 0.0
    test_passed: bool = False


class DiscoveryResultEntity(Document):
    """
    Discovery result stored in MongoDB
    """
    id: str = Field(default_factory=lambda: f"disc_{datetime.utcnow().timestamp()}")
    partner_id: str
    base_url: str
    status: str = "pending"  # pending, in_progress, completed, failed

    # Discovery results
    endpoints: List[DiscoveredEndpoint] = Field(default_factory=list)
    auth_config: Optional[AuthConfiguration] = None
    documentation_url: Optional[str] = None
    api_version: Optional[str] = None
    schemas: Dict[str, Any] = Field(default_factory=dict)
    dependency_graph: Dict[str, Any] = Field(default_factory=dict)
    workflows: List[Dict[str, Any]] = Field(default_factory=list)

    # Metadata
    discovery_time: float = 0.0
    errors: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "discovery_results"
        indexes = [
            "partner_id",
            "base_url",
            "status"
        ]
