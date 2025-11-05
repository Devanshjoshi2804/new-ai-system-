"""
Authentication Detector - Automatically detect and configure authentication
Supports: Bearer, Basic, API Key, OAuth, Custom, Session/Cookie
"""
import logging
import re
import json
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from src.domain.value_objects.api_schema import AuthConfig, AuthType

logger = logging.getLogger(__name__)


@dataclass
class AuthDetectionResult:
    """Result of authentication detection"""
    auth_type: AuthType
    header_name: Optional[str] = None
    token_location: Optional[str] = None  # e.g., "data.token", "token", "access_token"
    scheme: Optional[str] = None  # e.g., "bearer", "basic"
    login_endpoint: Optional[str] = None
    token_format: Optional[str] = None  # e.g., "Bearer {token}", "{token}"
    requires_credentials: bool = True
    detected_from: str = ""  # What method detected this
    confidence: float = 0.0  # 0.0 to 1.0
    test_passed: bool = False
    additional_info: Dict[str, Any] = None

    def __post_init__(self):
        if self.additional_info is None:
            self.additional_info = {}


class AuthDetector:
    """
    Intelligent authentication detector

    Detection strategies:
    1. Analyze 401/403 responses and WWW-Authenticate headers
    2. Parse API documentation for auth descriptions
    3. Try common authentication patterns
    4. Test authentication with sample credentials
    5. Detect session/cookie requirements
    6. Extract token location from successful logins
    """

    # Common authentication headers
    AUTH_HEADERS = [
        'Authorization',
        'X-API-Key',
        'X-Auth-Token',
        'Api-Key',
        'apikey',
        'token',
        'X-Access-Token',
    ]

    # Common login/auth endpoints
    LOGIN_ENDPOINTS = [
        '/login',
        '/auth',
        '/auth/login',
        '/api/login',
        '/api/auth',
        '/api/v1/login',
        '/api/v1/auth',
        '/authenticate',
        '/signin',
        '/token',
        '/oauth/token',
    ]

    # Common token field names in responses
    TOKEN_FIELDS = [
        'token',
        'access_token',
        'accessToken',
        'auth_token',
        'authToken',
        'jwt',
        'bearer_token',
        'api_key',
        'apiKey',
        'key',
    ]

    def __init__(self, timeout: int = 30):
        """
        Initialize Auth Detector

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = httpx.Timeout(timeout)
        self._session: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session"""
        if self._session is None or self._session.is_closed:
            self._session = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={'User-Agent': 'CargoDham-AI-AuthDetector/1.0'}
            )
        return self._session

    async def close(self):
        """Close HTTP session"""
        if self._session and not self._session.is_closed:
            await self._session.aclose()

    async def detect(
        self,
        base_url: str,
        documentation: Optional[Dict[str, Any]] = None,
        sample_endpoint: Optional[str] = None
    ) -> AuthDetectionResult:
        """
        Main detection method - identifies authentication type and configuration

        Args:
            base_url: API base URL
            documentation: Optional parsed API documentation
            sample_endpoint: Optional sample endpoint to test

        Returns:
            AuthDetectionResult with detected authentication configuration
        """
        try:
            logger.info(f"[START] Auth Detection: {base_url}")

            # Strategy 1: Check documentation first (most reliable)
            if documentation:
                result = await self._detect_from_documentation(documentation, base_url)
                if result and result.confidence > 0.7:
                    logger.info(f"[OK] Auth detected from documentation: {result.auth_type}")
                    return result

            # Strategy 2: Try making unauthenticated request to detect auth requirements
            result = await self._detect_from_401_response(base_url, sample_endpoint)
            if result and result.confidence > 0.5:
                logger.info(f"[OK] Auth detected from 401 response: {result.auth_type}")
                return result

            # Strategy 3: Try to find and analyze login endpoint
            result = await self._detect_from_login_endpoint(base_url)
            if result and result.confidence > 0.5:
                logger.info(f"[OK] Auth detected from login endpoint: {result.auth_type}")
                return result

            # Strategy 4: Try common auth patterns
            result = await self._detect_from_common_patterns(base_url)
            if result:
                logger.info(f"[OK] Auth detected from common patterns: {result.auth_type}")
                return result

            # Default: Assume no auth or API Key
            logger.warning("[WARN] Could not definitively detect auth type, assuming API Key")
            return AuthDetectionResult(
                auth_type=AuthType.API_KEY,
                header_name='X-API-Key',
                token_format='{token}',
                detected_from='default',
                confidence=0.3
            )

        except Exception as e:
            logger.error(f"[ERROR] Auth detection failed: {e}", exc_info=True)
            return AuthDetectionResult(
                auth_type=AuthType.CUSTOM,
                detected_from='error',
                confidence=0.0
            )

    async def _detect_from_documentation(
        self,
        documentation: Dict[str, Any],
        base_url: str
    ) -> Optional[AuthDetectionResult]:
        """Detect authentication from API documentation"""
        try:
            # Check for securitySchemes (OpenAPI 3.x)
            components = documentation.get('components', {})
            security_schemes = components.get('securitySchemes', {})

            if security_schemes:
                # Get first security scheme
                scheme_name, scheme_data = next(iter(security_schemes.items()))
                scheme_type = scheme_data.get('type', '').lower()

                if scheme_type == 'apikey':
                    return AuthDetectionResult(
                        auth_type=AuthType.API_KEY,
                        header_name=scheme_data.get('name', 'X-API-Key'),
                        scheme=scheme_data.get('in', 'header'),
                        token_format='{token}',
                        detected_from='openapi_docs',
                        confidence=0.95
                    )

                elif scheme_type == 'http':
                    http_scheme = scheme_data.get('scheme', '').lower()
                    if http_scheme == 'bearer':
                        return AuthDetectionResult(
                            auth_type=AuthType.BEARER_TOKEN,
                            header_name='Authorization',
                            scheme='bearer',
                            token_format='Bearer {token}',
                            detected_from='openapi_docs',
                            confidence=0.95
                        )
                    elif http_scheme == 'basic':
                        return AuthDetectionResult(
                            auth_type=AuthType.BASIC_AUTH,
                            header_name='Authorization',
                            scheme='basic',
                            token_format='Basic {token}',
                            detected_from='openapi_docs',
                            confidence=0.95
                        )

                elif scheme_type == 'oauth2':
                    flows = scheme_data.get('flows', {})
                    return AuthDetectionResult(
                        auth_type=AuthType.OAUTH2,
                        header_name='Authorization',
                        token_format='Bearer {token}',
                        detected_from='openapi_docs',
                        confidence=0.9,
                        additional_info={'flows': flows}
                    )

            # Check for security definitions (Swagger 2.0)
            security_defs = documentation.get('securityDefinitions', {})
            if security_defs:
                scheme_name, scheme_data = next(iter(security_defs.items()))
                scheme_type = scheme_data.get('type', '').lower()

                if scheme_type == 'apikey':
                    return AuthDetectionResult(
                        auth_type=AuthType.API_KEY,
                        header_name=scheme_data.get('name', 'X-API-Key'),
                        scheme=scheme_data.get('in', 'header'),
                        token_format='{token}',
                        detected_from='swagger_docs',
                        confidence=0.95
                    )

                elif scheme_type == 'basic':
                    return AuthDetectionResult(
                        auth_type=AuthType.BASIC_AUTH,
                        header_name='Authorization',
                        scheme='basic',
                        token_format='Basic {token}',
                        detected_from='swagger_docs',
                        confidence=0.95
                    )

                elif scheme_type == 'oauth2':
                    return AuthDetectionResult(
                        auth_type=AuthType.OAUTH2,
                        header_name='Authorization',
                        token_format='Bearer {token}',
                        detected_from='swagger_docs',
                        confidence=0.9
                    )

            return None

        except Exception as e:
            logger.debug(f"[DEBUG] Error detecting from docs: {e}")
            return None

    async def _detect_from_401_response(
        self,
        base_url: str,
        sample_endpoint: Optional[str] = None
    ) -> Optional[AuthDetectionResult]:
        """Detect authentication by analyzing 401/403 responses"""
        try:
            session = await self._get_session()

            # Try to make unauthenticated request
            test_url = base_url
            if sample_endpoint:
                test_url = f"{base_url.rstrip('/')}/{sample_endpoint.lstrip('/')}"

            logger.debug(f"[DEBUG] Testing unauthenticated request: {test_url}")

            response = await session.get(test_url)

            # Check for 401 Unauthorized or 403 Forbidden
            if response.status_code in [401, 403]:
                # Analyze WWW-Authenticate header
                www_auth = response.headers.get('WWW-Authenticate', '').lower()

                if www_auth:
                    logger.debug(f"[DEBUG] WWW-Authenticate: {www_auth}")

                    if 'bearer' in www_auth:
                        return AuthDetectionResult(
                            auth_type=AuthType.BEARER_TOKEN,
                            header_name='Authorization',
                            token_format='Bearer {token}',
                            detected_from='www_authenticate_header',
                            confidence=0.9
                        )

                    elif 'basic' in www_auth:
                        return AuthDetectionResult(
                            auth_type=AuthType.BASIC_AUTH,
                            header_name='Authorization',
                            scheme='basic',
                            token_format='Basic {token}',
                            detected_from='www_authenticate_header',
                            confidence=0.9
                        )

                # Check response body for auth hints
                try:
                    error_data = response.json()
                    error_message = json.dumps(error_data).lower()

                    if 'api key' in error_message or 'api_key' in error_message:
                        return AuthDetectionResult(
                            auth_type=AuthType.API_KEY,
                            header_name='X-API-Key',
                            token_format='{token}',
                            detected_from='error_message',
                            confidence=0.7
                        )

                    if 'bearer' in error_message or 'jwt' in error_message:
                        return AuthDetectionResult(
                            auth_type=AuthType.BEARER_TOKEN,
                            header_name='Authorization',
                            token_format='Bearer {token}',
                            detected_from='error_message',
                            confidence=0.7
                        )

                    if 'token' in error_message:
                        return AuthDetectionResult(
                            auth_type=AuthType.BEARER_TOKEN,
                            header_name='Authorization',
                            token_format='Bearer {token}',
                            detected_from='error_message',
                            confidence=0.6
                        )

                except:
                    pass

            return None

        except Exception as e:
            logger.debug(f"[DEBUG] Error detecting from 401: {e}")
            return None

    async def _detect_from_login_endpoint(
        self,
        base_url: str
    ) -> Optional[AuthDetectionResult]:
        """Find and analyze login endpoint to detect auth"""
        try:
            session = await self._get_session()

            # Try common login endpoints
            for login_path in self.LOGIN_ENDPOINTS:
                url = f"{base_url.rstrip('/')}{login_path}"

                try:
                    logger.debug(f"[DEBUG] Checking login endpoint: {url}")

                    # Try OPTIONS to see if endpoint exists
                    response = await session.options(url)
                    if response.status_code < 400:
                        # Endpoint exists, try to understand it

                        # Try POST with empty body to see error
                        post_response = await session.post(url, json={})

                        if post_response.status_code in [400, 422]:
                            # Analyze error to understand required fields
                            try:
                                error_data = post_response.json()
                                error_str = json.dumps(error_data).lower()

                                # Check what auth type it expects
                                if 'username' in error_str and 'password' in error_str:
                                    return AuthDetectionResult(
                                        auth_type=AuthType.BASIC_AUTH,
                                        login_endpoint=login_path,
                                        header_name='Authorization',
                                        scheme='basic',
                                        token_format='Basic {token}',
                                        detected_from='login_endpoint_analysis',
                                        confidence=0.8
                                    )

                                # Likely returns a token
                                return AuthDetectionResult(
                                    auth_type=AuthType.BEARER_TOKEN,
                                    login_endpoint=login_path,
                                    header_name='Authorization',
                                    token_format='Bearer {token}',
                                    detected_from='login_endpoint_found',
                                    confidence=0.7
                                )

                            except:
                                pass

                except httpx.HTTPStatusError:
                    continue
                except Exception as e:
                    logger.debug(f"[DEBUG] Error checking {login_path}: {e}")
                    continue

            return None

        except Exception as e:
            logger.debug(f"[DEBUG] Error detecting from login: {e}")
            return None

    async def _detect_from_common_patterns(
        self,
        base_url: str
    ) -> Optional[AuthDetectionResult]:
        """Try common authentication patterns"""
        try:
            # Most modern APIs use Bearer tokens
            return AuthDetectionResult(
                auth_type=AuthType.BEARER_TOKEN,
                header_name='Authorization',
                token_format='Bearer {token}',
                detected_from='common_pattern',
                confidence=0.5
            )

        except Exception as e:
            logger.debug(f"[DEBUG] Error with common patterns: {e}")
            return None

    async def test_authentication(
        self,
        base_url: str,
        auth_result: AuthDetectionResult,
        test_credentials: Optional[Dict[str, str]] = None,
        test_endpoint: Optional[str] = None
    ) -> bool:
        """
        Test if detected authentication works

        Args:
            base_url: API base URL
            auth_result: Detected authentication configuration
            test_credentials: Optional credentials to test with
            test_endpoint: Optional endpoint to test against

        Returns:
            True if authentication test passed
        """
        try:
            if not test_credentials:
                logger.warning("[WARN] No test credentials provided, cannot verify auth")
                return False

            session = await self._get_session()

            # Step 1: Get token (if needed)
            token = None

            if auth_result.login_endpoint:
                # Try to login first
                login_url = f"{base_url.rstrip('/')}{auth_result.login_endpoint}"
                logger.debug(f"[DEBUG] Testing login: {login_url}")

                response = await session.post(login_url, json=test_credentials)

                if response.status_code in [200, 201]:
                    data = response.json()

                    # Try to extract token
                    token = self._extract_token_from_response(data, auth_result)

                    if token:
                        logger.info(f"[OK] Successfully obtained token via login")
                        auth_result.test_passed = True
                        return True

            # Step 2: Try to make authenticated request
            if test_endpoint:
                test_url = f"{base_url.rstrip('/')}/{test_endpoint.lstrip('/')}"
                headers = {}

                if token:
                    # Use obtained token
                    if auth_result.token_format:
                        header_value = auth_result.token_format.replace('{token}', token)
                    else:
                        header_value = token

                    headers[auth_result.header_name] = header_value

                elif test_credentials.get('api_key'):
                    # Direct API key
                    headers[auth_result.header_name] = test_credentials['api_key']

                logger.debug(f"[DEBUG] Testing authenticated request: {test_url}")
                response = await session.get(test_url, headers=headers)

                if response.status_code < 400:
                    logger.info(f"[OK] Authenticated request successful")
                    auth_result.test_passed = True
                    return True

            return False

        except Exception as e:
            logger.error(f"[ERROR] Auth test failed: {e}")
            return False

    def _extract_token_from_response(
        self,
        response_data: Dict[str, Any],
        auth_result: AuthDetectionResult
    ) -> Optional[str]:
        """Extract authentication token from response"""
        try:
            # Try common token field names
            for field in self.TOKEN_FIELDS:
                if field in response_data:
                    token = response_data[field]
                    auth_result.token_location = field
                    return str(token)

            # Try nested in 'data' object
            if 'data' in response_data and isinstance(response_data['data'], dict):
                for field in self.TOKEN_FIELDS:
                    if field in response_data['data']:
                        token = response_data['data'][field]
                        auth_result.token_location = f"data.{field}"
                        return str(token)

            # Try nested in 'result' object
            if 'result' in response_data and isinstance(response_data['result'], dict):
                for field in self.TOKEN_FIELDS:
                    if field in response_data['result']:
                        token = response_data['result'][field]
                        auth_result.token_location = f"result.{field}"
                        return str(token)

            return None

        except Exception as e:
            logger.debug(f"[DEBUG] Error extracting token: {e}")
            return None
