# 🤖 AI Application Layer

This directory contains the core AI-powered components of the Autonomous API Testing & Execution System.

---

## 📁 Directory Structure

```
ai/
├── understanding/           # Document understanding & analysis
│   ├── comprehensive_api_analyzer.py   # Main API analyzer with LangGraph
│   ├── schema_inferrer.py              # Schema inference from examples
│   └── workflow_analyzer.py            # Workflow analysis
│
├── testing/                # Autonomous testing components
│   ├── autonomous_test_generator.py    # CrewAI multi-agent test generation
│   ├── smart_data_generator.py         # AI-powered test data generation
│   ├── intelligent_test_executor.py    # Self-healing test execution
│   ├── error_analyzer.py               # AI-powered error analysis
│   ├── test_executor.py                # Basic test executor
│   ├── test_coordinator.py             # Test coordination
│   ├── test_data_generator.py          # Test data generation
│   ├── dependency_analyzer.py          # Dependency analysis
│   └── api_test_agent.py               # Test agent
│
├── agents/                 # AI agents
│   ├── agent_factory.py    # Agent creation
│   └── __init__.py
│
├── generators/             # Code generators
│   ├── adapter_generator.py    # Adapter generation
│   ├── tool_generator.py       # Tool generation
│   └── __init__.py
│
├── graphs/                 # LangGraph workflows
│   ├── execution_graph.py      # Execution workflows
│   └── __init__.py
│
└── parsers/                # Document parsers
    ├── base_parser.py          # Base parser
    ├── format_detector.py      # Format detection
    ├── image_parser.py         # Image parsing
    ├── multi_parser.py         # Multi-format parsing
    └── __init__.py
```

---

## 🎯 Core Components

### 1. Understanding Layer

#### `comprehensive_api_analyzer.py`
**Purpose:** Complete API documentation analysis using LangGraph

**Key Features:**
- Extracts ALL endpoints (GET, POST, PUT, PATCH, DELETE)
- Identifies authentication requirements
- Understands request/response schemas
- Maps endpoint dependencies
- Extracts business rules
- Generates test scenarios

**Usage:**
```python
from src.application.ai.understanding.comprehensive_api_analyzer import ComprehensiveAPIAnalyzer

analyzer = ComprehensiveAPIAnalyzer()
result = await analyzer.analyze_from_file(file_bytes=pdf_bytes)

# Access results
endpoints = result['endpoints']
auth_config = result['auth_config']
schemas = result['schemas']
dependencies = result['dependencies']
test_scenarios = result['test_scenarios']
```

#### `schema_inferrer.py`
**Purpose:** Infer JSON schemas from examples

**Key Features:**
- Infer schemas from example data
- Detect field types and constraints
- Merge multiple schemas
- Validate data against schemas
- Generate sample data

**Usage:**
```python
from src.application.ai.understanding.schema_inferrer import SchemaInferrer

inferrer = SchemaInferrer()
schema = await inferrer.infer_schema_from_examples(
    examples=[example1, example2],
    schema_type="request"
)
```

---

### 2. Testing Layer

#### `autonomous_test_generator.py`
**Purpose:** Generate comprehensive tests using CrewAI multi-agent system

**Key Features:**
- Test Architect agent (strategy)
- Test Generator agent (test cases)
- Data Generator agent (test data)
- Coverage Validator agent (coverage)

**Usage:**
```python
from src.application.ai.testing.autonomous_test_generator import AutonomousTestGenerator

generator = AutonomousTestGenerator()
tests = await generator.generate_tests(
    api_spec=api_spec,
    test_scenarios=scenarios
)

test_cases = tests['test_cases']
test_data = tests['test_data']
coverage = tests['coverage']
```

#### `smart_data_generator.py`
**Purpose:** Generate realistic test data using AI

**Key Features:**
- Valid data generation (happy path)
- Invalid data generation (error cases)
- Edge case data generation (boundaries)
- Bulk data generation
- Workflow data generation
- Data mutation

