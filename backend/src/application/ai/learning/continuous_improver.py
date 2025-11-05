"""
Continuous Improvement System
Analyzes results and suggests improvements over time
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from src.infrastructure.ai.providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class ContinuousImprover:
    """Continuously improve test generation and execution"""
    
    def __init__(self):
        self.gemini = GeminiProvider()
    
    async def analyze_test_results(
        self,
        test_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze test results and suggest improvements
        
        Args:
            test_results: List of test execution results
            
        Returns:
            Analysis with improvement suggestions
        """
        try:
            logger.info(f"[INFO] Analyzing {len(test_results)} test results...")
            
            prompt = f"""
Analyze these test results and suggest improvements:

**Test Results:**
{json.dumps(test_results, indent=2)[:8000]}

**Your Task:**
Identify improvement opportunities:

1. **Flaky Tests**: Tests that sometimes pass, sometimes fail
   - Look for tests with retry_count > 0
   - Tests that pass after fix
   - Identify why they're unreliable

2. **Redundant Tests**: Tests that test the same thing
   - Multiple tests calling same endpoint with similar data
   - Suggest consolidation

3. **Missing Test Scenarios**: Gaps in coverage
   - Endpoints not tested
   - Error cases not covered
   - Edge cases missing

4. **Test Data Issues**: Problems with test data
   - Unrealistic data
   - Invalid data not invalid enough
   - Missing boundary cases

5. **Test Structure Issues**: Organizational problems
   - Tests in wrong order
   - Missing dependencies
   - Poor assertions

6. **Performance Issues**: Slow tests
   - Tests taking too long
   - Unnecessary API calls
   - Could be parallelized

Output as JSON:
{{
  "flaky_tests": [
    {{
      "test_id": "test_001",
      "reason": "Depends on timing",
      "suggestion": "Add explicit wait or retry logic"
    }}
  ],
  "redundant_tests": [
    {{
      "tests": ["test_001", "test_002"],
      "reason": "Both test same endpoint with same data",
      "suggestion": "Merge into one comprehensive test"
    }}
  ],
  "missing_tests": [
    {{
      "scenario": "DELETE endpoint not tested",
      "priority": "high",
      "suggested_test": "Add DELETE /api/resource test with cleanup"
    }}
  ],
  "test_data_issues": [
    {{
      "test_id": "test_001",
      "issue": "Using unrealistic data",
      "suggestion": "Use production-like addresses and names"
    }}
  ],
  "structure_issues": [
    {{
      "issue": "Tests not in dependency order",
      "suggestion": "Run auth tests before resource tests"
    }}
  ],
  "performance_issues": [
    {{
      "test_id": "test_001",
      "issue": "Takes 30 seconds",
      "suggestion": "Parallelize independent API calls"
    }}
  ],
  "overall_health": {{
    "score": 85,
    "grade": "B",
    "summary": "Good test suite with some improvements needed"
  }}
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.3)
            
            # Parse JSON from response
            improvements_text = response.strip()
            if "```json" in improvements_text:
                improvements_text = improvements_text.split("```json")[1].split("```")[0].strip()
            elif "```" in improvements_text:
                improvements_text = improvements_text.split("```")[1].split("```")[0].strip()
            
            improvements = json.loads(improvements_text)
            
            logger.info(f"[OK] Analysis complete")
            logger.info(f"[INFO] Overall health score: {improvements.get('overall_health', {}).get('score', 0)}")
            
            return improvements
        
        except Exception as e:
            logger.error(f"[ERROR] Error analyzing test results: {e}")
            return {
                'flaky_tests': [],
                'redundant_tests': [],
                'missing_tests': [],
                'test_data_issues': [],
                'structure_issues': [],
                'performance_issues': [],
                'overall_health': {'score': 0, 'grade': 'F', 'summary': 'Analysis failed'},
                'error': str(e)
            }
    
    async def track_metrics_over_time(
        self,
        historical_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Track metrics over time to identify trends
        
        Args:
            historical_results: Historical test results with timestamps
            
        Returns:
            Trend analysis
        """
        try:
            logger.info(f"[CHART] Tracking metrics over time...")
            
            # Calculate metrics by time period
            metrics_by_period = {}
            
            for result in historical_results:
                timestamp = result.get('timestamp', datetime.utcnow().isoformat())
                date = timestamp.split('T')[0]  # Get date part
                
                if date not in metrics_by_period:
                    metrics_by_period[date] = {
                        'total': 0,
                        'passed': 0,
                        'failed': 0,
                        'errors': 0
                    }
                
                metrics_by_period[date]['total'] += 1
                
                status = result.get('status', 'unknown')
                if status == 'passed':
                    metrics_by_period[date]['passed'] += 1
                elif status == 'failed':
                    metrics_by_period[date]['failed'] += 1
                elif status == 'error':
                    metrics_by_period[date]['errors'] += 1
            
            # Calculate trends
            dates = sorted(metrics_by_period.keys())
            if len(dates) >= 2:
                first_date = dates[0]
                last_date = dates[-1]
                
                first_pass_rate = (metrics_by_period[first_date]['passed'] / 
                                  metrics_by_period[first_date]['total'] * 100)
                last_pass_rate = (metrics_by_period[last_date]['passed'] / 
                                 metrics_by_period[last_date]['total'] * 100)
                
                trend = last_pass_rate - first_pass_rate
                
                trend_analysis = {
                    'trend': 'improving' if trend > 0 else 'declining' if trend < 0 else 'stable',
                    'change': trend,
                    'first_date': first_date,
                    'last_date': last_date,
                    'first_pass_rate': first_pass_rate,
                    'last_pass_rate': last_pass_rate
                }
            else:
                trend_analysis = {
                    'trend': 'insufficient_data',
                    'change': 0
                }
            
            logger.info(f"[OK] Trend: {trend_analysis.get('trend')}")
            
            return {
                'metrics_by_period': metrics_by_period,
                'trend_analysis': trend_analysis,
                'total_periods': len(dates)
            }
        
        except Exception as e:
            logger.error(f"[ERROR] Error tracking metrics: {e}")
            return {
                'metrics_by_period': {},
                'trend_analysis': {'trend': 'error'},
                'error': str(e)
            }
    
    async def suggest_optimizations(
        self,
        api_spec: Dict[str, Any],
        test_results: List[Dict[str, Any]],
        execution_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Suggest optimizations for API testing
        
        Args:
            api_spec: API specification
            test_results: Test results
            execution_time: Total execution time in seconds
            
        Returns:
            Optimization suggestions
        """
        try:
            logger.info("[START] Suggesting optimizations...")
            
            prompt = f"""
Suggest optimizations for this API testing setup:

**API Specification:**
- Endpoints: {len(api_spec.get('endpoints', []))}
- Test Scenarios: {len(api_spec.get('test_scenarios', []))}

**Test Results:**
- Total Tests: {len(test_results)}
- Passed: {len([r for r in test_results if r.get('status') == 'passed'])}
- Failed: {len([r for r in test_results if r.get('status') == 'failed'])}
- Execution Time: {execution_time} seconds

**Your Task:**
Suggest optimizations:

1. **Test Parallelization**: Which tests can run in parallel?
2. **Test Reduction**: Can we reduce test count without losing coverage?
3. **Data Optimization**: Better test data strategies?
4. **Caching**: What can be cached to speed up tests?
5. **Dependency Optimization**: Better dependency management?

Output as JSON:
{{
  "parallelization": {{
    "potential": "high|medium|low",
    "suggestion": "Run independent endpoint tests in parallel",
    "estimated_speedup": "50%"
  }},
  "test_reduction": {{
    "potential": "high|medium|low",
    "suggestion": "Merge redundant tests",
    "tests_to_remove": ["test_001", "test_002"]
  }},
  "data_optimization": {{
    "suggestion": "Cache authentication tokens",
    "estimated_speedup": "20%"
  }},
  "caching": {{
    "items_to_cache": ["auth_token", "address_ids"],
    "estimated_speedup": "30%"
  }},
  "dependency_optimization": {{
    "suggestion": "Reorder tests by dependencies",
    "estimated_speedup": "10%"
  }},
  "overall_potential_speedup": "70%"
}}

Return ONLY valid JSON, no markdown, no explanations.
"""
            
            response = await self.gemini.generate_content(prompt, temperature=0.3)
            
            # Parse JSON from response
            optimizations_text = response.strip()
            if "```json" in optimizations_text:
                optimizations_text = optimizations_text.split("```json")[1].split("```")[0].strip()
            elif "```" in optimizations_text:
                optimizations_text = optimizations_text.split("```")[1].split("```")[0].strip()
            
            optimizations = json.loads(optimizations_text)
            
            logger.info(f"[OK] Optimizations suggested: {optimizations.get('overall_potential_speedup', '0%')} potential speedup")
            
            return optimizations
        
        except Exception as e:
            logger.error(f"[ERROR] Error suggesting optimizations: {e}")
            return {
                'parallelization': {'potential': 'unknown'},
                'test_reduction': {'potential': 'unknown'},
                'data_optimization': {},
                'caching': {},
                'dependency_optimization': {},
                'overall_potential_speedup': '0%',
                'error': str(e)
            }
    
    async def generate_improvement_report(
        self,
        partner_id: str,
        test_results: List[Dict[str, Any]],
        api_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive improvement report
        
        Args:
            partner_id: Partner identifier
            test_results: Test results
            api_spec: API specification
            
        Returns:
            Comprehensive improvement report
        """
        try:
            logger.info(f"[NOTE] Generating improvement report for {partner_id}...")
            
            # Analyze test results
            analysis = await self.analyze_test_results(test_results)
            
            # Suggest optimizations
            optimizations = await self.suggest_optimizations(
                api_spec=api_spec,
                test_results=test_results
            )
            
            # Calculate summary statistics
            total = len(test_results)
            passed = len([r for r in test_results if r.get('status') == 'passed'])
            failed = len([r for r in test_results if r.get('status') == 'failed'])
            pass_rate = (passed / total * 100) if total > 0 else 0
            
            report = {
                'partner_id': partner_id,
                'generated_at': datetime.utcnow().isoformat(),
                'summary': {
                    'total_tests': total,
                    'passed': passed,
                    'failed': failed,
                    'pass_rate': pass_rate,
                    'health_score': analysis.get('overall_health', {}).get('score', 0)
                },
                'analysis': analysis,
                'optimizations': optimizations,
                'action_items': []
            }
            
            # Generate action items
            action_items = []
            
            # From flaky tests
            for flaky in analysis.get('flaky_tests', []):
                action_items.append({
                    'priority': 'high',
                    'category': 'reliability',
                    'action': f"Fix flaky test: {flaky.get('test_id')}",
                    'suggestion': flaky.get('suggestion')
                })
            
            # From missing tests
            for missing in analysis.get('missing_tests', [])[:3]:  # Top 3
                action_items.append({
                    'priority': missing.get('priority', 'medium'),
                    'category': 'coverage',
                    'action': f"Add missing test: {missing.get('scenario')}",
                    'suggestion': missing.get('suggested_test')
                })
            
            # From optimizations
            if optimizations.get('parallelization', {}).get('potential') == 'high':
                action_items.append({
                    'priority': 'medium',
                    'category': 'performance',
                    'action': 'Implement test parallelization',
                    'suggestion': optimizations['parallelization'].get('suggestion')
                })
            
            report['action_items'] = action_items
            
            logger.info(f"[OK] Report generated with {len(action_items)} action items")
            
            return report
        
        except Exception as e:
            logger.error(f"[ERROR] Error generating report: {e}")
            return {
                'partner_id': partner_id,
                'generated_at': datetime.utcnow().isoformat(),
                'error': str(e)
            }

