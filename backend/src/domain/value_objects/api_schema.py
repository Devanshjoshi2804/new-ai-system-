"""
API Schema value object
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class AuthType(str, Enum):
    """Authentication types"""
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    OAUTH2 = "oauth2"
    CUSTOM = "custom"
    NONE = "none"


class AuthConfig(BaseModel):
    """Authentication configuration"""
    type: AuthType
    header_name: Optional[str] = None  # For API key
    scheme: Optional[str] = None  # For bearer/basic
    flows: Optional[Dict[str, Any]] = None  # For OAuth2
    custom_logic: Optional[str] = None  # For custom auth


class APISpecification(BaseModel):
    """Complete API specification"""
    
    # Basic info
    title: str = "Unnamed API"
    version: str = "1.0.0"
    description: Optional[str] = None
    
    # Server info
    base_url: str
    servers: List[str] = Field(default_factory=list)
    
    # Endpoints
    endpoints: List['APIEndpoint'] = Field(default_factory=list)
    
    # Authentication
    auth: Optional[AuthConfig] = None
    
    # Schemas/Models
    schemas: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Webhooks
    webhooks: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    contact: Optional[Dict[str, str]] = None
    license: Optional[Dict[str, str]] = None
    external_docs: Optional[Dict[str, str]] = None
    
    def get_endpoint(self, path: str, method: str) -> Optional['APIEndpoint']:
        """Find endpoint by path and method"""
        from domain.value_objects.api_endpoint import APIEndpoint
        
        for endpoint in self.endpoints:
            if endpoint.path == path and endpoint.method.value == method.upper():
                return endpoint
        return None
    
    def get_endpoints_by_tag(self, tag: str) -> List['APIEndpoint']:
        """Get endpoints filtered by tag"""
        return [e for e in self.endpoints if tag in e.tags]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump()
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return self.model_dump_json(indent=2)


# Forward reference resolution
from src.domain.value_objects.api_endpoint import APIEndpoint
APISpecification.model_rebuild()


