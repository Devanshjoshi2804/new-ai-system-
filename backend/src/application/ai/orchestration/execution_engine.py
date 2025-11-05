"""
Execution Engine

Intelligent test execution system with:
- Retry logic and exponential backoff
- Automatic error fixing using HybridPredictor
- Dependency resolution
- Parallel execution where possible
- Rate limiting and circuit breakers
"""

import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Callable
import httpx
from datetime import datetime

from .types import (
    EndpointInfo,
    TestResult,
    TestStatus,
    DependencyGraph,
    ExecutionContext
)

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Circuit breaker pattern for fault tolerance

    Prevents cascading failures by stopping requests to failing services.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half_open

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""

        if self.state == 'open':
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = 'half_open'
                logger.info("[CIRCUIT_BREAKER] Attempting recovery (half-open)")
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)

            # Success - reset failure count
            if self.state == 'half_open':
                self.state = 'closed'
                self.failure_count = 0
                logger.info("[CIRCUIT_BREAKER] Recovery successful (closed)")

            return result

        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            logger.warning(
                f"[CIRCUIT_BREAKER] Failure {self.failure_count}/{self.failure_threshold}"
            )

            if self.failure_count >= self.failure_threshold:
                self.state = 'open'
                logger.error("[CIRCUIT_BREAKER] Circuit opened due to failures")

            raise


