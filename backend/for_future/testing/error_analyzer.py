"""
AI-Powered Error Analyzer
Analyzes API errors and suggests actionable fixes
Enhanced with Knowledge Graph integration for learned fixes
"""
import json
import logging
from typing import Dict, Any, List, Optional

from src.infrastructure.ai.providers.gemini_provider import GeminiProvider
from src.application.ai.learning.knowledge_graph import KnowledgeGraph

logger = logging.getLogger(__name__)


class ErrorAnalyzer:
    """Analyze API errors and suggest fixes using AI + learned patterns"""
    
    def __init__(self):
        self.gemini = GeminiProvider()
        self.knowledge_graph = KnowledgeGraph()
    
    async def analyze_error(
        self,
        request: Dict[str, Any],
        response: Dict[str, Any],
        api_spec: Optional[Dict[str, Any]] = None,
        partner_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deep analysis of API errors using AI + learned patterns
        Returns actionable fixes
        
        Args:
            request: The API request that failed
            response: The error response
            api_spec: Optional API specification for context
            partner_id: Optional partner ID for querying learned fixes
            
        Returns:
            Analysis with root cause and suggested fixes
        """
        try:
            logger.info("🔍 Analyzing API error...")
            
            # Step 1: Query knowledge graph for similar errors
            error_message = response.get('error', response.get('message', str(response)))
            learned_fix = None
            
            if partner_id and self.knowledge_graph:
                learned_fix = await self.knowledge_graph.query_error_fix(
                    error=error_message,
                    partner_id=partner_id
                )
                
                if learned_fix:
                    logger.info("✅ Found learned fix from knowledge graph")
            
            api_spec_str = json.dumps(api_spec, indent=2)[:3000] if api_spec else "No API spec provided"
            learned_fix_str = json.dumps(learned_fix, indent=2) if learned_fix else "No learned fix available"
            
            prompt = f"""
Analyze this API error and provide actionable fixes:

**Request:**
{json.dumps(request, indent=2)}

**Response:**
{json.dumps(response, indent=2)}

**API Specification:**
{api_spec_str}

**Learned Fix (from previous similar errors):**
{learned_fix_str}

Perform deep analysis:

1. **Root Cause**: What exactly went wrong?
   - Authentication issue? (missing/invalid token, expired token)
   - Data validation issue? (missing required field, invalid format, wrong type)
   - Business rule violation? (weight < 0, invalid status transition)
   - Endpoint issue? (wrong URL, wrong method)
   - Dependency issue? (missing prerequisite data like addressId)
   - Rate limiting? (too many requests)
   - Server error? (500, 503)

2. **Error Category**: Classify the error
   - auth_failure
   - validation_error
   - business_rule_violation
   - not_found
   - rate_limit
   - server_error
   - network_error
   - dependency_missing

3. **Problematic Fields**: Which fields caused the error?

4. **Corrected Request**: Provide the exact corrected request that should work

5. **Alternative Approaches**: Other ways to achieve the same goal

6. **Retry Strategy**: Should we retry? If yes, how?
   - Immediate retry with fixed data
   - Retry after delay (rate limiting)
   - Retry with different approach
   - Don't retry (API issue)

Output as JSON:
{{
  "root_cause": "Detailed explanation of what went wrong",
  "error_category": "validation_error",
  "problematic_fields": ["field1", "field2"],
  "field_issues": {{
    "field1": "Missing required field",
    "field2": "Invalid format, expected email"
  }},
  "corrected_request": {{
    "endpoint": "/api/endpoint",
    "method": "POST",
    "data": {{"field1": "corrected_value", "field2": "corrected_value"}},
    "headers": {{"Authorization": "Bearer token"}}
  }},
  "alternative_approaches": [
    "Try calling /api/validate first",
    "Use different endpoint /api/v2/endpoint"
  ],
  "retry_strategy": {{
    "should_retry": true,
    "retry_type": "immediate|delayed|different_approach",
    "delay_seconds": 0,
    "max_retries": 3,
    "explanation": "Why this retry strategy"
  }},
  "confidence": 0.9,
  "is_api_issue": false
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            response_text = await self.gemini.generate_content(prompt, temperature=0.2)
            
            # Parse JSON from response
            analysis_text = response_text.strip()
            if "```json" in analysis_text:
                analysis_text = analysis_text.split("```json")[1].split("```")[0].strip()
            elif "```" in analysis_text:
                analysis_text = analysis_text.split("```")[1].split("```")[0].strip()
            
            analysis = json.loads(analysis_text)
            
            # Add learned fix to analysis if available
            if learned_fix:
                analysis['learned_fix'] = learned_fix
                analysis['has_learned_fix'] = True
            else:
                analysis['has_learned_fix'] = False
            
            logger.info(f"✅ Error analyzed: {analysis.get('error_category')}")
            logger.info(f"💡 Root cause: {analysis.get('root_cause')[:100]}...")
            
            # Step 2: Store this fix in knowledge graph if analysis succeeded
            if partner_id and self.knowledge_graph and analysis.get('confidence', 0) > 0.7:
                await self.knowledge_graph.store_error_fix(
                    partner_id=partner_id,
                    error=error_message,
                    fix=analysis.get('corrected_request', {}),
                    success=False  # Will be updated if fix works
                )
            
            return analysis
        
        except Exception as e:
            logger.error(f"❌ Error analyzing error: {e}", exc_info=True)
            return {
                'root_cause': 'Unknown error',
                'error_category': 'unknown',
                'problematic_fields': [],
                'field_issues': {},
                'corrected_request': request,
                'alternative_approaches': [],
                'retry_strategy': {
                    'should_retry': False,
                    'retry_type': 'none',
                    'delay_seconds': 0,
                    'max_retries': 0,
                    'explanation': 'Analysis failed'
                },
                'confidence': 0.0,
                'is_api_issue': False,
                'analysis_error': str(e)
            }
    
    async def analyze_multiple_failures(
        self,
        failures: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze multiple test failures to identify patterns
        
        Args:
            failures: List of test failures
            
        Returns:
            Pattern analysis
        """
        try:
            logger.info(f"🔍 Analyzing {len(failures)} failures for patterns...")
            
            prompt = f"""
Analyze these multiple test failures to identify patterns:

**Failures:**
{json.dumps(failures, indent=2)[:8000]}

Identify:
1. **Common Patterns**: What's common across failures?
   - Same error type?
   - Same problematic fields?
   - Same endpoints failing?
   - Authentication issues across all tests?

2. **Root Cause**: Is there a systemic issue?
   - API configuration problem?
   - Test data generation issue?
   - Authentication setup issue?
   - API version mismatch?

3. **Bulk Fix**: Can we fix all failures with one change?
   - Update authentication?
   - Fix data format globally?
   - Change base URL?
   - Update required fields?

4. **Priority**: Which failures to fix first?

Output as JSON:
{{
  "patterns": [
    {{
      "pattern": "All tests failing with 401",
      "affected_tests": ["test1", "test2"],
      "frequency": 10
    }}
  ],
  "systemic_issue": {{
    "exists": true,
    "description": "Authentication token is invalid",
    "affects": "all_tests|some_tests"
  }},
  "bulk_fix": {{
    "possible": true,
    "fix_type": "update_auth|fix_data_format|change_endpoint",
    "fix_description": "Update authentication token",
    "affected_tests": ["test1", "test2", "test3"]
  }},
  "priority_order": [
    {{
      "test_id": "test1",
      "priority": "high",
      "reason": "Blocks other tests"
    }}
  ]
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.2)
            
            # Parse JSON from response
            analysis_text = response.strip()
            if "```json" in analysis_text:
                analysis_text = analysis_text.split("```json")[1].split("```")[0].strip()
            elif "```" in analysis_text:
                analysis_text = analysis_text.split("```")[1].split("```")[0].strip()
            
            analysis = json.loads(analysis_text)
            
            logger.info(f"✅ Pattern analysis complete")
            logger.info(f"📊 Found {len(analysis.get('patterns', []))} patterns")
            
            return analysis
        
        except Exception as e:
            logger.error(f"❌ Error analyzing multiple failures: {e}")
            return {
                'patterns': [],
                'systemic_issue': {'exists': False},
                'bulk_fix': {'possible': False},
                'priority_order': [],
                'error': str(e)
            }
    
    async def suggest_test_improvements(
        self,
        test_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze test results and suggest improvements
        
        Args:
            test_results: All test results (passed and failed)
            
        Returns:
            Improvement suggestions
        """
        try:
            logger.info("💡 Suggesting test improvements...")
            
            prompt = f"""
Analyze these test results and suggest improvements:

**Test Results:**
{json.dumps(test_results, indent=2)[:8000]}

Suggest improvements:

1. **Flaky Tests**: Tests that sometimes pass, sometimes fail
   - Identify unreliable tests
   - Suggest fixes for flakiness

2. **Redundant Tests**: Tests that test the same thing
   - Identify duplicates
   - Suggest consolidation

3. **Missing Tests**: Scenarios not covered
   - Identify gaps
   - Suggest new tests

4. **Test Data Issues**: Problems with test data
   - Unrealistic data
   - Invalid data not invalid enough
   - Missing edge cases

5. **Test Structure Issues**: Problems with test organization
   - Tests in wrong order
   - Missing dependencies
   - Poor assertions

Output as JSON:
{{
  "flaky_tests": [
    {{
      "test_id": "test1",
      "reason": "Depends on timing",
      "suggestion": "Add explicit wait"
    }}
  ],
  "redundant_tests": [
    {{
      "tests": ["test1", "test2"],
      "reason": "Both test same endpoint with same data",
      "suggestion": "Merge into one test"
    }}
  ],
  "missing_tests": [
    {{
      "scenario": "Delete endpoint not tested",
      "priority": "high",
      "suggested_test": "Add DELETE /api/resource test"
    }}
  ],
  "test_data_issues": [
    {{
      "test_id": "test1",
      "issue": "Using unrealistic data",
      "suggestion": "Use production-like addresses"
    }}
  ],
  "structure_issues": [
    {{
      "issue": "Tests not in dependency order",
      "suggestion": "Run auth tests first"
    }}
  ]
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.3)
            
            # Parse JSON from response
            suggestions_text = response.strip()
            if "```json" in suggestions_text:
                suggestions_text = suggestions_text.split("```json")[1].split("```")[0].strip()
            elif "```" in suggestions_text:
                suggestions_text = suggestions_text.split("```")[1].split("```")[0].strip()
            
            suggestions = json.loads(suggestions_text)
            
            logger.info("✅ Test improvement suggestions generated")
            
            return suggestions
        
        except Exception as e:
            logger.error(f"❌ Error suggesting improvements: {e}")
            return {
                'flaky_tests': [],
                'redundant_tests': [],
                'missing_tests': [],
                'test_data_issues': [],
                'structure_issues': [],
                'error': str(e)
            }
    
    async def explain_error_to_user(
        self,
        error: Dict[str, Any],
        user_friendly: bool = True
    ) -> str:
        """
        Generate user-friendly explanation of error
        
        Args:
            error: Error details
            user_friendly: Whether to use simple language
            
        Returns:
            Human-readable explanation
        """
        try:
            logger.info("📝 Generating user-friendly error explanation...")
            
            tone = "simple, non-technical" if user_friendly else "technical"
            
            prompt = f"""
Explain this API error in {tone} language:

**Error:**
{json.dumps(error, indent=2)}

Generate a clear explanation that:
1. Explains what went wrong in simple terms
2. Explains why it happened
3. Suggests what to do next
4. Provides actionable steps

{"Use simple language, avoid technical jargon." if user_friendly else "Use technical language, include details."}

Output as plain text (not JSON), 2-3 paragraphs.
"""
            
            explanation = await self.gemini.generate_content(prompt, temperature=0.5)
            
            logger.info("✅ User-friendly explanation generated")
            
            return explanation.strip()
        
        except Exception as e:
            logger.error(f"❌ Error generating explanation: {e}")
            return "An error occurred, but we couldn't generate a detailed explanation. Please check the error details."
