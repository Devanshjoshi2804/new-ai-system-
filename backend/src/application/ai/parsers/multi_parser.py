"""
Multi-Format Parser
Supports: OpenAPI, Swagger, JSON (generic + JSONLoader with jq), YAML, cURL text
"""
import logging
import json
import yaml
import re
from typing import List, Dict, Any, Optional
from fastapi import UploadFile

from src.application.ai.parsers.base_parser import BaseParser
from src.domain.value_objects.doc_format import DocFormat
from src.domain.value_objects.api_schema import APISpecification, AuthConfig, AuthType
from src.domain.value_objects.api_endpoint import APIEndpoint, HTTPMethod, APIParameter, ParameterLocation

logger = logging.getLogger(__name__)


class MultiParser(BaseParser):
    """Parser for multiple documentation formats: OpenAPI, JSON, YAML, cURL"""
    
    def __init__(self):
        from src.infrastructure.ai.providers.mistral_provider import MistralProvider
        self.mistral = MistralProvider()
    
    @property
    def supported_formats(self) -> list[DocFormat]:
        return [DocFormat.OPENAPI_30, DocFormat.OPENAPI_31, DocFormat.SWAGGER_20]
    
    async def can_parse(self, file: UploadFile) -> bool:
        """Check if file can be parsed"""
        try:
            content = await self.extract_text(file)
            
            # Try JSON
            try:
                data = json.loads(content)
                return True  # Can parse any JSON
            except json.JSONDecodeError:
                pass
            
            # Try YAML
            try:
                data = yaml.safe_load(content)
                if data and isinstance(data, dict):
                    return True
            except yaml.YAMLError:
                pass
            
            # Check if it's cURL commands
            if 'curl ' in content.lower():
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error checking format: {e}")
            return False
    
    async def detect_format(self, file: UploadFile) -> tuple[DocFormat, float]:
        """Detect format type"""
        try:
            content = await self.extract_text(file)
            
            # Try JSON first
            try:
                data = json.loads(content)
                
                # Check for OpenAPI
                if 'openapi' in data:
                    version = data.get('openapi', '')
                    if version.startswith('3.0'):
                        return DocFormat.OPENAPI_30, 0.99
                    elif version.startswith('3.1'):
                        return DocFormat.OPENAPI_31, 0.99
                
                # Check for Swagger
                if 'swagger' in data:
                    return DocFormat.SWAGGER_20, 0.99
                
                # Generic JSON
                return DocFormat.OPENAPI_30, 0.7  # Default to OpenAPI for processing
            
            except json.JSONDecodeError:
                pass
            
            # Try YAML
            try:
                data = yaml.safe_load(content)
                if isinstance(data, dict):
                    if 'openapi' in data:
                        version = data.get('openapi', '')
                        if version.startswith('3.0'):
                            return DocFormat.OPENAPI_30, 0.99
                        elif version.startswith('3.1'):
                            return DocFormat.OPENAPI_31, 0.99
                    if 'swagger' in data:
                        return DocFormat.SWAGGER_20, 0.99
                    
                    # Generic YAML
                    return DocFormat.OPENAPI_30, 0.7
            except yaml.YAMLError:
                pass
        
        except Exception as e:
            logger.error(f"Error detecting format: {e}")
        
        return DocFormat.UNKNOWN, 0.0
    
    async def analyze_extracted_text(self, extracted_text_data: Dict[str, Any]) -> APISpecification:
        """
        Analyze already-extracted text with Mistral AI to extract API specification
        This is called separately after text extraction via the /analyze endpoint
        Uses the same AI analysis as PDFParser
        """
        import asyncio
        from mistralai import Mistral
        
        try:
            document_text = extracted_text_data.get("full_text", "")
            raw_data = extracted_text_data.get("raw_data", {})
            
            logger.info(f"[INFO] Analyzing extracted text ({len(document_text)} chars) with Mistral AI...")
            
            # Use PDFParser's extraction logic for consistency
            from src.application.ai.parsers.pdf_parser import PDFParser
            pdf_parser = PDFParser()
            
            # Analyze with Mistral AI to extract API specification
            api_data = await pdf_parser._extract_api_specification_from_text(document_text)
            
            # Convert to APISpecification object
            api_spec = pdf_parser._convert_to_api_spec(api_data)
            
            # Add extracted text metadata to schemas
            if not api_spec.schemas:
                api_spec.schemas = {}
            
            api_spec.schemas["extracted_text"] = {
                "full_text": document_text,
                "raw_data": raw_data,
                "total_characters": len(document_text),
                "extraction_method": "MultiParser",
                "ai_analysis_completed": True
            }
            
            logger.info(f"[OK] AI analysis complete: {len(api_spec.endpoints)} endpoints found")
            
            return api_spec
            
        except Exception as e:
            logger.error(f"[ERROR] Error analyzing text: {e}")
            raise ValueError(f"Failed to analyze text: {str(e)}")
    
    async def parse(self, file: UploadFile) -> APISpecification:
        """Parse the file based on its content"""
        content = await self.extract_text(file)
        
        logger.info(f"[FILE] Parsing file: {file.filename}")
        
        # Try to parse as JSON
        try:
            data = json.loads(content)
            logger.info("[OK] Detected JSON format")
            return await self._parse_json_data(data, file.filename)
        except json.JSONDecodeError:
            pass
        
        # Try to parse as YAML
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                logger.info("[OK] Detected YAML format")
                return await self._parse_yaml_data(data, file.filename)
        except yaml.YAMLError:
            pass
        
        # Try to parse as cURL commands
        if 'curl ' in content.lower():
            logger.info("[OK] Detected cURL format")
            return await self._parse_curl_text(content)
        
        raise ValueError(f"Unable to parse file format for: {file.filename}")
    
    async def _parse_json_data(self, data: Dict[str, Any], filename: str) -> APISpecification:
        """Parse JSON data - can be OpenAPI, Swagger, or generic JSON"""
        
        # ALL JSON files (including OpenAPI/Swagger) should extract text first
        # AI analysis will be triggered separately via /analyze endpoint
        
        if 'openapi' in data or 'swagger' in data:
            logger.info("[SEARCH] Detected OpenAPI/Swagger - extracting text for AI analysis")
        elif 'info' in data and 'item' in data:
            logger.info("[SEARCH] Detected collection-style JSON - extracting text for AI analysis")
        else:
            logger.info("[SEARCH] Parsing as generic JSON - extracting raw text")
        
        # For ALL JSON, extract text and wait for AI analysis
        return await self._extract_json_text(data, filename)
    
    async def _parse_yaml_data(self, data: Dict[str, Any], filename: str) -> APISpecification:
        """Parse YAML data"""
        
        # ALL YAML files (including OpenAPI/Swagger) should extract text first
        # AI analysis will be triggered separately via /analyze endpoint
        
        if 'openapi' in data or 'swagger' in data:
            logger.info("[SEARCH] Detected OpenAPI/Swagger YAML - extracting text for AI analysis")
        else:
            logger.info("[SEARCH] Parsing as generic YAML - extracting raw text")
        
        # For ALL YAML, extract text and wait for AI analysis
        return await self._extract_yaml_text(data, filename)
    
    def _parse_openapi_swagger(self, spec_data: Dict[str, Any]) -> APISpecification:
        """Parse OpenAPI 3.x or Swagger 2.0 specification"""
        
        # Extract basic info
        info = spec_data.get('info', {})
        title = info.get('title', 'Unnamed API')
        version = info.get('version', '1.0.0')
        description = info.get('description')
        
        # Extract servers (OpenAPI 3.x) or host/basePath (Swagger 2.0)
        if 'servers' in spec_data:
            servers = spec_data.get('servers', [])
            base_url = servers[0]['url'] if servers else 'https://api.example.com'
            server_urls = [s['url'] for s in servers]
        elif 'host' in spec_data:
            # Swagger 2.0
            host = spec_data.get('host', 'api.example.com')
            base_path = spec_data.get('basePath', '')
            schemes = spec_data.get('schemes', ['https'])
            base_url = f"{schemes[0]}://{host}{base_path}"
            server_urls = [base_url]
        else:
            base_url = 'https://api.example.com'
            server_urls = [base_url]
        
        # Extract security schemes
        if 'openapi' in spec_data:
            auth_config = self._parse_auth(spec_data.get('components', {}).get('securitySchemes', {}))
        else:
            # Swagger 2.0
            auth_config = self._parse_swagger_auth(spec_data.get('securityDefinitions', {}))
        
        # Extract endpoints
        endpoints = self._parse_paths(spec_data.get('paths', {}))
        
        # Extract schemas
        if 'openapi' in spec_data:
            schemas = spec_data.get('components', {}).get('schemas', {})
        else:
            schemas = spec_data.get('definitions', {})
        
        # Extract webhooks (OpenAPI 3.1+)
        webhooks = spec_data.get('webhooks', {})
        
        return APISpecification(
            title=title,
            version=version,
            description=description,
            base_url=base_url,
            servers=server_urls,
            endpoints=endpoints,
            auth=auth_config,
            schemas=schemas,
            webhooks=webhooks,
            contact=info.get('contact'),
            license=info.get('license'),
            external_docs=spec_data.get('externalDocs')
        )
    
    async def _extract_json_text(self, data: Dict[str, Any], filename: str) -> APISpecification:
        """Extract text from generic JSON file - AI analysis comes later"""
        
        # Convert JSON to readable text format
        json_text = json.dumps(data, indent=2, ensure_ascii=False)
        full_text = f"JSON API Documentation from {filename}\n\n{json_text}"
        
        logger.info(f"[OK] Extracted {len(full_text)} characters from JSON file")
        
        return APISpecification(
            title=f"API from {filename} (Text Extracted)",
            version="1.0.0",
            description=f"Text extraction completed from JSON file. Click 'Analyze with AI' to extract endpoints.",
            base_url="",
            endpoints=[],  # No endpoints yet
            auth=None,
            schemas={
                "extracted_text": {
                    "full_text": full_text,
                    "raw_data": data,
                    "total_characters": len(full_text),
                    "extraction_method": "JSON",
                    "ai_analysis_pending": True
                }
            }
        )
    
    async def _extract_yaml_text(self, data: Dict[str, Any], filename: str) -> APISpecification:
        """Extract text from generic YAML file - AI analysis comes later"""
        
        # Convert YAML to readable text format
        yaml_text = yaml.dump(data, default_flow_style=False, allow_unicode=True)
        full_text = f"YAML API Documentation from {filename}\n\n{yaml_text}"
        
        logger.info(f"[OK] Extracted {len(full_text)} characters from YAML file")
        
        return APISpecification(
            title=f"API from {filename} (Text Extracted)",
            version="1.0.0",
            description=f"Text extraction completed from YAML file. Click 'Analyze with AI' to extract endpoints.",
            base_url="",
            endpoints=[],  # No endpoints yet
            auth=None,
            schemas={
                "extracted_text": {
                    "full_text": full_text,
                    "raw_data": data,
                    "total_characters": len(full_text),
                    "extraction_method": "YAML",
                    "ai_analysis_pending": True
                }
            }
        )
    
    async def _parse_curl_text(self, content: str) -> APISpecification:
        """Parse cURL commands from text - extract text only, AI analysis comes later"""
        
        logger.info("[SEARCH] Extracting text from cURL commands...")
        
        # Convert cURL commands to readable text for AI analysis
        full_text = f"cURL API Documentation\n\n{content}"
        
        logger.info(f"[OK] Extracted {len(full_text)} characters from cURL text")
        
        return APISpecification(
            title="API from cURL commands (Text Extracted)",
            version="1.0.0",
            description=f"Text extraction completed. {content.count('curl ')} cURL commands found. Click 'Analyze with AI' to extract endpoints.",
            base_url="",
            endpoints=[],  # No endpoints yet
            auth=None,
            schemas={
                "extracted_text": {
                    "full_text": full_text,
                    "raw_data": {"curl_commands": content},
                    "total_characters": len(full_text),
                    "extraction_method": "cURL",
                    "ai_analysis_pending": True
                }
            }
        )
    
    def _parse_curl_command(self, curl_command: str) -> Optional[APIEndpoint]:
        """Parse a single cURL command"""
        try:
            # Extract HTTP method
            method = "GET"  # Default
            if '-X' in curl_command or '--request' in curl_command:
                method_match = re.search(r'-X\s+([A-Z]+)|--request\s+([A-Z]+)', curl_command)
                if method_match:
                    method = method_match.group(1) or method_match.group(2)
            
            # Extract URL
            url_match = re.search(r'(https?://[^\s\'"]+)', curl_command)
            if not url_match:
                return None
            
            url = url_match.group(1)
            
            # Extract headers
            headers = re.findall(r'-H\s+["\']([^:]+):\s*([^"\']+)["\']', curl_command)
            
            # Extract data
            data_match = re.search(r'(?:-d|--data)\s+["\']([^"\']+)["\']', curl_command)
            request_body = None
            if data_match:
                try:
                    request_body = json.loads(data_match.group(1))
                except:
                    request_body = {"raw": data_match.group(1)}
            
            # Create endpoint
            return APIEndpoint(
                path=url,
                method=HTTPMethod(method),
                summary=f"{method} request to {url}",
                description=f"Extracted from cURL: {curl_command[:100]}...",
                parameters=[],
                request_body_schema=request_body,
                auth_required='Authorization' in [h[0] for h in headers]
            )
        
        except Exception as e:
            logger.warning(f"Error parsing cURL command: {e}")
            return None
    
    def _extract_endpoints_from_json(self, data: Dict[str, Any], prefix: str = "") -> List[APIEndpoint]:
        """Try to extract endpoint-like structures from generic JSON/YAML"""
        endpoints = []
        
        # Look for common patterns like "endpoints", "routes", "apis", "paths"
        for key in ['endpoints', 'routes', 'apis', 'paths', 'methods']:
            if key in data and isinstance(data[key], (list, dict)):
                if isinstance(data[key], list):
                    for idx, item in enumerate(data[key]):
                        if isinstance(item, dict):
                            endpoint = self._json_item_to_endpoint(item, f"{prefix}/{key}/{idx}")
                            if endpoint:
                                endpoints.append(endpoint)
                elif isinstance(data[key], dict):
                    for path, details in data[key].items():
                        if isinstance(details, dict):
                            endpoint = self._json_item_to_endpoint(details, path)
                            if endpoint:
                                endpoints.append(endpoint)
        
        return endpoints
    
    def _json_item_to_endpoint(self, item: Dict[str, Any], default_path: str) -> Optional[APIEndpoint]:
        """Convert a JSON item to an APIEndpoint"""
        try:
            # Try to extract path
            path = item.get('path') or item.get('url') or item.get('route') or item.get('endpoint') or default_path
            
            # Try to extract method
            method_str = item.get('method') or item.get('type') or item.get('verb') or 'GET'
            method = HTTPMethod(method_str.upper())
            
            # Extract description/summary
            summary = item.get('summary') or item.get('title') or item.get('name') or f"Endpoint: {path}"
            description = item.get('description') or item.get('desc') or ''
            
            return APIEndpoint(
                path=path,
                method=method,
                summary=summary,
                description=description,
                parameters=[],
                request_body_schema=item.get('request') or item.get('body'),
                response_schema=item.get('response'),
                auth_required=bool(item.get('auth') or item.get('authenticated'))
            )
        except Exception as e:
            logger.warning(f"Could not convert JSON item to endpoint: {e}")
            return None
    
    
    def _parse_auth(self, security_schemes: Dict[str, Any]) -> Optional[AuthConfig]:
        """Parse OpenAPI 3.x authentication configuration"""
        if not security_schemes:
            return None
        
        # Get first security scheme
        scheme_name, scheme_data = next(iter(security_schemes.items()))
        scheme_type = scheme_data.get('type', '')
        
        if scheme_type == 'apiKey':
            return AuthConfig(
                type=AuthType.API_KEY,
                header_name=scheme_data.get('name'),
                scheme=scheme_data.get('in')
            )
        elif scheme_type == 'http':
            scheme = scheme_data.get('scheme', '').lower()
            if scheme == 'bearer':
                return AuthConfig(type=AuthType.BEARER_TOKEN, scheme='bearer')
            elif scheme == 'basic':
                return AuthConfig(type=AuthType.BASIC_AUTH, scheme='basic')
        elif scheme_type == 'oauth2':
            return AuthConfig(
                type=AuthType.OAUTH2,
                flows=scheme_data.get('flows')
            )
        
        return AuthConfig(type=AuthType.CUSTOM)
    
    def _parse_swagger_auth(self, security_definitions: Dict[str, Any]) -> Optional[AuthConfig]:
        """Parse Swagger 2.0 authentication configuration"""
        if not security_definitions:
            return None
        
        # Get first security definition
        scheme_name, scheme_data = next(iter(security_definitions.items()))
        scheme_type = scheme_data.get('type', '')
        
        if scheme_type == 'apiKey':
            return AuthConfig(
                type=AuthType.API_KEY,
                header_name=scheme_data.get('name'),
                scheme=scheme_data.get('in')
            )
        elif scheme_type == 'basic':
            return AuthConfig(type=AuthType.BASIC_AUTH, scheme='basic')
        elif scheme_type == 'oauth2':
            return AuthConfig(
                type=AuthType.OAUTH2,
                flows={}
            )
        
        return AuthConfig(type=AuthType.CUSTOM)
    
    def _parse_paths(self, paths: Dict[str, Any]) -> List[APIEndpoint]:
        """Parse API paths/endpoints"""
        endpoints = []
        
        for path, path_item in paths.items():
            # Parse each HTTP method
            for method in ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']:
                if method in path_item:
                    operation = path_item[method]
                    endpoint = self._parse_operation(path, method.upper(), operation)
                    endpoints.append(endpoint)
        
        return endpoints
    
    def _parse_operation(self, path: str, method: str, operation: Dict[str, Any]) -> APIEndpoint:
        """Parse single operation"""
        # Extract parameters
        parameters = []
        for param in operation.get('parameters', []):
            param_location = param.get('in', 'query')
            try:
                location = ParameterLocation(param_location)
            except ValueError:
                location = ParameterLocation.QUERY
            
            parameters.append(APIParameter(
                name=param.get('name', ''),
                location=location,
                required=param.get('required', False),
                type=param.get('schema', {}).get('type') or param.get('type', 'string'),
                description=param.get('description'),
                example=param.get('example')
            ))
        
        # Extract request body
        request_body = operation.get('requestBody')
        request_schema = None
        if request_body:
            content = request_body.get('content', {})
            if content:
                first_content = next(iter(content.values()))
                request_schema = first_content.get('schema')
        
        # Extract response schema
        responses = operation.get('responses', {})
        response_schema = None
        for status_code in ['200', '201', '202']:
            if status_code in responses:
                content = responses[status_code].get('content', {})
                if content:
                    first_content = next(iter(content.values()))
                    response_schema = first_content.get('schema')
                    break
        
        # Check if auth is required
        auth_required = 'security' in operation or operation.get('security') != []
        
        return APIEndpoint(
            path=path,
            method=HTTPMethod(method),
            operation_id=operation.get('operationId'),
            summary=operation.get('summary'),
            description=operation.get('description'),
            parameters=parameters,
            request_body_schema=request_schema,
            response_schema=response_schema,
            auth_required=auth_required,
            tags=operation.get('tags', [])
        )



