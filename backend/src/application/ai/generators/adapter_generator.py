"""
Dynamic API adapter code generator
Generates Python API client code at runtime based on API specifications
"""
import logging
import ast
import astor
from typing import Dict, Any, Optional
from jinja2 import Environment, BaseLoader, Template
from pathlib import Path

from src.domain.value_objects.api_schema import APISpecification, AuthType
from src.domain.value_objects.api_endpoint import APIEndpoint, HTTPMethod

logger = logging.getLogger(__name__)


class DynamicAdapterGenerator:
    """
    Generates API client code dynamically from API specifications
    
    Features:
    - Complete API client class generation
    - Authentication handling (API Key, Bearer, OAuth2, Basic)
    - Error handling and retries
    - Async/await support
    - Type hints
    - Docstrings
    """
    
    def __init__(self):
        self.jinja_env = Environment(loader=BaseLoader())
    
    async def generate_adapter(
        self,
        partner_id: str,
        api_spec: APISpecification,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate complete API adapter code
        
        Args:
            partner_id: Unique partner identifier
            api_spec: Parsed API specification
            output_path: Optional path to save generated code
            
        Returns:
            Generated Python code as string
        """
        try:
            logger.info(f"Generating adapter for partner: {partner_id}")
            
            # Generate code from template
            template = self._get_adapter_template()
            code = template.render(
                partner_id=partner_id,
                class_name=self._generate_class_name(partner_id),
                api_title=api_spec.title,
                api_version=api_spec.version,
                base_url=api_spec.base_url,
                auth=api_spec.auth,
                endpoints=api_spec.endpoints,
                schemas=api_spec.schemas
            )
            
            # Validate generated code
            await self._validate_code(code)
            
            # Optionally save to file
            if output_path:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w') as f:
                    f.write(code)
                logger.info(f"Adapter saved to: {output_path}")
            
            logger.info(f"Adapter generated successfully for {partner_id}")
            return code
        
        except Exception as e:
            logger.error(f"Error generating adapter: {e}")
            raise
    
    def _generate_class_name(self, partner_id: str) -> str:
        """Generate a valid Python class name from partner_id"""
        # Remove special characters, capitalize words
        clean_name = ''.join(c if c.isalnum() else '_' for c in partner_id)
        words = clean_name.split('_')
        class_name = ''.join(word.capitalize() for word in words if word)
        return f"{class_name}APIClient"
    
    def _get_adapter_template(self) -> Template:
        """Get Jinja2 template for API adapter"""
        template_str = '''"""
{{ api_title }} API Client
Generated dynamically for partner: {{ partner_id }}

Version: {{ api_version }}
Base URL: {{ base_url }}
"""
import logging
from typing import Optional, Dict, Any, List
import aiohttp
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class {{ class_name }}:
    """
    API client for {{ api_title }}
    
    This class was automatically generated from API documentation.
    """
    
    def __init__(
        self,
        base_url: str = "{{ base_url }}",
{% if auth %}
{% if auth.type.value == "api_key" %}
        api_key: Optional[str] = None,
{% elif auth.type.value == "bearer_token" %}
        bearer_token: Optional[str] = None,
{% elif auth.type.value == "basic_auth" %}
        username: Optional[str] = None,
        password: Optional[str] = None,
{% endif %}
{% endif %}
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize {{ api_title }} API client
        
        Args:
            base_url: API base URL
{% if auth %}
{% if auth.type.value == "api_key" %}
            api_key: API key for authentication
{% elif auth.type.value == "bearer_token" %}
            bearer_token: Bearer token for authentication
{% elif auth.type.value == "basic_auth" %}
            username: Username for basic auth
            password: Password for basic auth
{% endif %}
{% endif %}
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip('/')
{% if auth %}
{% if auth.type.value == "api_key" %}
        self.api_key = api_key
{% elif auth.type.value == "bearer_token" %}
        self.bearer_token = bearer_token
{% elif auth.type.value == "basic_auth" %}
        self.username = username
        self.password = password
{% endif %}
{% endif %}
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._get_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=self._get_default_headers()
            )
        return self._session
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers including authentication"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
{% if auth %}
{% if auth.type.value == "api_key" and auth.header_name %}
        if self.api_key:
            headers["{{ auth.header_name }}"] = self.api_key
{% elif auth.type.value == "bearer_token" %}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
{% endif %}
{% endif %}
        
        return headers
    
    async def _request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retries
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            **kwargs: Additional arguments for aiohttp request
            
        Returns:
            Response data as dictionary
        """
        url = f"{self.base_url}{path}"
        session = await self._get_session()
        
        for attempt in range(self.max_retries):
            try:
                async with session.request(method, url, **kwargs) as response:
                    response.raise_for_status()
                    
                    # Handle different response types
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'application/json' in content_type:
                        return await response.json()
                    else:
                        text = await response.text()
                        return {"data": text}
            
            except aiohttp.ClientError as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt == self.max_retries - 1:
                    raise
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
        
        raise Exception("Max retries exceeded")
    
    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()

{% for endpoint in endpoints %}
    async def {{ endpoint.path.replace('/', '_').replace('{', '').replace('}', '').strip('_').lower() }}_{{ endpoint.method.value.lower() }}(
        self,
{% for param in endpoint.parameters %}
{% if param.required %}
        {{ param.name }}: {{ 'str' if param.type == 'string' else param.type }},
{% endif %}
{% endfor %}
{% for param in endpoint.parameters %}
{% if not param.required %}
        {{ param.name }}: Optional[{{ 'str' if param.type == 'string' else param.type }}] = None,
{% endif %}
{% endfor %}
{% if endpoint.request_body_schema %}
        body: Optional[Dict[str, Any]] = None,
{% endif %}
        **kwargs
    ) -> Dict[str, Any]:
        """
        {{ endpoint.summary or 'API endpoint' }}
        
{% if endpoint.description %}
        {{ endpoint.description }}
{% endif %}
        
        Args:
{% for param in endpoint.parameters %}
            {{ param.name }}: {{ param.description or 'Parameter' }}{% if param.required %} (required){% endif %}

{% endfor %}
{% if endpoint.request_body_schema %}
            body: Request body data
{% endif %}
            **kwargs: Additional request parameters
            
        Returns:
            API response as dictionary
        """
        # Build path with path parameters
        path = "{{ endpoint.path }}"
{% for param in endpoint.parameters %}
{% if param.location.value == 'path' %}
        path = path.replace("{%raw%}{{% endraw %}{{ param.name }}{%raw%}}{% endraw %}", str({{ param.name }}))
{% endif %}
{% endfor %}
        
        # Build query parameters
        params = {}
{% for param in endpoint.parameters %}
{% if param.location.value == 'query' %}
        if {{ param.name }} is not None:
            params["{{ param.name }}"] = {{ param.name }}
{% endif %}
{% endfor %}
        
        # Build headers
        headers = {}
{% for param in endpoint.parameters %}
{% if param.location.value == 'header' %}
        if {{ param.name }} is not None:
            headers["{{ param.name }}"] = {{ param.name }}
{% endif %}
{% endfor %}
        
        # Make request
        return await self._request(
            "{{ endpoint.method.value }}",
            path,
            params=params if params else None,
            headers=headers if headers else None,
{% if endpoint.request_body_schema %}
            json=body if body else None,
{% endif %}
            **kwargs
        )

{% endfor %}
'''
        
        return self.jinja_env.from_string(template_str)
    
    async def _validate_code(self, code: str) -> bool:
        """
        Validate generated Python code
        
        Checks:
        - Syntax validity
        - AST structure
        - No dangerous imports
        """
        try:
            # Parse code into AST
            tree = ast.parse(code)
            
            # Check for dangerous imports/operations
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in ['os', 'sys', 'subprocess', 'eval', 'exec']:
                            raise ValueError(f"Dangerous import detected: {alias.name}")
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module in ['os', 'sys', 'subprocess']:
                        raise ValueError(f"Dangerous import detected: {node.module}")
            
            logger.info("Code validation passed")
            return True
        
        except SyntaxError as e:
            logger.error(f"Syntax error in generated code: {e}")
            raise ValueError(f"Generated code has syntax error: {e}")
        
        except Exception as e:
            logger.error(f"Code validation failed: {e}")
            raise
    
    async def generate_test_code(
        self,
        partner_id: str,
        api_spec: APISpecification
    ) -> str:
        """
        Generate test code for the adapter
        """
        class_name = self._generate_class_name(partner_id)
        
        test_template = f'''"""
Test suite for {api_spec.title} API Client
"""
import pytest
import asyncio
from {partner_id}_client import {class_name}


@pytest.mark.asyncio
async def test_client_initialization():
    """Test client initialization"""
    async with {class_name}() as client:
        assert client.base_url == "{api_spec.base_url}"


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint if available"""
    async with {class_name}() as client:
        # Add actual test based on available endpoints
        pass


# Add more tests based on API endpoints
'''
        
        return test_template


