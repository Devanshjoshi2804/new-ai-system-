"""
Dynamic Adapter Loader
Loads and executes generated API adapters at runtime
"""
import logging
import hashlib
from typing import Dict, Any, Optional
from src.infrastructure.security.code_sandbox import CodeSandbox

logger = logging.getLogger(__name__)


class AdapterLoader:
    """
    Loads and executes dynamically generated API adapters
    
    Uses secure sandbox to run generated code
    """
    
    def __init__(self):
        self.sandbox = CodeSandbox()
        self._adapter_cache: Dict[str, Any] = {}
    
    async def load_adapter(
        self,
        adapter_code: str,
        class_name: str,
        partner_id: str,
        api_credentials: Optional[Dict[str, str]] = None
    ) -> Any:
        """
        Load and instantiate an adapter class
        
        Args:
            adapter_code: Generated Python code
            class_name: Name of the adapter class
            partner_id: Partner identifier
            api_credentials: API authentication credentials
            
        Returns:
            Instantiated adapter object
        """
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(partner_id, class_name)
            
            # Check cache
            if cache_key in self._adapter_cache:
                logger.info(f"Adapter loaded from cache: {class_name}")
                return self._adapter_cache[cache_key]
            
            logger.info(f"Loading adapter: {class_name}")
            
            # Execute code in sandbox to get class
            result = await self.sandbox.execute_code(
                code=adapter_code,
                globals_dict={},
                timeout_seconds=5
            )
            
            # Get the class from result
            if class_name not in result:
                raise ValueError(f"Class {class_name} not found in generated code")
            
            adapter_class = result[class_name]
            
            # Instantiate adapter
            if api_credentials:
                adapter_instance = adapter_class(**api_credentials)
            else:
                adapter_instance = adapter_class()
            
            # Cache the instance
            self._adapter_cache[cache_key] = adapter_instance
            
            logger.info(f"Adapter loaded successfully: {class_name}")
            return adapter_instance
        
        except Exception as e:
            logger.error(f"Failed to load adapter: {e}")
            raise
    
    async def execute_adapter_method(
        self,
        adapter_code: str,
        class_name: str,
        method_name: str,
        partner_id: str,
        api_credentials: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Any:
        """
        Load adapter and execute a specific method
        
        Args:
            adapter_code: Generated Python code
            class_name: Name of adapter class
            method_name: Method to call
            partner_id: Partner identifier
            api_credentials: API credentials
            **kwargs: Method arguments
            
        Returns:
            Method execution result
        """
        try:
            logger.info(f"Executing {class_name}.{method_name}")
            
            # Load adapter
            adapter = await self.load_adapter(
                adapter_code=adapter_code,
                class_name=class_name,
                partner_id=partner_id,
                api_credentials=api_credentials
            )
            
            # Check if method exists
            if not hasattr(adapter, method_name):
                raise AttributeError(f"Method {method_name} not found in {class_name}")
            
            # Get method
            method = getattr(adapter, method_name)
            
            # Execute method in sandbox
            result = await self.sandbox.execute_function(
                func=method,
                **kwargs
            )
            
            logger.info(f"Method executed successfully: {method_name}")
            return result
        
        except Exception as e:
            logger.error(f"Failed to execute adapter method: {e}")
            raise
    
    def _generate_cache_key(self, partner_id: str, class_name: str) -> str:
        """Generate cache key for adapter"""
        key_str = f"{partner_id}:{class_name}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def clear_cache(self, partner_id: Optional[str] = None):
        """
        Clear adapter cache
        
        Args:
            partner_id: If specified, only clear adapters for this partner
        """
        if partner_id:
            keys_to_remove = [
                k for k in self._adapter_cache.keys()
                if k.startswith(partner_id)
            ]
            for key in keys_to_remove:
                del self._adapter_cache[key]
            logger.info(f"Cleared cache for partner: {partner_id}")
        else:
            self._adapter_cache.clear()
            logger.info("Cleared all adapter cache")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            "cached_adapters": len(self._adapter_cache),
            "memory_mb": 0  # TODO: Calculate actual memory usage
        }


# Global instance
_adapter_loader: Optional[AdapterLoader] = None


def get_adapter_loader() -> AdapterLoader:
    """Get global adapter loader instance"""
    global _adapter_loader
    if _adapter_loader is None:
        _adapter_loader = AdapterLoader()
    return _adapter_loader


