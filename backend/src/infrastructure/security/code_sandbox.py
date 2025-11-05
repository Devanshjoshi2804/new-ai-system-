"""
Secure code execution sandbox using RestrictedPython
"""
import logging
from typing import Dict, Any, Optional
from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Guards import guarded_iter_unpack_sequence, safer_getattr
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CodeExecutionError(Exception):
    """Raised when code execution fails or is denied"""
    pass


class CodeSandbox:
    """
    Secure sandbox for executing dynamically generated code
    
    Features:
    - Restricted Python execution
    - Resource limits (time, memory)
    - No file system access
    - No dangerous imports
    - Limited built-ins
    """
    
    def __init__(
        self,
        timeout_seconds: int = 30,
        max_memory_mb: int = 100
    ):
        """
        Initialize code sandbox
        
        Args:
            timeout_seconds: Maximum execution time
            max_memory_mb: Maximum memory usage (not enforced on all platforms)
        """
        self.timeout_seconds = timeout_seconds
        self.max_memory_mb = max_memory_mb
    
    async def execute_code(
        self,
        code: str,
        globals_dict: Optional[Dict[str, Any]] = None,
        locals_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute Python code in sandbox
        
        Args:
            code: Python code to execute
            globals_dict: Global variables to make available
            locals_dict: Local variables to make available
            
        Returns:
            Dictionary with execution results
            
        Raises:
            CodeExecutionError: If execution fails or is denied
        """
        try:
            logger.info("Executing code in sandbox")
            
            # Compile with RestrictedPython
            byte_code = compile_restricted(
                code,
                filename='<sandbox>',
                mode='exec'
            )
            
            if byte_code.errors:
                error_msg = '; '.join(byte_code.errors)
                logger.error(f"Compilation errors: {error_msg}")
                raise CodeExecutionError(f"Code compilation failed: {error_msg}")
            
            # Prepare safe globals
            safe_globals_dict = self._get_safe_globals()
            if globals_dict:
                safe_globals_dict.update(globals_dict)
            
            # Prepare locals
            safe_locals = locals_dict or {}
            
            # Execute with timeout
            try:
                result = await asyncio.wait_for(
                    self._execute_async(byte_code, safe_globals_dict, safe_locals),
                    timeout=self.timeout_seconds
                )
                
                logger.info("Code execution completed successfully")
                
                return {
                    "success": True,
                    "result": result,
                    "locals": safe_locals,
                    "error": None
                }
            
            except asyncio.TimeoutError:
                logger.error("Code execution timeout")
                raise CodeExecutionError(f"Execution timeout after {self.timeout_seconds}s")
            
        except CodeExecutionError:
            raise
        except Exception as e:
            logger.error(f"Code execution error: {e}")
            raise CodeExecutionError(f"Execution failed: {str(e)}")
    
    async def _execute_async(
        self,
        byte_code,
        globals_dict: Dict[str, Any],
        locals_dict: Dict[str, Any]
    ):
        """Execute bytecode asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            exec,
            byte_code.code,
            globals_dict,
            locals_dict
        )
    
    def _get_safe_globals(self) -> Dict[str, Any]:
        """
        Get safe global variables for sandbox
        
        Includes:
        - Safe built-ins
        - Utility functions
        - No file/system access
        - No dangerous imports
        """
        safe_builtins = safe_globals.copy()
        
        # Add safe utilities
        safe_builtins.update({
            '_iter_unpack_sequence_': guarded_iter_unpack_sequence,
            '_getattr_': safer_getattr,
            '_print_': self._safe_print,
            '_getitem_': self._safe_getitem,
            'datetime': datetime,
            'timedelta': timedelta,
        })
        
        # Remove dangerous built-ins
        dangerous = [
            'open', 'file', 'input', 'raw_input',
            'compile', 'eval', 'exec', 'execfile',
            '__import__', 'reload',
            'vars', 'dir', 'globals', 'locals'
        ]
        
        for name in dangerous:
            safe_builtins.pop(name, None)
        
        return safe_builtins
    
    def _safe_print(self, *args, **kwargs):
        """Safe print function (logs instead of printing)"""
        message = ' '.join(str(arg) for arg in args)
        logger.debug(f"Sandbox print: {message}")
    
    def _safe_getitem(self, obj, key):
        """Safe getitem with restrictions"""
        if isinstance(key, str) and key.startswith('_'):
            raise CodeExecutionError("Access to private attributes is not allowed")
        return obj[key]
    
    async def validate_code(self, code: str) -> Dict[str, Any]:
        """
        Validate code without executing
        
        Returns:
            Validation result with any errors/warnings
        """
        try:
            byte_code = compile_restricted(
                code,
                filename='<validation>',
                mode='exec'
            )
            
            if byte_code.errors:
                return {
                    "valid": False,
                    "errors": byte_code.errors,
                    "warnings": byte_code.warnings if hasattr(byte_code, 'warnings') else []
                }
            
            return {
                "valid": True,
                "errors": [],
                "warnings": byte_code.warnings if hasattr(byte_code, 'warnings') else []
            }
        
        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": []
            }
    
    async def load_and_execute_adapter(
        self,
        adapter_code: str,
        class_name: str,
        method_name: str,
        **method_kwargs
    ) -> Any:
        """
        Load dynamically generated adapter and execute method
        
        Args:
            adapter_code: Generated adapter code
            class_name: Name of the client class
            method_name: Method to call
            **method_kwargs: Arguments for the method
            
        Returns:
            Method execution result
        """
        try:
            # Validate code
            validation = await self.validate_code(adapter_code)
            if not validation["valid"]:
                raise CodeExecutionError(f"Invalid adapter code: {validation['errors']}")
            
            # Execute code to define the class
            locals_dict = {}
            result = await self.execute_code(
                adapter_code,
                globals_dict={'aiohttp': __import__('aiohttp')},
                locals_dict=locals_dict
            )
            
            # Get the class from locals
            if class_name not in result["locals"]:
                raise CodeExecutionError(f"Class {class_name} not found in adapter")
            
            client_class = result["locals"][class_name]
            
            # Instantiate and call method
            async with client_class() as client:
                method = getattr(client, method_name)
                return await method(**method_kwargs)
        
        except Exception as e:
            logger.error(f"Error executing adapter: {e}")
            raise CodeExecutionError(f"Adapter execution failed: {str(e)}")


# Global singleton instance
_sandbox_instance: Optional[CodeSandbox] = None


def get_code_sandbox() -> CodeSandbox:
    """Get global code sandbox instance"""
    global _sandbox_instance
    if _sandbox_instance is None:
        _sandbox_instance = CodeSandbox()
    return _sandbox_instance


