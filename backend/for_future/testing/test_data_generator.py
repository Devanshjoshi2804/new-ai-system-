"""
Test Data Generator - Generates realistic test data using AI and rules
"""
import logging
import random
import string
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)


class TestDataGenerator:
    """Generates test data for API testing using hybrid AI + rule-based approach"""
    
    def __init__(self, ai_provider=None, gemini_provider=None, flow_store=None):
        """
        Initialize test data generator
        
        Args:
            ai_provider: Optional AI provider (Groq/Gemini/Mistral) for AI-generated data
            gemini_provider: Deprecated, use ai_provider instead
            flow_store: Optional FlowVectorStore for context-aware generation
        """
        self.ai_provider = ai_provider or gemini_provider
        # Keep backward compatibility
        self.gemini_provider = self.ai_provider
        self.test_data_store = {}  # Store generated data for reuse
        self.flow_store = flow_store  # NEW: Flow DB for context
    
    async def generate_test_data_with_context(
        self,
        endpoint_key: str,
        parameters: List[Dict[str, Any]],
        test_data_store: Optional[Dict[str, Any]] = None,
        documentation_text: str = ""
    ) -> Dict[str, Any]:
        """
        Generate test data using Flow DB context (SMART GENERATION)
        
        This method uses:
        1. Flow DB to find credentials/tokens/IDs from previous tests
        2. AI provider to generate realistic data based on documentation
        3. Rule-based fallback for reliability
        
        Args:
            endpoint_key: Endpoint being tested (e.g., "POST /api/login")
            parameters: List of parameter specifications
            test_data_store: Optional store of previously generated data
            documentation_text: API documentation context
            
        Returns:
            Dictionary of generated test data
        """
        test_data = {}
        
        # Step 1: Query Flow DB for dependencies
        if self.flow_store:
            try:
                logger.info(f"🔍 Querying Flow DB for dependencies: {endpoint_key}")
                dependencies = await self.flow_store.query_for_dependencies(endpoint_key)
                credentials = await self.flow_store.query_for_credentials(endpoint_key)
                
                # Merge credentials into test data
                if credentials:
                    logger.info(f"✅ Using {len(credentials)} credentials from Flow DB")
                    test_data.update(credentials)
            except Exception as e:
                logger.warning(f"Failed to query Flow DB: {e}")
                dependencies = ""
                credentials = {}
        else:
            dependencies = ""
            credentials = {}
        
        # Step 2: Generate data for each parameter
        for param in parameters:
            param_name = param.get('name', '')
            
            # Skip if already have from credentials
            if param_name in test_data:
                logger.debug(f"Using existing data for {param_name}")
                continue
            
            param_type = param.get('type', 'string')
            required = param.get('required', False)
            description = param.get('description', '')
            
            # Check if we can reuse data from test_data_store
            if test_data_store and param_name in test_data_store:
                test_data[param_name] = test_data_store[param_name]
                logger.debug(f"Reusing data for {param_name}: {test_data[param_name]}")
                continue
            
            # Step 3: Try AI generation with context (IMPROVED PROMPT)
            if self.ai_provider and (dependencies or documentation_text):
                try:
                    # CRITICAL FIX: Improved prompt to EXTRACT examples from documentation
                    context = f"""
CRITICAL INSTRUCTIONS:
1. LOOK for EXAMPLE JSON request bodies in the documentation
2. EXTRACT the EXACT value for field '{param_name}' from the examples
3. DO NOT make up values - USE ONLY what you see in the documentation
4. If you find multiple examples, use the first complete one

Previous API Calls Context (use values from here if available):
{dependencies}

Documentation (LOOK FOR JSON EXAMPLES HERE):
{documentation_text[:3000]}

Target Endpoint: {endpoint_key}
Field to Extract: {param_name} (type: {param_type})
Field Description: {description}

Other fields already extracted:
{test_data}

CRITICAL: If you see an example request body in the documentation, extract the EXACT value for '{param_name}'.
Example: If docs show {{"email": "test@example.com"}}, use "test@example.com", not "user@domain.com"
"""
                    value = await self.ai_provider.infer_test_data(
                        field_schema=param,
                        context={'context_text': context, 'other_fields': test_data}
                    )
                    test_data[param_name] = value
                    logger.debug(f"AI extracted {param_name}: {value}")
                    continue
                except Exception as e:
                    logger.warning(f"AI generation failed for {param_name}: {e}")
            
            # Step 4: Fallback to rule-based
            test_data[param_name] = self._generate_rule_based_data(param)
            logger.debug(f"Rule-based {param_name}: {test_data[param_name]}")
        
        return test_data
    
    async def generate_test_data(
        self,
        parameters: List[Dict[str, Any]],
        test_data_store: Optional[Dict[str, Any]] = None,
        use_ai: bool = True
    ) -> Dict[str, Any]:
        """
        Generate test data for a set of parameters
        
        Args:
            parameters: List of parameter specifications
            test_data_store: Optional store of previously generated data
            use_ai: Whether to use AI for generation
            
        Returns:
            Dictionary of generated test data
        """
        test_data = {}
        
        for param in parameters:
            param_name = param.get('name', '')
            param_type = param.get('type', 'string')
            required = param.get('required', False)
            description = param.get('description', '')
            
            # Check if we can reuse data from previous tests
            if test_data_store and param_name in test_data_store:
                test_data[param_name] = test_data_store[param_name]
                logger.debug(f"Reusing data for {param_name}: {test_data[param_name]}")
                continue
            
            # Generate new data
            if use_ai and self.gemini_provider:
                try:
                    value = await self.gemini_provider.infer_test_data(
                        field_schema=param,
                        context={'other_fields': test_data}
                    )
                    test_data[param_name] = value
                except Exception as e:
                    logger.warning(f"AI data generation failed for {param_name}, using rule-based: {e}")
                    test_data[param_name] = self._generate_rule_based_data(param)
            else:
                test_data[param_name] = self._generate_rule_based_data(param)
        
        return test_data
    
    def _generate_rule_based_data(self, param: Dict[str, Any]) -> Any:
        """Generate test data using rule-based patterns"""
        param_name = param.get('name', '').lower()
        param_type = param.get('type', 'string').lower()
        description = param.get('description', '').lower()
        
        # Email patterns
        if 'email' in param_name or 'email' in description:
            return f"test_{self._random_string(8)}@yopmail.com"
        
        # Password patterns
        if 'password' in param_name or 'password' in description:
            return "Test@1234"
        
        # Phone/Mobile patterns
        if any(word in param_name for word in ['phone', 'mobile', 'contact']):
            return self._generate_phone_number()
        
        # Name patterns
        if 'name' in param_name and 'company' not in param_name:
            return f"Test {self._random_string(6).title()}"
        
        # Company name patterns
        if 'company' in param_name or 'organization' in param_name:
            return f"Test Company {self._random_string(4).upper()}"
        
        # Address patterns
        if 'address' in param_name or 'street' in param_name:
            return f"{random.randint(1, 999)} Test Street"
        
        # City patterns
        if 'city' in param_name:
            cities = ['Mumbai', 'Delhi', 'Bangalore', 'Pune', 'Hyderabad']
            return random.choice(cities)
        
        # State patterns
        if 'state' in param_name:
            states = ['Maharashtra', 'Delhi', 'Karnataka', 'Tamil Nadu', 'Gujarat']
            return random.choice(states)
        
        # Country patterns
        if 'country' in param_name:
            return 'India'
        
        # Postal/Zip code patterns
        if any(word in param_name for word in ['postal', 'zip', 'pincode', 'pin']):
            return '411014'  # Test pincode
        
        # GST patterns
        if 'gst' in param_name:
            return f"{self._random_string(15).upper()}"
        
        # Vendor code patterns
        if 'vendor' in param_name and 'code' in param_name:
            return "bhav19"  # QA vendor code
        
        # AWB number patterns
        if 'awb' in param_name or 'airway' in param_name:
            return f"bhav19{random.randint(1000000000, 9999999999)}"
        
        # Order ID patterns
        if 'order' in param_name and 'id' in param_name:
            return f"{random.randint(100000000, 999999999)}"
        
        # URL patterns
        if 'url' in param_name:
            return f"https://example.com/test/{self._random_string(10)}.pdf"
        
        # Date patterns
        if 'date' in param_name:
            date = datetime.now() + timedelta(days=random.randint(1, 30))
            return date.isoformat()
        
        # Currency patterns
        if 'currency' in param_name:
            return 'INR'
        
        # Amount/Price patterns
        if any(word in param_name for word in ['amount', 'price', 'cost', 'charge']):
            return round(random.uniform(100, 10000), 2)
        
        # Weight patterns
        if 'weight' in param_name:
            return random.randint(1, 100)
        
        # Dimension patterns (length, width, height)
        if any(word in param_name for word in ['length', 'width', 'height']):
            return random.randint(5, 50)
        
        # Boolean patterns
        if param_type in ['boolean', 'bool']:
            return True
        
        # Number patterns
        if param_type in ['number', 'integer', 'int', 'float']:
            return random.randint(1, 1000)
        
        # Default string
        return f"test_{self._random_string(8)}"
    
    def generate_test_variations(
        self,
        base_data: Dict[str, Any],
        parameters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate variations of test data for comprehensive testing
        
        Args:
            base_data: Base test data (happy path)
            parameters: Parameter specifications
            
        Returns:
            List of test data variations
        """
        variations = [base_data]  # Start with happy path
        
        # Generate variations with missing required fields
        for param in parameters:
            if param.get('required', False):
                param_name = param.get('name', '')
                # Create variation without this required field
                variation = {k: v for k, v in base_data.items() if k != param_name}
                variations.append(variation)
        
        # Generate variations with invalid data types
        for param_name, value in base_data.items():
            # Find parameter spec
            param_spec = next((p for p in parameters if p.get('name') == param_name), None)
            if not param_spec:
                continue
            
            param_type = param_spec.get('type', 'string').lower()
            
            # Generate invalid type variations
            if param_type in ['number', 'integer']:
                # Try string instead of number
                variation = base_data.copy()
                variation[param_name] = "not_a_number"
                variations.append(variation)
            elif param_type == 'string':
                # Try empty string
                variation = base_data.copy()
                variation[param_name] = ""
                variations.append(variation)
                
                # Try very long string
                variation = base_data.copy()
                variation[param_name] = "x" * 1000
                variations.append(variation)
        
        return variations
    
    def store_response_data(self, response: Dict[str, Any], endpoint: str):
        """
        Store ALL ID-like fields recursively (BUG #5 FIX)
        Previously only stored hardcoded field names, now extracts ALL IDs
        
        Args:
            response: API response data
            endpoint: Endpoint that generated this response
        """
        if not response:
            return
        
        def extract_ids(obj, prefix=''):
            """Recursively extract all ID-like fields"""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    # Match any field ending in Id, ID, Code, Token, Number, Key
                    if re.match(r'.*([Ii]d|[Cc]ode|[Tt]oken|[Nn]umber|[Kk]ey)$', key):
                        full_key = f"{prefix}{key}" if prefix else key
                        self.test_data_store[key] = value  # Store with simple key
                        if prefix:  # Also store with full path
                            self.test_data_store[full_key] = value
                        logger.debug(f"💾 Stored {full_key}: {value} from {endpoint}")
                    
                    # Recurse into nested objects/arrays
                    if isinstance(value, dict):
                        extract_ids(value, f"{prefix}{key}.")
                    elif isinstance(value, list) and value and isinstance(value[0], dict):
                        for item in value:
                            if isinstance(item, dict):
                                extract_ids(item, f"{prefix}{key}.")
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict):
                        extract_ids(item, prefix)
        
        # Check common wrapper fields
        for key in ['data', 'result', 'response']:
            if key in response and isinstance(response[key], dict):
                extract_ids(response[key])
        
        # Extract from root
        extract_ids(response)
    
    def get_stored_data(self, key: str) -> Optional[Any]:
        """Get stored data by key"""
        return self.test_data_store.get(key)
    
    def _random_string(self, length: int = 10) -> str:
        """Generate random string"""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
    def _generate_phone_number(self) -> str:
        """Generate random Indian phone number"""
        return f"{random.choice([6, 7, 8, 9])}{random.randint(100000000, 999999999)}"
    
    def extract_value_by_path(self, data: dict, json_path: str) -> Any:
        """
        Extract value from nested dict using JSON path notation
        
        Examples:
            data = {"data": {"user": {"id": 123}}}
            extract_value_by_path(data, "data.user.id") -> 123
            
            data = {"items": [{"id": 1}, {"id": 2}]}
            extract_value_by_path(data, "items.0.id") -> 1
        
        Args:
            data: Dictionary to extract from
            json_path: Dot-notation path (e.g., "data.token" or "items.0.id")
            
        Returns:
            Extracted value or None if path not found
        """
        if not json_path or not data:
            return None
        
        keys = json_path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            elif isinstance(value, list) and key.isdigit():
                idx = int(key)
                if 0 <= idx < len(value):
                    value = value[idx]
                else:
                    return None
            else:
                return None
        
        return value
    
    async def map_data_to_parameters(
        self,
        endpoint: Dict[str, Any],
        data_mappings: Dict[str, Any],
        test_data_store: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Automatically map stored data to endpoint parameters based on data mappings
        
        Args:
            endpoint: Endpoint specification
            data_mappings: Data mapping configuration from workflow analysis
            test_data_store: Stored data from previous requests
            
        Returns:
            Test data with intelligently mapped values
        """
        test_data = {}
        parameters = endpoint.get('parameters', [])
        
        logger.info(f"Mapping data for {endpoint.get('path')}: {len(data_mappings)} mappings available")
        
        for param in parameters:
            param_name = param.get('name')
            param_required = param.get('required', False)
            
            # Check if this parameter has a data mapping
            if param_name in data_mappings:
                mapping = data_mappings[param_name]
                source_endpoint = mapping.get('source_endpoint')
                source_path = mapping.get('source_path')
                
                logger.debug(f"Found mapping for {param_name}: {source_endpoint} -> {source_path}")
                
                # Get data from store
                if source_endpoint in test_data_store:
                    stored_response = test_data_store[source_endpoint]
                    value = self.extract_value_by_path(stored_response, source_path)
                    
                    if value:
                        test_data[param_name] = value
                        logger.info(f"✅ Mapped {param_name} = {value} from {source_endpoint}")
                    else:
                        logger.warning(f"⚠️ Could not extract {param_name} from {source_endpoint} using path {source_path}")
                        if param_required:
                            # Generate fallback value
                            test_data[param_name] = self._generate_rule_based_data(param)
                else:
                    logger.warning(f"⚠️ Source endpoint {source_endpoint} not in test data store yet")
                    if param_required:
                        test_data[param_name] = self._generate_rule_based_data(param)
            else:
                # No mapping found, generate value if required
                if param_required:
                    test_data[param_name] = self._generate_rule_based_data(param)
                    logger.debug(f"Generated value for {param_name}: {test_data[param_name]}")
        
        return test_data

