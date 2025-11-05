"""
Dynamic LangChain tool generator
Converts API endpoints into LangChain tools that AI agents can use
"""
import logging
from typing import Dict, Any, Optional, Callable
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, StructuredTool

from src.domain.value_objects.api_endpoint import APIEndpoint, ParameterLocation
from src.infrastructure.security.code_sandbox import get_code_sandbox

logger = logging.getLogger(__name__)


class ToolGenerator:
    """
    Generates LangChain tools from API endpoints
    
    These tools allow AI agents to call real partner APIs
    """
    
    def __init__(self):
        self.sandbox = get_code_sandbox()
    
    async def generate_tool_from_endpoint(
        self,
        endpoint: APIEndpoint,
        adapter_code: str,
        adapter_class_name: str,
        partner_id: str,
        api_credentials: Optional[Dict[str, str]] = None
    ) -> BaseTool:
        """
        Convert API endpoint into a LangChain tool
        
        Args:
            endpoint: API endpoint specification
            adapter_code: Generated adapter code
            adapter_class_name: Name of the adapter class
            partner_id: Partner identifier
            api_credentials: API authentication credentials
            
        Returns:
            LangChain tool that agents can use
        """
        try:
            logger.info(f"Generating tool for endpoint: {endpoint.method} {endpoint.path}")
            
            # Generate tool name (sanitized)
            tool_name = self._generate_tool_name(endpoint)
            
            # Generate tool description
            tool_description = self._generate_tool_description(endpoint)
            
            # Generate input schema
            input_schema = self._generate_input_schema(endpoint)
            
            # Create the tool function
            tool_func = await self._create_tool_function(
                endpoint,
                adapter_code,
                adapter_class_name,
                api_credentials
            )
            
            # Create structured tool
            tool = StructuredTool(
                name=tool_name,
                description=tool_description,
                func=tool_func,
                args_schema=input_schema,
                coroutine=tool_func  # For async support
            )
            
            logger.info(f"Tool created: {tool_name}")
            return tool
        
        except Exception as e:
            logger.error(f"Error generating tool: {e}")
            raise
    
    def _generate_tool_name(self, endpoint: APIEndpoint) -> str:
        """Generate a valid tool name"""
        # Clean path: /api/v1/bookings/create -> bookings_create
        path_parts = [p for p in endpoint.path.split('/') if p and not p.startswith('{')]
        path_name = '_'.join(path_parts).lower()
        
        # Add method prefix
        method = endpoint.method.value.lower()
        
        # Combine
        name = f"{method}_{path_name}"
        
        # Remove special characters
        name = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
        
        return name
    
    def _generate_tool_description(self, endpoint: APIEndpoint) -> str:
        """Generate tool description for AI agent"""
        description = endpoint.summary or f"{endpoint.method} {endpoint.path}"
        
        if endpoint.description:
            description += f"\n\n{endpoint.description}"
        
        # Add parameter information
        if endpoint.parameters:
            required_params = [p for p in endpoint.parameters if p.required]
            if required_params:
                param_names = ', '.join(p.name for p in required_params)
                description += f"\n\nRequired parameters: {param_names}"
        
        # Add authentication info
        if endpoint.auth_required:
            description += "\n\nAuthentication: Required"
        
        return description
    
    def _generate_input_schema(self, endpoint: APIEndpoint) -> type[BaseModel]:
        """
        Generate Pydantic model for tool inputs
        """
        # Collect all parameters
        fields = {}
        
        for param in endpoint.parameters:
            # Determine field type
            field_type = str
            if param.type == 'integer':
                field_type = int
            elif param.type == 'number':
                field_type = float
            elif param.type == 'boolean':
                field_type = bool
            
            # Make optional if not required
            if not param.required:
                field_type = Optional[field_type]
            
            # Create field
            field_kwargs = {
                'description': param.description or f"{param.name} parameter"
            }
            
            if not param.required:
                field_kwargs['default'] = None
            
            fields[param.name] = (field_type, Field(**field_kwargs))
        
        # Add body field if endpoint has request body
        if endpoint.request_body_schema:
            fields['body'] = (Optional[Dict[str, Any]], Field(
                default=None,
                description="Request body data"
            ))
        
        # Create dynamic Pydantic model
        model = type(
            f"{self._generate_tool_name(endpoint)}_input",
            (BaseModel,),
            {'__annotations__': {k: v[0] for k, v in fields.items()},
             **{k: v[1] for k, v in fields.items()}}
        )
        
        return model
    
    async def _create_tool_function(
        self,
        endpoint: APIEndpoint,
        adapter_code: str,
        adapter_class_name: str,
        api_credentials: Optional[Dict[str, str]]
    ) -> Callable:
        """
        Create the actual function that the tool will execute
        
        This function will call the partner's API via the generated adapter
        """
        
        async def tool_function(**kwargs) -> str:
            """
            Dynamically generated tool function
            Calls partner API via generated adapter
            """
            try:
                logger.info(f"Tool executing: {endpoint.method} {endpoint.path}")
                logger.debug(f"Tool input: {kwargs}")
                
                # Load and execute adapter
                result = await self.sandbox.load_and_execute_adapter(
                    adapter_code=adapter_code,
                    class_name=adapter_class_name,
                    method_name=self._get_adapter_method_name(endpoint),
                    **kwargs
                )
                
                logger.info(f"Tool execution successful")
                
                # Return formatted result
                import json
                return json.dumps(result, indent=2)
            
            except Exception as e:
                error_msg = f"Tool execution failed: {str(e)}"
                logger.error(error_msg)
                return json.dumps({"error": error_msg})
        
        return tool_function
    
    def _get_adapter_method_name(self, endpoint: APIEndpoint) -> str:
        """Get the method name in the generated adapter"""
        # This should match the method naming in adapter_generator.py
        path_clean = endpoint.path.replace('/', '_').replace('{', '').replace('}', '').strip('_').lower()
        method = endpoint.method.value.lower()
        return f"{path_clean}_{method}"
    
    async def generate_tools_from_workflow(
        self,
        workflow_endpoints: list[APIEndpoint],
        adapter_code: str,
        adapter_class_name: str,
        partner_id: str,
        api_credentials: Optional[Dict[str, str]] = None
    ) -> list[BaseTool]:
        """
        Generate multiple tools from a workflow
        
        Args:
            workflow_endpoints: List of endpoints in the workflow
            adapter_code: Generated adapter code
            adapter_class_name: Name of adapter class
            partner_id: Partner identifier
            api_credentials: API credentials
            
        Returns:
            List of LangChain tools
        """
        tools = []
        
        for endpoint in workflow_endpoints:
            try:
                tool = await self.generate_tool_from_endpoint(
                    endpoint,
                    adapter_code,
                    adapter_class_name,
                    partner_id,
                    api_credentials
                )
                tools.append(tool)
            except Exception as e:
                logger.warning(f"Failed to generate tool for {endpoint.path}: {e}")
        
        logger.info(f"Generated {len(tools)} tools from workflow")
        return tools