class RateLimiter:
    """
    Rate limiter using token bucket algorithm

    Ensures we don't overwhelm the API with too many requests.
    """

    def __init__(self, rate_per_second: int = 10):
        """
        Initialize rate limiter

        Args:
            rate_per_second: Maximum requests per second
        """
        self.rate = rate_per_second
        self.tokens = rate_per_second
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Acquire permission to make a request"""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update

            # Add tokens based on elapsed time
            self.tokens = min(
                self.rate,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now

            if self.tokens < 1:
                # Wait until we have a token
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


class ExecutionEngine:
    """
    Intelligent test execution engine

    Executes API endpoint tests with smart retry logic, error fixing,
    and dependency management.
    """

    def __init__(self, hybrid_predictor=None):
        """
        Initialize execution engine

        Args:
            hybrid_predictor: Hybrid predictor for error fixing
        """
        self.hybrid_predictor = hybrid_predictor
        self.circuit_breaker = CircuitBreaker()

        logger.info("[EXECUTION_ENGINE] Initialized")

    async def execute_tests(
        self,
        endpoints: List[EndpointInfo],
        payloads: Dict[str, Dict[str, Any]],
        dependency_graph: DependencyGraph,
        context: ExecutionContext,
        on_progress: Optional[Callable[[float], None]] = None
    ) -> List[TestResult]:
        """
        Execute tests for all endpoints with intelligent ordering

        Args:
            endpoints: List of endpoints to test
            payloads: Generated payloads for each endpoint
            dependency_graph: Dependency relationships
            context: Execution context with auth, retries, etc.
            on_progress: Optional callback for progress updates

        Returns:
            List of test results
        """
        logger.info(f"[EXECUTION_ENGINE] Starting test execution for {len(endpoints)} endpoints")

        rate_limiter = RateLimiter(rate_per_second=context.rate_limit_per_second)
        results = []

        try:
            # Get execution order
            execution_order = dependency_graph.get_execution_order()
            logger.info(f"[EXECUTION_ENGINE] Execution order: {execution_order}")

            total = len(execution_order)
            completed = 0

            # Execute in order
            for endpoint_id in execution_order:
                # Find endpoint
                endpoint = next(
                    (ep for ep in endpoints if ep.id == endpoint_id),
                    None
                )

                if not endpoint:
                    logger.warning(f"[EXECUTION_ENGINE] Endpoint not found: {endpoint_id}")
                    completed += 1
                    if on_progress:
                        on_progress((completed / total) * 100)
                    continue

                # Get payload
                payload = payloads.get(endpoint_id, {})

                # Rate limit
                await rate_limiter.acquire()

                # Execute test
                result = await self._execute_single_test(
                    endpoint=endpoint,
                    payload=payload,
                    context=context
                )

                results.append(result)
                context.executed_endpoints[endpoint_id] = result

                # Update progress
                completed += 1
                if on_progress:
                    on_progress((completed / total) * 100)

                # Store results that might be needed by dependent endpoints
                if result.status == TestStatus.PASSED and result.response:
                    # Extract useful data from response
                    self._extract_shared_state(endpoint, result, context)

            logger.info(
                f"[EXECUTION_ENGINE] Execution complete: "
                f"{sum(1 for r in results if r.status == TestStatus.PASSED)} passed, "
                f"{sum(1 for r in results if r.status == TestStatus.FAILED)} failed"
            )

            return results

        except Exception as e:
            logger.error(f"[EXECUTION_ENGINE] Execution failed: {e}")
            raise

    async def _execute_single_test(
        self,
        endpoint: EndpointInfo,
        payload: Dict[str, Any],
        context: ExecutionContext
    ) -> TestResult:
        """
        Execute single endpoint test with retry and error fixing

        Args:
            endpoint: Endpoint to test
            payload: Request payload
            context: Execution context

        Returns:
            Test result
        """
        logger.info(f"[EXECUTION_ENGINE] Testing {endpoint.method} {endpoint.url}")

        retry_count = 0
        last_error = None
        current_payload = payload.copy()

        for attempt in range(context.max_retries + 1):
            try:
                # Execute request
                result = await self._make_request(
                    endpoint=endpoint,
                    payload=current_payload,
                    context=context
                )

                # Success!
                result.retry_count = retry_count
                logger.info(
                    f"[EXECUTION_ENGINE] ✓ {endpoint.id} passed "
                    f"({result.latency_ms:.0f}ms, {retry_count} retries)"
                )

                return result

            except Exception as e:
                last_error = e
                retry_count = attempt + 1

                logger.warning(
                    f"[EXECUTION_ENGINE] ✗ {endpoint.id} failed "
                    f"(attempt {retry_count}/{context.max_retries + 1}): {e}"
                )

                # Try to fix error if auto-fix is enabled
                if context.enable_auto_fix and self.hybrid_predictor and retry_count <= context.max_retries:
                    try:
                        logger.info(f"[EXECUTION_ENGINE] Attempting auto-fix for {endpoint.id}...")

                        # Get error response
                        error_response = {
                            'error': str(e),
                            'endpoint': endpoint.url,
                            'method': endpoint.method
                        }

                        # Try to fix
                        fix_result = await self.hybrid_predictor.fix_error(
                            endpoint_url=endpoint.url,
                            error_response=error_response,
                            original_payload=current_payload,
                            context={'retry': retry_count}
                        )

                        if fix_result.confidence > 0.5:
                            # Use fixed payload
                            current_payload = fix_result.prediction
                            logger.info(
                                f"[EXECUTION_ENGINE] Applied fix "
                                f"(confidence={fix_result.confidence:.3f})"
                            )

                            # Wait before retry
                            await asyncio.sleep(context.retry_delay_seconds * attempt)
                            continue

                    except Exception as fix_error:
                        logger.warning(f"[EXECUTION_ENGINE] Auto-fix failed: {fix_error}")

                # Wait before retry
                if retry_count <= context.max_retries:
                    await asyncio.sleep(context.retry_delay_seconds * attempt)

        # All retries failed
        result = TestResult(
            endpoint_id=endpoint.id,
            status=TestStatus.FAILED,
            request={
                'url': endpoint.url,
                'method': endpoint.method,
                'payload': current_payload
            },
            error=str(last_error),
            retry_count=retry_count,
            timestamp=datetime.utcnow()
        )

        logger.error(f"[EXECUTION_ENGINE] ✗ {endpoint.id} failed after {retry_count} retries")

        return result

    async def _make_request(
        self,
        endpoint: EndpointInfo,
        payload: Dict[str, Any],
        context: ExecutionContext
    ) -> TestResult:
        """
        Make actual HTTP request

        Args:
            endpoint: Endpoint to call
            payload: Request payload
            context: Execution context

        Returns:
            Test result

        Raises:
            Exception: If request fails
        """
        start_time = time.time()

        # Build full URL
        url = endpoint.url
        if context.base_url and not url.startswith('http'):
            url = f"{context.base_url.rstrip('/')}/{url.lstrip('/')}"

        # Get auth headers
        headers = context.auth_config.get_auth_headers()
        headers.update(endpoint.headers)

        # Add default headers
        if 'Content-Type' not in headers and endpoint.method in ['POST', 'PUT', 'PATCH']:
            headers['Content-Type'] = 'application/json'

        try:
            async with httpx.AsyncClient(timeout=context.timeout_seconds) as client:
                # Prepare request kwargs
                request_kwargs = {
                    'headers': headers
                }

                # Add payload for methods that support body
                if endpoint.method in ['POST', 'PUT', 'PATCH'] and payload:
                    request_kwargs['json'] = payload

                # Make request
                response = await client.request(
                    endpoint.method,
                    url,
                    **request_kwargs
                )

                latency_ms = (time.time() - start_time) * 1000

                # Read response
                try:
                    response_data = response.json()
                except:
                    response_data = {'text': response.text}

                # Check status code
                if response.status_code >= 400:
                    raise Exception(
                        f"HTTP {response.status_code}: {response_data.get('error', response_data)}"
                    )

                # Success
                return TestResult(
                    endpoint_id=endpoint.id,
                    status=TestStatus.PASSED,
                    request={
                        'url': url,
                        'method': endpoint.method,
                        'headers': headers,
                        'payload': payload
                    },
                    response=response_data,
                    latency_ms=latency_ms,
                    timestamp=datetime.utcnow()
                )

        except asyncio.TimeoutError:
            raise Exception(f"Request timeout after {context.timeout_seconds}s")

        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")

    def _extract_shared_state(
        self,
        endpoint: EndpointInfo,
        result: TestResult,
        context: ExecutionContext
    ):
        """
        Extract useful data from response to share with dependent endpoints

        Args:
            endpoint: Endpoint that was executed
            result: Test result
            context: Execution context to update
        """
        if not result.response:
            return

        # Extract common fields
        if endpoint.category == 'authentication':
            # Extract auth token
            if 'token' in result.response:
                context.shared_state['auth_token'] = result.response['token']
                logger.debug("[EXECUTION_ENGINE] Extracted auth token")

            if 'access_token' in result.response:
                context.shared_state['access_token'] = result.response['access_token']
                logger.debug("[EXECUTION_ENGINE] Extracted access token")

        # Extract IDs from creation endpoints
        if endpoint.category == 'data_creation':
            if 'id' in result.response:
                key = f"{endpoint.id}_created_id"
                context.shared_state[key] = result.response['id']
                logger.debug(f"[EXECUTION_ENGINE] Extracted created ID: {key}")

        # Store entire response for reference
        context.shared_state[f"{endpoint.id}_response"] = result.response

    async def execute_parallel_batch(
        self,
        endpoints: List[EndpointInfo],
        payloads: Dict[str, Dict[str, Any]],
        context: ExecutionContext
    ) -> List[TestResult]:
        """
        Execute multiple endpoints in parallel

        Args:
            endpoints: List of endpoints to execute
            payloads: Payloads for each endpoint
            context: Execution context

        Returns:
            List of test results
        """
        logger.info(f"[EXECUTION_ENGINE] Executing {len(endpoints)} endpoints in parallel")

        tasks = []
        for endpoint in endpoints:
            payload = payloads.get(endpoint.id, {})
            task = self._execute_single_test(endpoint, payload, context)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed test results
        final_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                endpoint = endpoints[idx]
                final_results.append(
                    TestResult(
                        endpoint_id=endpoint.id,
                        status=TestStatus.FAILED,
                        request={
                            'url': endpoint.url,
                            'method': endpoint.method
                        },
                        error=str(result),
                        timestamp=datetime.utcnow()
                    )
                )
            else:
                final_results.append(result)

        return final_results