**Usage:**
```python
from src.application.ai.testing.smart_data_generator import SmartDataGenerator

generator = SmartDataGenerator()

# Generate valid data
valid_data = await generator.generate_test_data(
    schema=schema,
    scenario_type="valid"
)

# Generate invalid data
invalid_data = await generator.generate_test_data(
    schema=schema,
    scenario_type="invalid"
)
```

#### `intelligent_test_executor.py`
**Purpose:** Execute tests with AI-powered self-healing

**Key Features:**
- Automatic authentication
- Dependency-aware execution
- AI failure analysis
- Automatic fix application
- Retry with modified approach
- Data extraction and substitution

**Usage:**
```python
from src.application.ai.testing.intelligent_test_executor import IntelligentTestExecutor

executor = IntelligentTestExecutor()
results = await executor.execute_tests(
    test_cases=test_cases,
    auth_config=auth_config,
    base_url="https://api.example.com",
    max_retries=3
)

print(f"Passed: {results['passed']}/{results['total_tests']}")
print(f"Pass Rate: {results['pass_rate']}%")
```

#### `error_analyzer.py`
**Purpose:** Analyze API errors and suggest fixes

**Key Features:**
- Root cause analysis
- Error categorization
- Fix suggestions
- Retry strategies
- Pattern analysis
- Improvement suggestions
- User-friendly explanations

**Usage:**
```python
from src.application.ai.testing.error_analyzer import ErrorAnalyzer

analyzer = ErrorAnalyzer()

# Analyze single error
analysis = await analyzer.analyze_error(
    request=failed_request,
    response=error_response,
    api_spec=api_spec
)

print(f"Root Cause: {analysis['root_cause']}")
print(f"Fix: {analysis['suggested_fix']}")

# Analyze multiple failures
patterns = await analyzer.analyze_multiple_failures(
    failures=failed_tests
)

# Suggest improvements
improvements = await analyzer.suggest_test_improvements(
    test_results=all_results
)
```

---

## 🔄 Workflows

### Complete Testing Workflow

```
1. Document Analysis
   ↓
   ComprehensiveAPIAnalyzer
   - Extract endpoints
   - Understand auth
   - Map dependencies
   - Generate scenarios
   ↓
2. Test Generation
   ↓
   AutonomousTestGenerator (CrewAI)
   - Test Architect: Strategy
   - Test Generator: Test cases
   - Data Generator: Test data
   - Coverage Validator: Validation
   ↓
3. Test Execution
   ↓
   IntelligentTestExecutor (LangGraph)
   - Setup authentication
   - Execute test
   - Failure? → Analyze → Fix → Retry
   - Success? → Next test
   ↓
4. Analysis & Improvement
   ↓
   ErrorAnalyzer
   - Analyze failures
   - Find patterns
   - Suggest improvements
```

---

## 🛠️ Technology Stack

### AI/ML
- **LangGraph**: State machine workflows
- **CrewAI**: Multi-agent collaboration
- **Google Gemini**: AI reasoning and analysis
- **Mistral**: OCR and document processing

### Core Libraries
- **httpx**: HTTP client for API calls
- **Pydantic**: Data validation
- **jsonschema**: Schema validation
- **asyncio**: Async operations

---

## 📊 Key Concepts

### 1. LangGraph State Machines

Used for complex workflows with multiple steps:

```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(StateType)
workflow.add_node("step1", step1_function)
workflow.add_node("step2", step2_function)
workflow.add_edge("step1", "step2")
workflow.add_edge("step2", END)

graph = workflow.compile()
result = await graph.ainvoke(initial_state)
```

### 2. CrewAI Multi-Agent System

Collaborative AI agents working together:

