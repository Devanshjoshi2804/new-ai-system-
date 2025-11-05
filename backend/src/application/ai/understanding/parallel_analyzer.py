"""
Parallel API Analyzer - Process multiple analysis tasks concurrently
Massive speed improvement by running independent analyses in parallel
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AnalysisTask:
    """Represents an analysis task"""
    name: str
    func: Callable
    args: tuple = ()
    kwargs: dict = None
    
    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}


class ParallelAnalyzer:
    """
    Execute multiple analysis tasks in parallel
    
    Features:
    - Concurrent execution of independent tasks
    - Error handling per task
    - Progress tracking
    - Result aggregation
    """
    
    def __init__(self, max_concurrent: int = 5):
        """
        Initialize parallel analyzer
        
        Args:
            max_concurrent: Maximum concurrent tasks
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def execute_task(self, task: AnalysisTask) -> tuple[str, Any, Optional[Exception]]:
        """
        Execute a single task with error handling
        
        Args:
            task: Analysis task to execute
            
        Returns:
            Tuple of (task_name, result, error)
        """
        async with self.semaphore:
            try:
                logger.info(f"[INFO] Starting task: {task.name}")
                start_time = asyncio.get_event_loop().time()
                
                result = await task.func(*task.args, **task.kwargs)
                
                elapsed = asyncio.get_event_loop().time() - start_time
                logger.info(f"[OK] Completed task: {task.name} ({elapsed:.2f}s)")
                
                return (task.name, result, None)
            
            except Exception as e:
                logger.error(f"[ERROR] Task failed: {task.name} - {e}")
                return (task.name, None, e)
    
    async def execute_all(
        self,
        tasks: List[AnalysisTask],
        fail_fast: bool = False
    ) -> Dict[str, Any]:
        """
        Execute all tasks in parallel
        
        Args:
            tasks: List of analysis tasks
            fail_fast: If True, stop on first error
            
        Returns:
            Dictionary of results by task name
        """
        logger.info(f"[START] Starting parallel execution of {len(tasks)} tasks (max_concurrent={self.max_concurrent})")
        start_time = asyncio.get_event_loop().time()
        
        # Execute all tasks concurrently
        if fail_fast:
            # Use gather without return_exceptions to fail fast
            results = await asyncio.gather(
                *[self.execute_task(task) for task in tasks]
            )
        else:
            # Use gather with return_exceptions to continue on errors
            results = await asyncio.gather(
                *[self.execute_task(task) for task in tasks],
                return_exceptions=True
            )
        
        # Aggregate results
        aggregated = {
            'results': {},
            'errors': {},
            'success_count': 0,
            'error_count': 0
        }
        
        for result in results:
            if isinstance(result, Exception):
                # Task itself raised an exception
                aggregated['errors']['unknown'] = str(result)
                aggregated['error_count'] += 1
            else:
                task_name, task_result, task_error = result
                
                if task_error:
                    aggregated['errors'][task_name] = str(task_error)
                    aggregated['error_count'] += 1
                else:
                    aggregated['results'][task_name] = task_result
                    aggregated['success_count'] += 1
        
        elapsed = asyncio.get_event_loop().time() - start_time
        logger.info(
            f"[OK] Parallel execution complete: {aggregated['success_count']}/{len(tasks)} succeeded "
            f"({elapsed:.2f}s total, {elapsed/len(tasks):.2f}s avg)"
        )
        
        if aggregated['error_count'] > 0:
            logger.warning(f"[WARN] {aggregated['error_count']} tasks failed")
        
        return aggregated
    
    async def execute_with_fallback(
        self,
        primary_tasks: List[AnalysisTask],
        fallback_tasks: Dict[str, AnalysisTask]
    ) -> Dict[str, Any]:
        """
        Execute tasks with fallback options
        
        Args:
            primary_tasks: Primary tasks to execute
            fallback_tasks: Fallback tasks by name
            
        Returns:
            Dictionary of results
        """
        # Execute primary tasks
        results = await self.execute_all(primary_tasks, fail_fast=False)
        
        # Execute fallbacks for failed tasks
        if results['error_count'] > 0:
            logger.info(f"[INFO] Executing {len(results['errors'])} fallback tasks")
            
            fallback_task_list = []
            for task_name in results['errors'].keys():
                if task_name in fallback_tasks:
                    fallback_task_list.append(fallback_tasks[task_name])
            
            if fallback_task_list:
                fallback_results = await self.execute_all(fallback_task_list, fail_fast=False)
                
                # Merge fallback results
                results['results'].update(fallback_results['results'])
                results['success_count'] += fallback_results['success_count']
                
                # Remove successful fallbacks from errors
                for task_name in fallback_results['results'].keys():
                    if task_name in results['errors']:
                        del results['errors'][task_name]
                        results['error_count'] -= 1
        
        return results


