"""
Test Executor - Executes API tests with retry logic and result capture
"""
import logging
import time
import asyncio
from typing import Dict, Any, Optional, Tuple
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)


class TestExecutor:
    """Executes API tests with exponential backoff retry logic"""
    
    def __init__(
        self,
        max_retries: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 32.0,
        timeout: int = 30
    ):
        """
        Initialize test executor
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries
            timeout: Request timeout in seconds
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.timeout = timeout
    
    async def execute_test(
        self,
        endpoint: Dict[str, Any],
        test_data: Dict[str, Any],
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        attempt: int = 1
    ) -> Dict[str, Any]:
        """
        Execute a single test with retry logic
        
        Args:
            endpoint: Endpoint specification
            test_data: Test data to send
            base_url: Base URL for the API
            headers: Optional HTTP headers
            attempt: Current attempt number
            
        Returns:
            Test result dictionary
        """
        method = endpoint.get('method', 'GET').upper()
        path = endpoint.get('path', '')
        full_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        
        # Replace path parameters
        for key, value in test_data.items():
            if f"{{{key}}}" in full_url:
                full_url = full_url.replace(f"{{{key}}}", str(value))
        
        # Prepare headers
        request_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if headers:
            request_headers.update(headers)
        
        # Prepare request data
        if method in ['GET', 'DELETE']:
            # Use query parameters
            params = test_data
            data = None
        else:
            # Use request body
            params = None
            data = test_data
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=full_url,
                    params=params,
                    json=data,
                    headers=request_headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    execution_time = time.time() - start_time
                    
                    # Read response
                    try:
                        response_data = await response.json()
                    except:
                        response_data = {"text": await response.text()}
                    
                    response_headers = dict(response.headers)
                    
                    # Determine if test passed
                    status_code = response.status
                    is_success = 200 <= status_code < 300
                    
                    result = {
                        "status": "passed" if is_success else "failed",
                        "attempt_number": attempt,
                        "request_data": test_data,
                        "request_headers": request_headers,
                        "response_data": response_data,
                        "response_status": status_code,
                        "response_headers": response_headers,
                        "execution_time": execution_time,
                        "error_message": None if is_success else f"HTTP {status_code}",
                        "error_type": None if is_success else "HTTP_ERROR",
                        "timestamp": datetime.utcnow()
                    }
                    
                    # If failed and retries available, retry
                    if not is_success and attempt < self.max_retries:
                        if self._should_retry(status_code):
                            logger.info(f"Test failed with {status_code}, retrying (attempt {attempt + 1}/{self.max_retries})")
                            await self._exponential_backoff(attempt)
                            return await self.execute_test(
                                endpoint, test_data, base_url, headers, attempt + 1
                            )
                    
                    return result
                    
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            logger.error(f"Request timeout for {method} {path}")
            
            result = {
                "status": "failed",
                "attempt_number": attempt,
                "request_data": test_data,
                "request_headers": request_headers,
                "response_data": None,
                "response_status": None,
                "response_headers": None,
                "execution_time": execution_time,
                "error_message": f"Request timeout after {self.timeout}s",
                "error_type": "TIMEOUT",
                "timestamp": datetime.utcnow()
            }
            
            # Retry on timeout
            if attempt < self.max_retries:
                logger.info(f"Timeout, retrying (attempt {attempt + 1}/{self.max_retries})")
                await self._exponential_backoff(attempt)
                return await self.execute_test(
                    endpoint, test_data, base_url, headers, attempt + 1
                )
            
            return result
            
        except aiohttp.ClientError as e:
            execution_time = time.time() - start_time
            logger.error(f"Network error for {method} {path}: {e}")
            
            result = {
                "status": "failed",
                "attempt_number": attempt,
                "request_data": test_data,
                "request_headers": request_headers,
                "response_data": None,
                "response_status": None,
                "response_headers": None,
                "execution_time": execution_time,
                "error_message": f"Network error: {str(e)}",
                "error_type": "NETWORK_ERROR",
                "timestamp": datetime.utcnow()
            }
            
            # Retry on network errors
            if attempt < self.max_retries:
                logger.info(f"Network error, retrying (attempt {attempt + 1}/{self.max_retries})")
                await self._exponential_backoff(attempt)
                return await self.execute_test(
                    endpoint, test_data, base_url, headers, attempt + 1
                )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Unexpected error for {method} {path}: {e}")
            
            return {
                "status": "failed",
                "attempt_number": attempt,
                "request_data": test_data,
                "request_headers": request_headers,
                "response_data": None,
                "response_status": None,
                "response_headers": None,
                "execution_time": execution_time,
                "error_message": f"Unexpected error: {str(e)}",
                "error_type": "UNKNOWN_ERROR",
                "timestamp": datetime.utcnow()
            }
    
    def _should_retry(self, status_code: int) -> bool:
        """
        Determine if a failed request should be retried
        
        Args:
            status_code: HTTP status code
            
        Returns:
            True if should retry, False otherwise
        """
        # Retry on 5xx server errors
        if 500 <= status_code < 600:
            return True
        
        # Retry on 429 (rate limiting)
        if status_code == 429:
            return True
        
        # Don't retry on 4xx client errors (except 429)
        # These usually indicate bad request data that won't fix with retry
        return False
    
    async def _exponential_backoff(self, attempt: int):
        """
        Wait with exponential backoff before retry
        
        Args:
            attempt: Current attempt number (0-indexed)
        """
        delay = min(self.initial_delay * (2 ** attempt), self.max_delay)
        logger.debug(f"Waiting {delay}s before retry...")
        await asyncio.sleep(delay)
    
    async def execute_batch(
        self,
        tests: list[Tuple[Dict[str, Any], Dict[str, Any]]],
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        max_concurrent: int = 5
    ) -> list[Dict[str, Any]]:
        """
        Execute multiple tests concurrently with rate limiting
        
        Args:
            tests: List of (endpoint, test_data) tuples
            base_url: Base URL for the API
            headers: Optional HTTP headers
            max_concurrent: Maximum concurrent requests
            
        Returns:
            List of test results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_semaphore(endpoint, test_data):
            async with semaphore:
                return await self.execute_test(endpoint, test_data, base_url, headers)
        
        tasks = [
            execute_with_semaphore(endpoint, test_data)
            for endpoint, test_data in tests
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                endpoint, test_data = tests[i]
                processed_results.append({
                    "status": "failed",
                    "attempt_number": 1,
                    "request_data": test_data,
                    "request_headers": headers or {},
                    "response_data": None,
                    "response_status": None,
                    "response_headers": None,
                    "execution_time": 0.0,
                    "error_message": f"Exception during execution: {str(result)}",
                    "error_type": "EXECUTION_ERROR",
                    "timestamp": datetime.utcnow()
                })
            else:
                processed_results.append(result)
        
        return processed_results

