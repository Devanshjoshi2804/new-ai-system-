"""
Schema Inferencer - Infer request/response schemas from API interactions
Builds JSON schemas automatically by analyzing multiple API calls
"""
import logging
import json
from typing import Dict, Any, List, Optional, Set, Tuple
from collections import defaultdict, Counter
from datetime import datetime
import re

import httpx

logger = logging.getLogger(__name__)


class SchemaInferencer:
    """
    Intelligent schema inference from API responses and error messages

    Strategies:
    1. Make multiple sample requests and analyze responses
    2. Detect field types from values (string, int, float, bool, array, object)
    3. Detect required vs optional fields
    4. Extract enum values from error messages
    5. Detect formats (email, phone, date, uuid, url)
    6. Build JSON Schema specification
    7. Detect validation rules from errors
    """

    # Format patterns
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    UUID_PATTERN = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    DATE_PATTERN = r'^\d{4}-\d{2}-\d{2}$'
    DATETIME_PATTERN = r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}'
    PHONE_PATTERN = r'^\+?[\d\s\-\(\)]+$'
    URL_PATTERN = r'^https?://'

    def __init__(self, timeout: int = 30, samples_per_endpoint: int = 3):
        """
        Initialize Schema Inferencer

        Args:
            timeout: Request timeout
            samples_per_endpoint: Number of samples to collect per endpoint
        """
        self.timeout = httpx.Timeout(timeout)
        self.samples_per_endpoint = samples_per_endpoint
        self._session: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _get_session(self) -> httpx.AsyncClient:
        if self._session is None or self._session.is_closed:
            self._session = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True
            )
        return self._session

    async def close(self):
        if self._session and not self._session.is_closed:
            await self._session.aclose()

    async def infer_schemas(
        self,
        base_url: str,
        endpoints: List[Dict[str, Any]],
        auth_token: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Infer schemas for all endpoints

        Args:
            base_url: API base URL
            endpoints: List of discovered endpoints
            auth_token: Optional auth token

        Returns:
            Dictionary mapping endpoint keys to schemas
        """
        try:
            logger.info(f"[START] Schema inference for {len(endpoints)} endpoints")

            schemas = {}

            for endpoint in endpoints[:20]:  # Limit to first 20 to avoid too many requests
                endpoint_key = f"{endpoint['method']} {endpoint['path']}"

                try:
                    # Infer schema for this endpoint
                    schema = await self.infer_endpoint_schema(
                        base_url,
                        endpoint,
                        auth_token
                    )

                    if schema:
                        schemas[endpoint_key] = schema
                        logger.debug(f"[OK] Schema inferred for {endpoint_key}")

                except Exception as e:
                    logger.debug(f"[DEBUG] Failed to infer schema for {endpoint_key}: {e}")
                    continue

            logger.info(f"[OK] Inferred {len(schemas)} schemas")
            return schemas

        except Exception as e:
            logger.error(f"[ERROR] Schema inference failed: {e}")
            return {}

    async def infer_endpoint_schema(
        self,
        base_url: str,
        endpoint: Dict[str, Any],
        auth_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Infer schema for a single endpoint

        Returns schema with:
        - request_schema: JSON Schema for request body
        - response_schema: JSON Schema for response
        - required_fields: List of required fields
        - optional_fields: List of optional fields
        """
        try:
            method = endpoint['method'].upper()
            path = endpoint['path']
            url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"

            schema = {
                'endpoint': f"{method} {path}",
                'request_schema': None,
                'response_schema': None,
                'required_fields': [],
                'optional_fields': [],
                'enums': {},
                'formats': {}
            }

            # For GET requests, infer response schema
            if method == 'GET':
                response_samples = await self._collect_response_samples(
                    url,
                    method,
                    auth_token
                )

                if response_samples:
                    schema['response_schema'] = self._infer_schema_from_samples(response_samples)

            # For POST/PUT/PATCH, infer request schema from errors
            elif method in ['POST', 'PUT', 'PATCH']:
                # Try with empty body to get validation errors
                error_data = await self._get_validation_errors(url, method, auth_token)

                if error_data:
                    request_schema = self._infer_request_schema_from_errors(error_data)
                    schema['request_schema'] = request_schema
                    schema['required_fields'] = request_schema.get('required', [])

            return schema

        except Exception as e:
            logger.debug(f"[DEBUG] Error inferring endpoint schema: {e}")
            return None

    async def _collect_response_samples(
        self,
        url: str,
        method: str,
        auth_token: Optional[str] = None,
        num_samples: int = 3
    ) -> List[Dict[str, Any]]:
        """Collect multiple response samples from an endpoint"""
        samples = []
        session = await self._get_session()

        headers = {}
        if auth_token:
            headers['Authorization'] = f"Bearer {auth_token}"

        for i in range(num_samples):
            try:
                if method == 'GET':
                    response = await session.get(url, headers=headers)
                elif method == 'POST':
                    response = await session.post(url, json={}, headers=headers)
                else:
                    continue

                if response.status_code == 200:
                    try:
                        data = response.json()
                        samples.append(data)
                    except:
                        pass

            except:
                continue

        return samples

    async def _get_validation_errors(
        self,
        url: str,
        method: str,
        auth_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get validation errors by sending invalid requests"""
        try:
            session = await self._get_session()

            headers = {}
            if auth_token:
                headers['Authorization'] = f"Bearer {auth_token}"

            # Send empty body to trigger validation errors
            if method == 'POST':
                response = await session.post(url, json={}, headers=headers)
            elif method == 'PUT':
                response = await session.put(url, json={}, headers=headers)
            elif method == 'PATCH':
                response = await session.patch(url, json={}, headers=headers)
            else:
                return None

            # Look for 400/422 validation errors
            if response.status_code in [400, 422]:
                try:
                    return response.json()
                except:
                    return None

            return None

        except Exception as e:
            logger.debug(f"[DEBUG] Error getting validation errors: {e}")
            return None

    def _infer_schema_from_samples(
        self,
        samples: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Infer JSON Schema from multiple response samples

        Uses multiple samples to determine:
        - Which fields are always present (required)
        - Which fields are sometimes present (optional)
        - Field types
        - Field formats
        """
        if not samples:
            return {}

        # Collect field information across all samples
        field_info = defaultdict(lambda: {
            'types': Counter(),
            'formats': Counter(),
            'present_in': 0,
            'examples': []
        })

        total_samples = len(samples)

        for sample in samples:
            self._analyze_object(sample, field_info, "")

        # Build JSON Schema
        schema = {
            'type': 'object',
            'properties': {},
            'required': []
        }

        for field_path, info in field_info.items():
            # Determine if required (present in > 80% of samples)
            is_required = (info['present_in'] / total_samples) > 0.8

            # Get most common type
            most_common_type = info['types'].most_common(1)[0][0]

            # Get most common format
            format_str = None
            if info['formats']:
                most_common_format = info['formats'].most_common(1)[0][0]
                if most_common_format != 'none':
                    format_str = most_common_format

            # Build property schema
            prop_schema = {'type': most_common_type}
            if format_str:
                prop_schema['format'] = format_str

            if info['examples']:
                prop_schema['example'] = info['examples'][0]

            # Handle nested fields
            if '.' in field_path:
                # For now, just use top-level field
                field_name = field_path.split('.')[0]
            else:
                field_name = field_path

            schema['properties'][field_name] = prop_schema

            if is_required:
                if field_name not in schema['required']:
                    schema['required'].append(field_name)

        return schema

    def _analyze_object(
        self,
        obj: Any,
        field_info: Dict[str, Dict[str, Any]],
        prefix: str = ""
    ):
        """Recursively analyze object structure"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                field_path = f"{prefix}.{key}" if prefix else key

                field_info[field_path]['present_in'] += 1

                # Detect type
                value_type = self._detect_type(value)
                field_info[field_path]['types'][value_type] += 1

                # Detect format
                value_format = self._detect_format(value)
                field_info[field_path]['formats'][value_format] += 1

                # Store example
                if len(field_info[field_path]['examples']) < 3:
                    field_info[field_path]['examples'].append(value)

                # Recurse for nested objects
                if isinstance(value, dict):
                    self._analyze_object(value, field_info, field_path)
                elif isinstance(value, list) and value and isinstance(value[0], dict):
                    self._analyze_object(value[0], field_info, field_path)

        elif isinstance(obj, list):
            if obj and isinstance(obj[0], dict):
                self._analyze_object(obj[0], field_info, prefix)

    def _detect_type(self, value: Any) -> str:
        """Detect JSON Schema type"""
        if value is None:
            return 'null'
        elif isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'number'
        elif isinstance(value, list):
            return 'array'
        elif isinstance(value, dict):
            return 'object'
        elif isinstance(value, str):
            return 'string'
        else:
            return 'string'

    def _detect_format(self, value: Any) -> str:
        """Detect JSON Schema format"""
        if not isinstance(value, str):
            return 'none'

        value_str = str(value)

        # Check patterns
        if re.match(self.EMAIL_PATTERN, value_str):
            return 'email'
        elif re.match(self.UUID_PATTERN, value_str, re.IGNORECASE):
            return 'uuid'
        elif re.match(self.DATETIME_PATTERN, value_str):
            return 'date-time'
        elif re.match(self.DATE_PATTERN, value_str):
            return 'date'
        elif re.match(self.URL_PATTERN, value_str):
            return 'uri'
        elif re.match(self.PHONE_PATTERN, value_str) and len(value_str) > 8:
            return 'phone'
        else:
            return 'none'

    def _infer_request_schema_from_errors(
        self,
        error_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Infer request schema from validation error messages

        Common error formats:
        - {"field": ["Field is required"]}
        - {"errors": [{"field": "email", "message": "Invalid email"}]}
        - {"detail": [{"loc": ["body", "email"], "msg": "field required"}]}
        """
        schema = {
            'type': 'object',
            'properties': {},
            'required': []
        }

        try:
            # FastAPI/Pydantic style errors
            if 'detail' in error_data and isinstance(error_data['detail'], list):
                for error in error_data['detail']:
                    if isinstance(error, dict):
                        loc = error.get('loc', [])
                        msg = error.get('msg', '').lower()

                        if len(loc) >= 2:
                            field_name = loc[-1]

                            # Determine if required
                            if 'required' in msg or 'missing' in msg:
                                if field_name not in schema['required']:
                                    schema['required'].append(field_name)

                            # Try to infer type
                            field_type = self._infer_type_from_error_message(msg)

                            schema['properties'][field_name] = {'type': field_type}

            # Generic validation errors
            elif 'errors' in error_data:
                errors = error_data['errors']
                if isinstance(errors, dict):
                    for field, messages in errors.items():
                        if isinstance(messages, list) and messages:
                            msg = messages[0].lower()

                            if 'required' in msg:
                                if field not in schema['required']:
                                    schema['required'].append(field)

                            field_type = self._infer_type_from_error_message(msg)
                            schema['properties'][field] = {'type': field_type}

            # Simple field: message format
            elif isinstance(error_data, dict):
                for field, message in error_data.items():
                    if field not in ['error', 'message', 'status']:
                        msg = str(message).lower() if message else ''

                        if 'required' in msg:
                            if field not in schema['required']:
                                schema['required'].append(field)

                        field_type = self._infer_type_from_error_message(msg)
                        schema['properties'][field] = {'type': field_type}

        except Exception as e:
            logger.debug(f"[DEBUG] Error inferring from error message: {e}")

        return schema

    def _infer_type_from_error_message(self, message: str) -> str:
        """Infer field type from error message"""
        message = message.lower()

        if 'email' in message:
            return 'string'  # format: email
        elif 'integer' in message or 'number' in message:
            return 'integer'
        elif 'float' in message or 'decimal' in message:
            return 'number'
        elif 'boolean' in message or 'bool' in message:
            return 'boolean'
        elif 'array' in message or 'list' in message:
            return 'array'
        elif 'object' in message or 'dict' in message:
            return 'object'
        else:
            return 'string'  # Default to string
