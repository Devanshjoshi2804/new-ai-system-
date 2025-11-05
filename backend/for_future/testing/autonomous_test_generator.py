"""
Autonomous Test Generator using CrewAI Multi-Agent System
Generates comprehensive tests using collaborative AI agents
"""
import json
import logging
from typing import List, Dict, Any, Optional
from crewai import Agent, Task, Crew, Process
from langchain_google_genai import ChatGoogleGenerativeAI

from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class AutonomousTestGenerator:
    """Generate comprehensive tests using multi-agent collaboration"""
    
    def __init__(self):
        """Initialize test generator with Gemini LLM"""
        # Use Gemini as the LLM for CrewAI
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=settings.gemini_api_key,
            temperature=0.3
        )
    
    async def generate_tests(
        self,
        api_spec: Dict[str, Any],
        test_scenarios: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate executable tests using CrewAI
        
        Args:
            api_spec: Complete API specification
            test_scenarios: High-level test scenarios
            
        Returns:
            List of executable test cases
        """
        try:
            logger.info("🤖 Starting multi-agent test generation...")
            
            # Agent 1: Test Architect
            test_architect = Agent(
                role="Test Architect",
                goal="Design comprehensive test strategy covering all scenarios",
                backstory="""You are an expert in API testing with deep understanding of 
                REST principles, authentication flows, and edge cases. You excel at 
                identifying critical paths and potential failure points.""",
                verbose=True,
                llm=self.llm,
                allow_delegation=True
            )
            
            # Agent 2: Test Case Generator
            test_generator = Agent(
                role="Test Case Generator",
                goal="Create detailed, executable test cases with proper assertions",
                backstory="""You are a specialist in writing executable test cases with 
                proper setup, execution, and validation steps. You know how to structure 
                tests for maximum clarity and maintainability.""",
                verbose=True,
                llm=self.llm,
                allow_delegation=True
            )
            
            # Agent 3: Test Data Generator
            data_generator = Agent(
                role="Test Data Generator",
                goal="Generate realistic and comprehensive test data",
                backstory="""You are an expert in creating valid and invalid test data 
                that covers all edge cases and business rules. You understand data 
                constraints, formats, and realistic production-like values.""",
                verbose=True,
                llm=self.llm,
                allow_delegation=True
            )
            
            # Agent 4: Coverage Validator
            coverage_validator = Agent(
                role="Coverage Validator",
                goal="Ensure comprehensive test coverage and identify gaps",
                backstory="""You are a quality assurance expert who validates that all 
                endpoints, methods, and scenarios are covered. You identify missing 
                test cases and suggest improvements.""",
                verbose=True,
                llm=self.llm,
                allow_delegation=False
            )
            
            # Task 1: Create Test Strategy
            task1 = Task(
                description=f"""
Analyze this API specification and create a comprehensive test strategy:

API Specification:
{json.dumps(api_spec, indent=2)[:8000]}

Test Scenarios:
{json.dumps(test_scenarios, indent=2)[:5000]}

Create a test strategy that identifies:
1. Critical paths to test (authentication, main workflows)
2. Authentication test requirements (login, token handling, auth failures)
3. Data validation tests (required fields, formats, constraints)
4. Error handling tests (invalid data, missing fields, business rule violations)
5. Edge cases (boundary values, empty data, max lengths)
6. Performance considerations (rate limits, timeouts)
7. Dependency testing (calling endpoints in wrong order)

Output as JSON:
{{
  "critical_paths": ["path1", "path2"],
  "authentication_tests": ["test1", "test2"],
  "validation_tests": ["test1", "test2"],
  "error_tests": ["test1", "test2"],
  "edge_cases": ["case1", "case2"],
  "performance_tests": ["test1", "test2"],
  "dependency_tests": ["test1", "test2"]
}}
""",
                agent=test_architect,
                expected_output="Comprehensive test strategy document in JSON format"
            )
            
            # Task 2: Generate Test Cases
            task2 = Task(
                description=f"""
Generate executable test cases based on the test strategy and scenarios:

Test Scenarios:
{json.dumps(test_scenarios, indent=2)[:5000]}

API Specification:
{json.dumps(api_spec, indent=2)[:8000]}

For each scenario, create detailed test cases with:
1. Test name and description
2. Pre-conditions (setup steps, authentication)
3. Test steps (sequence of API calls with exact endpoints and methods)
4. Test data (what data to send)
5. Expected results (status codes, response structure)
6. Assertions (what to verify in responses)
7. Post-conditions (cleanup steps)
8. Dependencies (which tests must run before this)

Output as JSON array:
[
  {{
    "test_id": "test_001",
    "name": "Happy Path - Complete Booking Flow",
    "description": "Test complete booking workflow with valid data",
    "category": "happy_path",
    "priority": "high",
    "pre_conditions": [
      "API is accessible",
      "Test credentials are valid"
    ],
    "steps": [
      {{
        "step": 1,
        "action": "Login",
        "endpoint": "/api/login",
        "method": "POST",
        "description": "Authenticate and get token"
      }},
      {{
        "step": 2,
        "action": "Create Booking",
        "endpoint": "/api/bookings",
        "method": "POST",
        "description": "Create a new booking"
      }}
    ],
    "expected_results": [
      "Login returns 200 with token",
      "Booking created with 201 status"
    ],
    "assertions": [
      "Response contains token",
      "Booking ID is returned",
      "Status is 'created'"
    ],
    "post_conditions": [
      "Cleanup created booking"
    ],
    "depends_on": []
  }}
]
""",
                agent=test_generator,
                expected_output="List of executable test cases in JSON format"
            )
            
            # Task 3: Generate Test Data
            task3 = Task(
                description=f"""
Generate comprehensive test data for all test cases:

API Schemas:
{json.dumps(api_spec.get('schemas', {}), indent=2)[:5000]}

Business Rules:
{json.dumps(api_spec.get('business_rules', []), indent=2)[:3000]}

Create test data sets:
1. **Valid Data** (happy path):
   - All required fields present
   - Valid formats and types
   - Realistic values
   - Respects business rules

2. **Invalid Data** (error cases):
   - Missing required fields (one at a time)
   - Invalid formats (bad email, phone, date)
   - Invalid types (string instead of number)
   - Violates business rules (negative weight, etc.)

3. **Edge Case Data** (boundaries):
   - Empty strings
   - Very long strings (max length + 1)
   - Zero and negative numbers
   - Boundary dates (past, future, today)
   - Special characters

4. **Realistic Data** (production-like):
   - Real addresses
   - Real names
   - Valid phone numbers
   - Realistic dimensions and weights

Output as JSON:
{{
  "valid_data_sets": [
    {{
      "name": "valid_booking_1",
      "data": {{"origin": "Mumbai", "destination": "Delhi", "weight": 10}}
    }}
  ],
  "invalid_data_sets": [
    {{
      "name": "missing_origin",
      "data": {{"destination": "Delhi", "weight": 10}},
      "expected_error": "origin is required"
    }}
  ],
  "edge_case_data_sets": [
    {{
      "name": "zero_weight",
      "data": {{"origin": "Mumbai", "destination": "Delhi", "weight": 0}},
      "expected_error": "weight must be greater than 0"
    }}
  ],
  "realistic_data_sets": [
    {{
      "name": "realistic_booking_1",
      "data": {{
        "origin": "123 Main St, Mumbai, Maharashtra 400001",
        "destination": "456 Park Ave, Delhi, Delhi 110001",
        "weight": 15.5,
        "dimensions": {{"length": 30, "width": 20, "height": 10}}
      }}
    }}
  ]
}}
""",
                agent=data_generator,
                expected_output="Comprehensive test data sets in JSON format"
            )
            
            # Task 4: Validate Coverage
            task4 = Task(
                description=f"""
Validate test coverage and identify gaps:

API Endpoints:
{json.dumps(api_spec.get('endpoints', []), indent=2)[:5000]}

Review the generated test cases and data to ensure:
1. **Endpoint Coverage**: All endpoints are tested
2. **Method Coverage**: All HTTP methods (GET, POST, PUT, DELETE) are tested
3. **Authentication Coverage**: Auth success and failure cases
4. **Error Coverage**: All error scenarios are tested
5. **Edge Case Coverage**: Boundary values and special cases
6. **Workflow Coverage**: Complete end-to-end workflows
7. **Business Rule Coverage**: All business rules are validated

Identify:
- Missing test cases
- Untested endpoints
- Uncovered error scenarios
- Missing edge cases
- Gaps in workflows

Output as JSON:
{{
  "coverage_summary": {{
    "endpoints_covered": 15,
    "endpoints_total": 20,
    "coverage_percentage": 75,
    "methods_covered": ["GET", "POST"],
    "methods_missing": ["PUT", "DELETE"]
  }},
  "gaps": [
    {{
      "type": "missing_endpoint",
      "endpoint": "/api/cancel",
      "severity": "high",
      "recommendation": "Add cancel booking test"
    }}
  ],
  "recommendations": [
    "Add tests for DELETE methods",
    "Add more edge cases for address validation",
    "Add performance tests for bulk operations"
  ]
}}
""",
                agent=coverage_validator,
                expected_output="Coverage report with gaps and recommendations in JSON format"
            )
            
            # Create crew
            crew = Crew(
                agents=[test_architect, test_generator, data_generator, coverage_validator],
                tasks=[task1, task2, task3, task4],
                process=Process.sequential,
                verbose=True
            )
            
            # Execute crew
            logger.info("🚀 Executing multi-agent test generation crew...")
            result = crew.kickoff()
            
            # Parse results
            test_results = self._parse_crew_results(result)
            
            logger.info(f"✅ Generated {len(test_results.get('test_cases', []))} test cases")
            
            return test_results
        
        except Exception as e:
            logger.error(f"❌ Error in multi-agent test generation: {e}", exc_info=True)
            return {
                'test_cases': [],
                'test_data': {},
                'coverage': {},
                'error': str(e)
            }
    
    def _parse_crew_results(self, result: Any) -> Dict[str, Any]:
        """
        Parse results from CrewAI execution
        
        Args:
            result: Raw result from crew.kickoff()
            
        Returns:
            Parsed test results
        """
        try:
            # CrewAI returns string output from final task
            result_text = str(result)
            
            # Try to extract JSON from result
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            # Try to parse as JSON
            try:
                parsed = json.loads(result_text)
                return parsed
            except json.JSONDecodeError:
                # If not valid JSON, return structured result
                return {
                    'test_cases': [],
                    'test_data': {},
                    'coverage': {},
                    'raw_output': result_text
                }
        
        except Exception as e:
            logger.error(f"Error parsing crew results: {e}")
            return {
                'test_cases': [],
                'test_data': {},
                'coverage': {},
                'error': str(e)
            }
    
    async def generate_additional_tests(
        self,
        api_spec: Dict[str, Any],
        existing_tests: List[Dict[str, Any]],
        coverage_gaps: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate additional tests to fill coverage gaps
        
        Args:
            api_spec: API specification
            existing_tests: Already generated tests
            coverage_gaps: Identified gaps in coverage
            
        Returns:
            Additional test cases
        """
        try:
            logger.info("🔧 Generating additional tests to fill gaps...")
            
            # Create a focused agent for gap filling
            gap_filler = Agent(
                role="Gap Filler",
                goal="Generate tests to fill specific coverage gaps",
                backstory="""You are an expert at identifying and filling gaps in test 
                coverage. You create targeted tests for missing scenarios.""",
                verbose=True,
                llm=self.llm
            )
            
            task = Task(
                description=f"""
Generate tests to fill these coverage gaps:

Coverage Gaps:
{json.dumps(coverage_gaps, indent=2)}

Existing Tests:
{json.dumps([t.get('name') for t in existing_tests], indent=2)}

API Specification:
{json.dumps(api_spec, indent=2)[:5000]}

Create new test cases that:
1. Cover the identified gaps
2. Don't duplicate existing tests
3. Follow the same structure as existing tests
4. Are comprehensive and executable

Output as JSON array of test cases.
""",
                agent=gap_filler,
                expected_output="Additional test cases in JSON format"
            )
            
            crew = Crew(
                agents=[gap_filler],
                tasks=[task],
                process=Process.sequential,
                verbose=True
            )
            
            result = crew.kickoff()
            additional_tests = self._parse_crew_results(result)
            
            logger.info(f"✅ Generated {len(additional_tests.get('test_cases', []))} additional tests")
            
            return additional_tests.get('test_cases', [])
        
        except Exception as e:
            logger.error(f"❌ Error generating additional tests: {e}")
            return []
