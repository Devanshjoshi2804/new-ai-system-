"""
MongoDB models for API testing execution and results (using Motor, not Beanie)
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from bson import ObjectId


class APITestResult(BaseModel):
    """Individual API test result"""
    
    # MongoDB ID
    id: Optional[str] = Field(default=None, alias="_id", description="MongoDB document ID")
    
    test_execution_id: str = Field(..., description="ID of parent test execution")
    endpoint: str = Field(..., description="API endpoint path")
    method: str = Field(..., description="HTTP method (GET, POST, etc.)")
    test_case_id: str = Field(..., description="Unique test case identifier")
    test_case_name: str = Field(default="", description="Human-readable test case name")
    
    # Execution details
    status: str = Field(..., description="Test status: passed, failed, retrying, skipped")
    attempt_number: int = Field(default=1, description="Attempt number (for retries)")
    
    # Request/Response data
    request_data: Dict[str, Any] = Field(default_factory=dict, description="Request payload sent")
    request_headers: Dict[str, str] = Field(default_factory=dict, description="Request headers")
    response_data: Optional[Dict[str, Any]] = Field(default=None, description="Response body received")
    response_status: Optional[int] = Field(default=None, description="HTTP response status code")
    response_headers: Optional[Dict[str, str]] = Field(default=None, description="Response headers")
    
    # Performance metrics
    execution_time: float = Field(default=0.0, description="Execution time in seconds")
    
    # Error tracking
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    error_type: Optional[str] = Field(default=None, description="Error type/category")
    
    # Analysis
    ai_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Gemini analysis of failure")
    
    # Timestamps
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When test was executed")
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class TestExecution(BaseModel):
    """Master test execution record for a partner integration"""
    
    # MongoDB ID
    id: Optional[str] = Field(default=None, alias="_id", description="MongoDB document ID")
    
    # Identifiers
    partner_id: str = Field(..., description="Partner ID being tested")
    documentation_id: str = Field(..., description="Documentation ID used for testing")
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID")
    
    # Status
    status: str = Field(
        default="pending",
        description="Execution status: pending, analyzing, running, completed, failed"
    )
    
    # Progress tracking
    total_endpoints: int = Field(default=0, description="Total number of endpoints to test")
    tested_endpoints: int = Field(default=0, description="Number of endpoints tested so far")
    passed_tests: int = Field(default=0, description="Number of tests that passed")
    failed_tests: int = Field(default=0, description="Number of tests that failed")
    skipped_tests: int = Field(default=0, description="Number of tests skipped")
    
    # Dependency analysis
    dependency_graph: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Dependency graph: {endpoint: [dependencies]}"
    )
    execution_order: List[str] = Field(
        default_factory=list,
        description="Ordered list of endpoints to execute"
    )
    
    # Test results
    test_results: List[str] = Field(
        default_factory=list,
        description="List of APITestResult IDs"
    )
    
    # Shared test data (for dependencies)
    test_data_store: Dict[str, Any] = Field(
        default_factory=dict,
        description="Shared data from successful tests (IDs, tokens, etc.)"
    )
    
    # Current execution state
    current_endpoint: Optional[str] = Field(default=None, description="Currently testing endpoint")
    current_phase: str = Field(default="initializing", description="Current phase of testing")
    
    # Error tracking
    global_errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Global errors that stopped testing"
    )
    
    # Metrics
    total_execution_time: float = Field(default=0.0, description="Total execution time in seconds")
    average_response_time: float = Field(default=0.0, description="Average API response time")
    pass_rate: float = Field(default=0.0, description="Percentage of tests passed")
    
    # Timestamps
    started_at: Optional[datetime] = Field(default=None, description="When testing started")
    completed_at: Optional[datetime] = Field(default=None, description="When testing completed")
    
    # Configuration
    max_retries: int = Field(default=5, description="Maximum retry attempts per test")
    retry_delay: float = Field(default=1.0, description="Initial retry delay in seconds")
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
    
    def calculate_metrics(self):
        """Calculate aggregated metrics"""
        total_tests = self.passed_tests + self.failed_tests
        if total_tests > 0:
            self.pass_rate = (self.passed_tests / total_tests) * 100
        else:
            self.pass_rate = 0.0
    
    def is_complete(self) -> bool:
        """Check if testing is complete"""
        return self.status in ["completed", "failed"]
    
    def is_successful(self) -> bool:
        """Check if all tests passed"""
        return self.status == "completed" and self.failed_tests == 0