```python
from crewai import Agent, Task, Crew

agent1 = Agent(role="Architect", goal="Design strategy")
agent2 = Agent(role="Generator", goal="Create tests")

task1 = Task(description="Design test strategy", agent=agent1)
task2 = Task(description="Generate tests", agent=agent2)

crew = Crew(agents=[agent1, agent2], tasks=[task1, task2])
result = crew.kickoff()
```

### 3. Self-Healing Tests

Tests that fix themselves:

```
Test Fails
   ↓
AI Analyzes Failure
   ↓
Identifies Root Cause
   ↓
Suggests Fix
   ↓
Applies Fix
   ↓
Retries Test
   ↓
Success!
```

---

## 🎯 Best Practices

### 1. Error Handling

Always handle errors gracefully:

```python
try:
    result = await analyzer.analyze_from_file(file_bytes)
except Exception as e:
    logger.error(f"Analysis failed: {e}")
    return default_result
```

### 2. Logging

Use structured logging:

```python
logger.info("🔍 Analyzing documentation...")
logger.info(f"✅ Found {len(endpoints)} endpoints")
logger.error(f"❌ Error: {error}")
```

### 3. Async Operations

Use async/await for I/O operations:

```python
async def process_document():
    result = await analyzer.analyze_from_file(file_bytes)
    tests = await generator.generate_tests(result)
    execution = await executor.execute_tests(tests)
    return execution
```

### 4. Type Hints

Use type hints for better code quality:

```python
async def analyze_error(
    request: Dict[str, Any],
    response: Dict[str, Any],
    api_spec: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    ...
```

---

## 🧪 Testing

### Unit Tests

Test individual components:

```python
import pytest

@pytest.mark.asyncio
async def test_schema_inferrer():
    inferrer = SchemaInferrer()
    schema = await inferrer.infer_schema_from_examples(
        examples=[{"name": "John", "age": 30}]
    )
    assert "properties" in schema
    assert "name" in schema["properties"]
```

### Integration Tests

Test complete workflows:

```python
@pytest.mark.asyncio
async def test_complete_workflow():
    # Analyze
    analyzer = ComprehensiveAPIAnalyzer()
    api_spec = await analyzer.analyze_from_file(file_bytes)
    
    # Generate
    generator = AutonomousTestGenerator()
    tests = await generator.generate_tests(api_spec)
    
    # Execute
    executor = IntelligentTestExecutor()
    results = await executor.execute_tests(tests)
    
    assert results['pass_rate'] > 80
```

---

## 📈 Performance

### Optimization Tips

1. **Caching**: Cache API specifications
2. **Parallel Execution**: Run independent tests in parallel
3. **Batch Processing**: Process multiple documents together
4. **Connection Pooling**: Reuse HTTP connections

### Monitoring

Monitor these metrics:
- Analysis time per document
- Test generation time
- Test execution time
- Pass rate
- Self-healing success rate

---

## 🔮 Future Enhancements

### Planned Features

1. **Natural Language Executor**
   - Intent understanding
   - Autonomous execution
   - Multi-step orchestration

2. **Learning & Optimization**
   - Mem0 integration
   - Pattern learning
   - Continuous improvement

3. **Advanced Analytics**
   - Test coverage analysis
   - Performance profiling
   - Trend analysis

---

## 📚 Resources

- **LangGraph**: https://langchain-ai.github.io/langgraph/
- **CrewAI**: https://docs.crewai.com/
- **Google Gemini**: https://ai.google.dev/
- **Mistral**: https://docs.mistral.ai/

---

## 🤝 Contributing

When adding new components:

1. Follow existing patterns
2. Add comprehensive docstrings
3. Include type hints
4. Add logging
5. Handle errors gracefully
6. Write tests
7. Update documentation

---

## 📞 Support

For questions or issues:
- Check `/AUTONOMOUS_TESTING_IMPLEMENTATION.md`
- Review `/AUTONOMOUS_TESTING_QUICK_START.md`
- See API docs at `http://localhost:8000/docs`

---

**Built with ❤️ using cutting-edge AI technology**
