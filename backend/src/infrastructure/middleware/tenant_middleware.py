"""
Tenant middleware for automatic tenant isolation on all requests
"""
import logging
from typing import Callable, Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import jwt

from src.domain.value_objects.tenant_id import TenantContext
# Temporarily disabled MongoDB imports - using SQLite
# from src.infrastructure.database.mongodb.tenant_aware_client import TenantAwareClient
from src.infrastructure.config.settings import settings


# Temporary: Simple context storage for SQLite (no MongoDB)
from contextvars import ContextVar
tenant_context_var: ContextVar[Optional[TenantContext]] = ContextVar('tenant_context', default=None)


class TenantAwareClient:
    """Simplified tenant client for SQLite"""
    
    @staticmethod
    def set_context(context: TenantContext):
        tenant_context_var.set(context)
    
    @staticmethod
    def clear_context():
        tenant_context_var.set(None)

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and set tenant context for every request
    
    Tenant can be identified from:
    1. X-Tenant-ID header (highest priority)
    2. Subdomain (e.g., partner1.platform.com)
    3. JWT token claims
    """
    
    # Paths that don't require tenant context
    EXCLUDED_PATHS = [
        "/",  # Root endpoint
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/api/health",
        "/api/auth/login",
        "/api/auth/register",
        "/api/partners",  # Allow all partner endpoints during onboarding (including subroutes)
        "/api/documentation",  # Allow documentation endpoints during onboarding
        "/api/vision",  # Allow vision/OCR endpoints
        "/api/testing",  # Allow testing endpoints
        "/api/chat",  # Allow chat endpoints for testing
        "/api/simple-testing",  # Allow simple testing endpoints
        "/api/discovery",  # Allow discovery endpoints (AI autonomous API discovery)
    ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and inject tenant context"""
        
        # Log all requests
        logger.info(f"[WEB] Middleware: {request.method} {request.url.path}")
        
        # Always allow OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            logger.info(f"[OK] OPTIONS request allowed: {request.url.path}")
            return await call_next(request)
        
        # Skip tenant extraction for excluded paths
        if self._is_excluded_path(request.url.path):
            logger.info(f"[OK] Path excluded from tenant check: {request.url.path}")
            return await call_next(request)
        
        try:
            # Extract tenant context
            tenant_context = await self._extract_tenant_context(request)
            
            if not tenant_context:
                logger.warning(f"[ERROR] Tenant context not found for: {request.url.path}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Tenant context not found. Please provide X-Tenant-ID header or valid authentication."
                )
            
            # Set tenant context for this request
            TenantAwareClient.set_context(tenant_context)
            
            # Add tenant info to request state for easy access
            request.state.tenant_context = tenant_context
            
            logger.debug(f"Tenant context set: {tenant_context.tenant_id}")
            
            # Process request
            response = await call_next(request)
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in tenant middleware: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error processing tenant context"
            )
        finally:
            # Clear context after request
            TenantAwareClient.clear_context()
    
    async def _extract_tenant_context(self, request: Request) -> Optional[TenantContext]:
        """
        Extract tenant context from request using multiple strategies
        """
        # Strategy 1: X-Tenant-ID header (explicit)
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return TenantContext(
                tenant_id=tenant_id,
                user_id=self._extract_user_id_from_request(request)
            )
        
        # Strategy 2: Extract from subdomain
        tenant_id = self._extract_from_subdomain(request)
        if tenant_id:
            return TenantContext(
                tenant_id=tenant_id,
                user_id=self._extract_user_id_from_request(request)
            )
        
        # Strategy 3: Extract from JWT token
        tenant_context = await self._extract_from_jwt(request)
        if tenant_context:
            return tenant_context
        
        return None
    
    def _extract_from_subdomain(self, request: Request) -> Optional[str]:
        """
        Extract tenant from subdomain
        Format: {tenant}.platform.com -> tenant
        """
        host = request.headers.get("host", "")
        parts = host.split(".")
        
        # Check if subdomain exists (at least 3 parts: subdomain.domain.tld)
        if len(parts) >= 3 and parts[0] not in ["www", "api"]:
            return parts[0]
        
        return None
    
    async def _extract_from_jwt(self, request: Request) -> Optional[TenantContext]:
        """
        Extract tenant context from JWT token
        """
        # Get authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        
        try:
            # Decode JWT token
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm]
            )
            
            tenant_id = payload.get("tenant_id")
            user_id = payload.get("sub")  # Standard JWT claim for user ID
            partner_id = payload.get("partner_id")
            
            if tenant_id:
                return TenantContext(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    partner_id=partner_id
                )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error decoding JWT: {e}")
            return None
        
        return None
    
    def _extract_user_id_from_request(self, request: Request) -> Optional[str]:
        """
        Extract user ID from request headers or JWT
        """
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return user_id
        
        # Try to extract from JWT
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(
                    token,
                    settings.secret_key,
                    algorithms=[settings.algorithm]
                )
                return payload.get("sub")
            except:
                pass
        
        return None
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from tenant requirement"""
        # Exact match for root path
        if path == "/":
            return True
        # Prefix match for other paths
        return any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS if excluded != "/")


