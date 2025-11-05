"""
API Explorer - Automatically discover API endpoints from minimal information
Handles: OpenAPI docs discovery, endpoint crawling, method detection, versioning
"""
import logging
import asyncio
import re
from typing import List, Dict, Any, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
import json

import httpx
from bs4 import BeautifulSoup

from src.domain.value_objects.api_endpoint import APIEndpoint, HTTPMethod
from src.domain.value_objects.api_schema import APISpecification

logger = logging.getLogger(__name__)


class DiscoveryResult:
    """Result of API discovery process"""

    def __init__(self):
        self.base_url: str = ""
        self.endpoints: List[Dict[str, Any]] = []
        self.documentation_url: Optional[str] = None
        self.api_version: Optional[str] = None
        self.discovered_methods: Set[str] = set()
        self.rate_limits: Dict[str, Any] = {}
        self.server_info: Dict[str, Any] = {}
        self.discovery_time: float = 0.0
        self.errors: List[str] = []


class APIExplorer:
    """
    Intelligent API Explorer that discovers endpoints from minimal information

    Strategies:
    1. Try common documentation paths (/docs, /swagger.json, /openapi.json, /.well-known/api)
    2. OPTIONS requests to discover supported methods
    3. Crawl HTML for API endpoint links
    4. Extract HATEOAS links from responses
    5. Detect API versioning patterns
    6. Handle rate limiting intelligently
    """

    # Common API documentation paths to try
    COMMON_DOC_PATHS = [
        '/docs',
        '/api/docs',
        '/swagger.json',
        '/swagger.yaml',
        '/openapi.json',
        '/openapi.yaml',
        '/api-docs',
        '/api/v1/docs',
        '/api/v2/docs',
        '/documentation',
        '/.well-known/api',
        '/redoc',
        '/api/swagger',
        '/api/openapi',
    ]

    # Common API endpoint patterns
    COMMON_API_PATTERNS = [
        '/api',
        '/api/v1',
        '/api/v2',
        '/v1',
        '/v2',
        '/rest',
        '/rest/v1',
    ]

    # Common resource endpoints to try
    COMMON_RESOURCES = [
        'users',
        'items',
        'products',
        'orders',
        'customers',
        'data',
        'resources',
        'entities',
    ]

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        max_depth: int = 2,
        max_endpoints: int = 100
    ):
        """
        Initialize API Explorer

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            max_depth: Maximum crawl depth
            max_endpoints: Maximum endpoints to discover
        """
        self.timeout = httpx.Timeout(timeout)
        self.max_retries = max_retries
        self.max_depth = max_depth
        self.max_endpoints = max_endpoints
        self._session: Optional[httpx.AsyncClient] = None
        self._discovered_urls: Set[str] = set()
        self._rate_limit_reset: Optional[datetime] = None

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
                headers={
                    'User-Agent': 'CargoDham-AI-Explorer/1.0',
                    'Accept': 'application/json, text/html, */*'
                }
            )
        return self._session

    async def close(self):
        """Close HTTP session"""
        if self._session and not self._session.is_closed:
            await self._session.aclose()

    async def explore(
        self,
        minimal_info: str,
        auth_token: Optional[str] = None
    ) -> DiscoveryResult:
        """
        Main exploration method - discovers API structure from URL or snippet

        Args:
            minimal_info: Base URL or API snippet
            auth_token: Optional authentication token

        Returns:
            DiscoveryResult with discovered endpoints and metadata
        """
        start_time = datetime.now()
        result = DiscoveryResult()

        try:
            logger.info(f"[START] API Discovery: {minimal_info[:100]}")

            # Step 1: Extract/validate base URL
            base_url = await self._extract_base_url(minimal_info)
            if not base_url:
                raise ValueError("Could not extract valid base URL")

            result.base_url = base_url
            logger.info(f"[OK] Base URL: {base_url}")

            # Step 2: Try to find API documentation
            doc_url = await self._find_documentation(base_url, auth_token)
            if doc_url:
                result.documentation_url = doc_url
                logger.info(f"[OK] Documentation found: {doc_url}")

                # If we found OpenAPI/Swagger docs, parse them
                endpoints = await self._parse_documentation(doc_url, auth_token)
                if endpoints:
                    result.endpoints.extend(endpoints)
                    logger.info(f"[OK] Parsed {len(endpoints)} endpoints from documentation")

            # Step 3: Probe for API endpoints
            if len(result.endpoints) < self.max_endpoints:
                discovered = await self._probe_common_patterns(base_url, auth_token)
                result.endpoints.extend(discovered)
                logger.info(f"[OK] Discovered {len(discovered)} endpoints via probing")

            # Step 4: Detect API version
            result.api_version = await self._detect_api_version(base_url, result.endpoints)

            # Step 5: Get server information
            result.server_info = await self._get_server_info(base_url)

            # Step 6: Deduplicate and clean endpoints
            result.endpoints = self._deduplicate_endpoints(result.endpoints)

            # Calculate discovery time
            result.discovery_time = (datetime.now() - start_time).total_seconds()

            logger.info(f"[COMPLETE] Discovery finished: {len(result.endpoints)} endpoints in {result.discovery_time:.2f}s")

            return result

        except Exception as e:
            logger.error(f"[ERROR] Discovery failed: {e}", exc_info=True)
            result.errors.append(str(e))
            result.discovery_time = (datetime.now() - start_time).total_seconds()
            return result

    async def _extract_base_url(self, minimal_info: str) -> Optional[str]:
        """Extract and validate base URL from input"""
        try:
            # Check if it's already a URL
            if minimal_info.startswith(('http://', 'https://')):
                parsed = urlparse(minimal_info)
                # Remove path, query, fragment - keep just scheme + netloc
                base_url = f"{parsed.scheme}://{parsed.netloc}"

                # Verify it's accessible
                if await self._is_accessible(base_url):
                    return base_url

            # Try adding https://
            potential_url = f"https://{minimal_info.strip()}"
            if await self._is_accessible(potential_url):
                return potential_url

            # Try http://
            potential_url = f"http://{minimal_info.strip()}"
            if await self._is_accessible(potential_url):
                return potential_url

            return None

        except Exception as e:
            logger.warning(f"[WARN] Could not extract base URL: {e}")
            return None

    async def _is_accessible(self, url: str) -> bool:
        """Check if URL is accessible"""
        try:
            session = await self._get_session()
            response = await session.head(url, timeout=5.0)
            return response.status_code < 500
        except:
            return False

    async def _find_documentation(
        self,
        base_url: str,
        auth_token: Optional[str] = None
    ) -> Optional[str]:
        """Try to find API documentation"""
        session = await self._get_session()
        headers = {}
        if auth_token:
            headers['Authorization'] = f"Bearer {auth_token}"

        for doc_path in self.COMMON_DOC_PATHS:
            try:
                url = urljoin(base_url, doc_path)
                logger.debug(f"[SEARCH] Trying documentation path: {url}")

                response = await session.get(url, headers=headers)

                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')

                    # Check if it's OpenAPI/Swagger JSON/YAML
                    if 'json' in content_type or 'yaml' in content_type or 'yml' in content_type:
                        try:
                            data = response.json() if 'json' in content_type else response.text
                            if isinstance(data, dict) and ('openapi' in data or 'swagger' in data):
                                logger.info(f"[OK] Found OpenAPI/Swagger docs at: {url}")
                                return url
                        except:
                            pass

                    # Check if it's HTML documentation page
                    if 'html' in content_type:
                        if any(keyword in response.text.lower() for keyword in ['swagger', 'openapi', 'api documentation']):
                            logger.info(f"[OK] Found documentation page at: {url}")
                            return url

            except httpx.HTTPStatusError:
                continue
            except Exception as e:
                logger.debug(f"[DEBUG] Error checking {doc_path}: {e}")
                continue

        logger.warning("[WARN] No API documentation found")
        return None

    async def _parse_documentation(
        self,
        doc_url: str,
        auth_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Parse OpenAPI/Swagger documentation"""
        try:
            session = await self._get_session()
            headers = {}
            if auth_token:
                headers['Authorization'] = f"Bearer {auth_token}"

            response = await session.get(doc_url, headers=headers)

            if response.status_code != 200:
                return []

            content_type = response.headers.get('content-type', '')

            if 'json' in content_type:
                spec_data = response.json()
            elif 'yaml' in content_type or 'yml' in content_type:
                import yaml
                spec_data = yaml.safe_load(response.text)
            else:
                return []

            # Parse OpenAPI 3.x or Swagger 2.0
            if not isinstance(spec_data, dict):
                return []

            paths = spec_data.get('paths', {})
            endpoints = []

            for path, methods in paths.items():
                for method, details in methods.items():
                    if method.lower() in ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']:
                        endpoints.append({
                            'path': path,
                            'method': method.upper(),
                            'summary': details.get('summary', ''),
                            'description': details.get('description', ''),
                            'parameters': details.get('parameters', []),
                            'source': 'documentation',
                            'auth_required': 'security' in details
                        })

            return endpoints

        except Exception as e:
            logger.error(f"[ERROR] Failed to parse documentation: {e}")
            return []

    async def _probe_common_patterns(
        self,
        base_url: str,
        auth_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Probe common API patterns to discover endpoints"""
        discovered = []
        session = await self._get_session()
        headers = {}
        if auth_token:
            headers['Authorization'] = f"Bearer {auth_token}"

        # Try common API base paths
        for api_path in self.COMMON_API_PATTERNS:
            url = urljoin(base_url, api_path)

            # Try OPTIONS to discover supported methods
            try:
                response = await session.options(url, headers=headers)
                if response.status_code < 400:
                    allowed_methods = self._parse_allowed_methods(response)
                    if allowed_methods:
                        for method in allowed_methods:
                            discovered.append({
                                'path': api_path,
                                'method': method,
                                'summary': f'{method} {api_path}',
                                'source': 'options_probe',
                                'auth_required': False
                            })
            except:
                pass

            # Try GET request
            try:
                response = await session.get(url, headers=headers)
                if response.status_code < 400:
                    discovered.append({
                        'path': api_path,
                        'method': 'GET',
                        'summary': f'GET {api_path}',
                        'source': 'probe',
                        'auth_required': False
                    })

                    # Extract links from response
                    links = await self._extract_links_from_response(response, base_url)
                    for link in links:
                        discovered.append(link)
            except:
                pass

            # Try common resources under this API path
            for resource in self.COMMON_RESOURCES[:5]:  # Limit to avoid too many requests
                resource_url = f"{api_path}/{resource}"
                full_url = urljoin(base_url, resource_url)

                try:
                    response = await session.get(full_url, headers=headers)
                    if response.status_code < 400:
                        discovered.append({
                            'path': resource_url,
                            'method': 'GET',
                            'summary': f'GET {resource}',
                            'source': 'resource_probe',
                            'auth_required': False
                        })
                except:
                    pass

                if len(discovered) >= self.max_endpoints:
                    break

            if len(discovered) >= self.max_endpoints:
                break

        return discovered

    def _parse_allowed_methods(self, response: httpx.Response) -> List[str]:
        """Parse allowed methods from OPTIONS response"""
        allowed = response.headers.get('Allow', '')
        if allowed:
            methods = [m.strip().upper() for m in allowed.split(',')]
            return [m for m in methods if m in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD']]
        return []

    async def _extract_links_from_response(
        self,
        response: httpx.Response,
        base_url: str
    ) -> List[Dict[str, Any]]:
        """Extract API endpoint links from response (HATEOAS, hypermedia)"""
        links = []

        try:
            content_type = response.headers.get('content-type', '')

            if 'json' in content_type:
                data = response.json()
                # Look for common link patterns
                extracted = self._extract_links_from_json(data, base_url)
                links.extend(extracted)

            elif 'html' in content_type:
                # Extract from HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if self._looks_like_api_endpoint(href):
                        full_url = urljoin(base_url, href)
                        parsed = urlparse(full_url)
                        links.append({
                            'path': parsed.path,
                            'method': 'GET',
                            'summary': link.get_text(strip=True) or f'GET {parsed.path}',
                            'source': 'html_crawl',
                            'auth_required': False
                        })

        except:
            pass

        return links[:10]  # Limit links per response

    def _extract_links_from_json(
        self,
        data: Any,
        base_url: str,
        depth: int = 0
    ) -> List[Dict[str, Any]]:
        """Recursively extract links from JSON response"""
        links = []

        if depth > 3:  # Prevent deep recursion
            return links

        if isinstance(data, dict):
            # Check for common link keys
            for key in ['href', 'url', 'link', 'uri', '_links', 'links']:
                if key in data:
                    value = data[key]
                    if isinstance(value, str) and self._looks_like_api_endpoint(value):
                        parsed = urlparse(urljoin(base_url, value))
                        links.append({
                            'path': parsed.path,
                            'method': 'GET',
                            'summary': f'GET {parsed.path}',
                            'source': 'hateoas',
                            'auth_required': False
                        })

            # Recurse into nested objects
            for value in data.values():
                links.extend(self._extract_links_from_json(value, base_url, depth + 1))

        elif isinstance(data, list):
            for item in data[:5]:  # Limit to first 5 items
                links.extend(self._extract_links_from_json(item, base_url, depth + 1))

        return links

    def _looks_like_api_endpoint(self, url: str) -> bool:
        """Check if URL looks like an API endpoint"""
        if not url:
            return False

        # Remove query string and fragment
        path = urlparse(url).path

        # Must start with / and not be root
        if not path or path == '/':
            return False

        # Exclude common non-API paths
        excluded = ['.html', '.css', '.js', '.png', '.jpg', '.ico', '.svg', '.woff']
        if any(path.endswith(ext) for ext in excluded):
            return False

        # Must contain API-like patterns
        api_indicators = ['/api/', '/v1/', '/v2/', '/rest/', '/data/', '/resource/']
        return any(indicator in path.lower() for indicator in api_indicators)

    async def _detect_api_version(
        self,
        base_url: str,
        endpoints: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Detect API versioning scheme"""
        # Check URL patterns
        version_patterns = [
            r'/v(\d+)',
            r'/api/v(\d+)',
            r'/api/(\d+\.\d+)',
        ]

        for endpoint in endpoints:
            path = endpoint.get('path', '')
            for pattern in version_patterns:
                match = re.search(pattern, path)
                if match:
                    return match.group(1)

        return None

    async def _get_server_info(self, base_url: str) -> Dict[str, Any]:
        """Get server information from headers"""
        try:
            session = await self._get_session()
            response = await session.head(base_url)

            return {
                'server': response.headers.get('Server', 'Unknown'),
                'powered_by': response.headers.get('X-Powered-By', 'Unknown'),
                'rate_limit': response.headers.get('X-RateLimit-Limit', 'Unknown'),
                'cors': 'Access-Control-Allow-Origin' in response.headers
            }
        except:
            return {}

    def _deduplicate_endpoints(self, endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate endpoints"""
        seen = set()
        unique = []

        for endpoint in endpoints:
            key = (endpoint['path'], endpoint['method'])
            if key not in seen:
                seen.add(key)
                unique.append(endpoint)

        return unique