async def analyze_api_parallel(
    raw_text: str,
    endpoints: List[Dict[str, Any]],
    gemini_provider,
    mistral_provider=None
) -> Dict[str, Any]:
    """
    Analyze API documentation using parallel processing
    
    Args:
        raw_text: Documentation text
        endpoints: List of endpoints
        gemini_provider: Gemini provider instance
        mistral_provider: Optional Mistral provider
        
    Returns:
        Complete analysis results
    """
    analyzer = ParallelAnalyzer(max_concurrent=5)
    
    # Define all analysis tasks that can run in parallel
    tasks = [
        AnalysisTask(
            name="auth_config",
            func=extract_auth_config_parallel,
            args=(raw_text, gemini_provider)
        ),
        AnalysisTask(
            name="schemas",
            func=extract_schemas_parallel,
            args=(raw_text, endpoints, gemini_provider)
        ),
        AnalysisTask(
            name="dependencies",
            func=gemini_provider.analyze_api_dependencies,
            args=(endpoints,)
        ),
        AnalysisTask(
            name="business_rules",
            func=extract_business_rules_parallel,
            args=(raw_text, gemini_provider)
        ),
        AnalysisTask(
            name="workflow_analysis",
            func=gemini_provider.analyze_workflow_and_data_flow,
            args=(endpoints,),
            kwargs={'documentation_text': raw_text[:10000]}
        )
    ]
    
    # Execute all tasks in parallel
    results = await analyzer.execute_all(tasks, fail_fast=False)
    
    return results


async def extract_auth_config_parallel(raw_text: str, gemini_provider) -> Dict[str, Any]:
    """Extract auth config in parallel"""
    prompt = f"""
Analyze authentication requirements from this documentation:

Documentation:
{raw_text[:15000]}

Identify:
- Auth type (API Key, Bearer Token, OAuth2, Basic Auth, Custom)
- Where to provide credentials (header, query parameter, body)
- Header/parameter names
- Token format (e.g., "Bearer {{token}}", "{{token}}", "API-Key {{token}}")
- How to obtain credentials (which endpoint to call)
- Test credentials (if mentioned in documentation)
- Token expiration (if mentioned)

Output as JSON:
{{
  "type": "bearer",
  "location": "header",
  "header_name": "Authorization",
  "token_format": "Bearer {{token}}",
  "auth_endpoint": "/api/login",
  "auth_method": "POST",
  "credentials_required": ["email", "password"],
  "test_credentials": {{"email": "test@example.com", "password": "test123"}},
  "token_response_path": "data.token",
  "token_expiration": "24 hours"
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
    
    result_text = await gemini_provider.generate_content(prompt, temperature=0.1)
    
    # Parse JSON
    if "```json" in result_text:
        result_text = result_text.split("```json")[1].split("```")[0].strip()
    elif "```" in result_text:
        result_text = result_text.split("```")[1].split("```")[0].strip()
    
    import json
    return json.loads(result_text)


async def extract_schemas_parallel(
    raw_text: str,
    endpoints: List[Dict[str, Any]],
    gemini_provider
) -> Dict[str, Any]:
    """Extract schemas in parallel"""
    import json
    
    prompt = f"""
Extract data schemas from examples in this documentation:

Documentation:
{raw_text[:15000]}

Endpoints:
{json.dumps(endpoints, indent=2)[:5000]}

For each endpoint, provide:
- Request body schema (JSON Schema format)
- Response schema (JSON Schema format)
- Required vs optional fields
- Field types and constraints (min, max, pattern, enum)
- Example values
- Field descriptions

Output as JSON:
{{
  "/api/endpoint1": {{
    "request_schema": {{
      "type": "object",
      "properties": {{
        "field1": {{"type": "string", "description": "...", "required": true}}
      }},
      "required": ["field1"]
    }},
    "response_schema": {{
      "type": "object",
      "properties": {{
        "status": {{"type": "string"}},
        "data": {{"type": "object"}}
      }}
    }}
  }}
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
    
    result_text = await gemini_provider.generate_content(prompt, temperature=0.1)
    
    # Parse JSON
    if "```json" in result_text:
        result_text = result_text.split("```json")[1].split("```")[0].strip()
    elif "```" in result_text:
        result_text = result_text.split("```")[1].split("```")[0].strip()
    
    return json.loads(result_text)


async def extract_business_rules_parallel(raw_text: str, gemini_provider) -> List[Dict[str, Any]]:
    """Extract business rules in parallel"""
    import json
    
    prompt = f"""
Extract business rules and constraints from this documentation:

Documentation:
{raw_text[:15000]}

Identify:
- Validation rules (e.g., "weight must be > 0", "email must be valid")
- Business constraints (e.g., "cannot cancel after pickup", "max 50kg per shipment")
- Required sequences (e.g., "must validate address before booking")
- Error conditions and handling
- Rate limits and quotas
- Data format requirements (date formats, phone formats, etc.)

Output as JSON array of rules:
[
  {{
    "rule": "Weight must be greater than 0",
    "type": "validation",
    "applies_to": ["/api/bookings"],
    "severity": "error"
  }}
]

Return ONLY valid JSON array, no markdown, no explanations.
"""
    
    result_text = await gemini_provider.generate_content(prompt, temperature=0.2)
    
    # Parse JSON
    if "```json" in result_text:
        result_text = result_text.split("```json")[1].split("```")[0].strip()
    elif "```" in result_text:
        result_text = result_text.split("```")[1].split("```")[0].strip()
    
    return json.loads(result_text)

