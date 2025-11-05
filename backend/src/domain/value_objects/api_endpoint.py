"""
API Endpoint value object
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class HTTPMethod(str, Enum):
    """HTTP methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ParameterLocation(str, Enum):
    """Parameter locations"""
    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    BODY = "body"
    COOKIE = "cookie"


class APIParameter(BaseModel):
    """API parameter definition"""
    name: str
    location: ParameterLocation
    required: bool = False
    type: str = "string"
    description: Optional[str] = None
    default: Optional[Any] = None
    example: Optional[Any] = None


class APIEndpoint(BaseModel):
    """API endpoint value object"""
    
    path: str = Field(..., description="Endpoint path (e.g., /api/v1/bookings)")
    method: HTTPMethod
    operation_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    
    parameters: List[APIParameter] = Field(default_factory=list)
    request_body_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    
    auth_required: bool = True
    rate_limit: Optional[int] = None
    
    tags: List[str] = Field(default_factory=list)
    
    def get_full_path(self, base_url: str) -> str:
        """Get full URL path"""
        base = base_url.rstrip('/')
        path = self.path if self.path.startswith('/') else f'/{self.path}'
        return f"{base}{path}"
    
    def get_required_parameters(self) -> List[APIParameter]:
        """Get list of required parameters"""
        return [p for p in self.parameters if p.required]
    
    def get_parameters_by_location(self, location: ParameterLocation) -> List[APIParameter]:
        """Get parameters by location"""
        return [p for p in self.parameters if p.location == location]


